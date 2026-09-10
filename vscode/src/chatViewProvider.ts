/**
 * Chat sidebar webview provider for AlpieCode.
 *
 * Cross-platform (Windows / Linux / macOS).
 * Manages webview lifecycle, SSE streaming, chat history, workdir resolution,
 * multimodal image attachments, change plan approval, and sandbox execution.
 */

import * as vscode from "vscode";
import * as os from "os";
import * as path from "path";
import * as fs from "fs";
import * as cp from "child_process";
import { streamChat, checkHealth, AgentEvent } from "./sseClient";
import { showDiffPreview } from "./diffHelper";

/* ------------------------------------------------------------------ */
/*  Data models                                                       */
/* ------------------------------------------------------------------ */

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  image?: string;
  timestamp: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  sessionId?: string;
  createdAt: number;
}

interface PendingChange {
  workdir: string;
  relPath: string;
  absPath: string;
  newContent: string;
  oldContent: string;
  toolName: string;
  isNewFile: boolean;
  oldStr?: string;
  newStr?: string;
}


interface MissingDep {
  name: string;
  type: "global" | "pylib" | "npm";
  installCmd: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const MAX_AUTO_FIX_RETRIES = 3;

/** Python standard library modules — never flag these as missing deps. */
const PYTHON_STDLIB = new Set([
  "abc", "argparse", "ast", "asyncio", "base64", "bisect", "calendar",
  "codecs", "collections", "configparser", "contextlib", "copy", "csv",
  "ctypes", "dataclasses", "datetime", "decimal", "difflib", "dis",
  "email", "enum", "fileinput", "fnmatch", "fractions", "functools",
  "gc", "getpass", "glob", "gzip", "hashlib", "heapq", "html", "http",
  "importlib", "inspect", "io", "itertools", "json", "logging", "math",
  "mimetypes", "multiprocessing", "operator", "os", "pathlib", "pickle",
  "platform", "pprint", "profile", "pstats", "queue", "random", "re",
  "readline", "secrets", "select", "shelve", "shlex", "shutil", "signal",
  "socket", "sqlite3", "ssl", "statistics", "string", "struct",
  "subprocess", "sys", "tempfile", "textwrap", "threading", "time",
  "timeit", "tkinter", "traceback", "turtle", "types", "typing",
  "unicodedata", "unittest", "urllib", "uuid", "warnings", "weakref",
  "xml", "xmlrpc", "zipfile", "zipimport", "zlib",
]);

/** Map of common system commands to their apt package names. */
const GLOBAL_INSTALL_MAP: Record<string, string> = {
  python3: "python3", python: "python3", pip: "python3-pip", pip3: "python3-pip",
  node: "nodejs", npm: "npm", npx: "npm",
  gcc: "gcc", "g++": "g++", make: "make",
  go: "golang-go", rustc: "rustc", cargo: "cargo",
  java: "default-jdk", javac: "default-jdk",
  git: "git", curl: "curl", wget: "wget",
};


/* ------------------------------------------------------------------ */
/*  Provider                                                          */
/* ------------------------------------------------------------------ */

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "alpiecode.chatView";

  private _view?: vscode.WebviewView;
  private _abortStream?: () => void;

  private _conversations: Conversation[] = [];
  private _activeId: string | null = null;

  /** Pending change awaiting user approval (edit to existing file). */
  private _pendingChange: PendingChange | null = null;

  /** Auto-fix retry counter to prevent infinite loops. */
  private _autoFixRetries = 0;

  /** Track whether GitHub push has been prompted for the current project/session. */
  private _gitPushPrompted = false;

  /** Token & Speed Meter state. */
  private _tokenCount = 0;
  private _streamStartTime = 0;
  private _statsInterval?: ReturnType<typeof setInterval>;
  private _sessionTokenTotal = 0;

  constructor(
    private readonly _extUri: vscode.Uri,
    private readonly _ctx: vscode.ExtensionContext
  ) {
    this._loadHistory();
  }

  /* ---- Lifecycle ---- */

  public resolveWebviewView(
    wv: vscode.WebviewView,
    _c: vscode.WebviewViewResolveContext,
    _t: vscode.CancellationToken
  ) {
    this._view = wv;

    wv.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this._extUri, "media")],
    };

    wv.webview.html = this._html(wv.webview);
    wv.webview.onDidReceiveMessage((m) => this._onMessage(m));
    wv.onDidDispose(() => {
      this._abort();
      if (this._healthInterval) {
        clearInterval(this._healthInterval);
        this._healthInterval = undefined;
      }
      this._view = undefined;
    });

    this._startHealthMonitoring();

    // Track active editor to provide instant file context chip
    const activeDocDis = vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && editor.document) {
        const filePath = vscode.workspace.asRelativePath(editor.document.uri);
        const fileName = path.basename(filePath);
        const lang = editor.document.languageId;
        this._post({
          action: "activeFileContext",
          data: { filePath, fileName, lang }
        });
      }
    });
    this._ctx.subscriptions.push(activeDocDis);

    // Initial context check
    if (vscode.window.activeTextEditor?.document) {
      const doc = vscode.window.activeTextEditor.document;
      const filePath = vscode.workspace.asRelativePath(doc.uri);
      const fileName = path.basename(filePath);
      const lang = doc.languageId;
      setTimeout(() => {
        this._post({
          action: "activeFileContext",
          data: { filePath, fileName, lang }
        });
      }, 300);
    }

    // Track active editor selection to provide instant context chips
    const selDis = vscode.window.onDidChangeTextEditorSelection((e) => {
      const editor = e.textEditor;
      if (!editor || !editor.selection || editor.selection.isEmpty) {
        this._post({ action: "clearSelectionContext" });
        return;
      }
      const sel = editor.selection;
      const text = editor.document.getText(sel);
      if (!text || text.trim().length === 0) {
        this._post({ action: "clearSelectionContext" });
        return;
      }
      const fileName = path.basename(editor.document.fileName);
      const range = `${sel.start.line + 1}-${sel.end.line + 1}`;
      this._post({
        action: "updateSelectionContext",
        data: {
          fileName,
          range,
          snippet: text.slice(0, 4000)
        }
      });
    });
    this._ctx.subscriptions.push(selDis);

    // Start fresh by default; populate the history drawer with past conversations
    this._activeId = null;
    setTimeout(() => {
      this._pushHistoryList();
    }, 200);
  }

  /* ---- Public (called from code actions) ---- */

  public sendTask(task: string, image?: string) {
    if (!this._view) {
      vscode.window.showErrorMessage("AlpieCode panel not open.");
      return;
    }
    this._view.show?.(true);
    this._post({ action: "userMessage", text: task, image });
    this._stream(task, image);
  }

  /* ---- Streaming ---- */

  private async _stream(task: string, image?: string, reasoningLevel?: "thinking" | "no-thinking" | "high" | "medium" | "low" | string) {
    this._abort();

    if (!this._activeId) { this._newConv(task); }
    const conv = this._activeConv();
    if (!conv) { return; }

    conv.messages.push({ role: "user", content: task, image, timestamp: Date.now() });
    this._saveHistory();

    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    // Proactively verify server is reachable, auto-start if needed
    const health = await checkHealth(url);
    if (!health) {
      this._post({ action: "buildStatus", status: "rephrasing", message: "Starting AlpieCode API server..." });
      const started = await this.startServer();
      if (!started) {
        this._post({ action: "streamEnd" });
        this._post({
          action: "agentEvent",
          event: {
            type: "error",
            data: {
              error: `AlpieCode API server is offline at ${url}.\nPlease run 'alpiecode serve' in terminal or click 'Start Server' in the top header.`,
            },
          },
        });
        return;
      }
    }

    const workdir = this._workdir();

    this._post({ action: "streamStart" });
    this._post({ action: "buildStatus", status: "rephrasing", message: "Solidifying prompt requirements..." });

    // Token meter: reset counters
    this._tokenCount = 0;
    this._streamStartTime = Date.now();
    if (this._statsInterval) { clearInterval(this._statsInterval); }
    this._statsInterval = setInterval(() => this._pushTokenStats(), 500);

    let assistantBuf = "";
    this._modifiedFiles = [];
    this._fileStats = {};
    this._executedCommands = [];

    this._abortStream = streamChat(
      url,
      { task, workdir, sessionId: conv.sessionId, image, reasoningLevel },
      (ev) => {
        if (ev.type === "start" && ev.data.session_id) {
          conv.sessionId = ev.data.session_id;
        }
        if (ev.type === "message" || ev.type === "token" || ev.type === "thinking_delta" || ev.type === "thinking") {
          const chunk = ev.data.content || ev.data.text || ev.data.delta || "";
          if (ev.type === "message" || ev.type === "token") {
            assistantBuf += chunk;
          }
          if (chunk) {
            this._tokenCount += Math.max(1, Math.ceil(chunk.length / 3.5));
          }
        }
        if (ev.type === "status") {
          this._post({ action: "buildStatus", status: ev.data.phase || "building", message: ev.data.message || "" });
        }
        if (ev.type === "tool_call") {
          this._handleToolCall(workdir, ev.data);
          const toolName = ev.data.name || "";
          let phase = "building";
          if (toolName === "write_file" || toolName === "edit_file") { phase = "files"; }
          else if (toolName === "bash") { phase = "verify"; }
          else if (toolName === "update_plan") { phase = "plan"; }
          this._post({ action: "buildStatus", status: phase, message: this._toolBuildingDesc(ev.data) });
        }
        if (ev.type === "walkthrough") {
          this._handleWalkthroughEvent(workdir, ev.data);
        }
        this._post({ action: "agentEvent", event: ev });
      },
      (err) => {
        this._post({
          action: "agentEvent",
          event: { type: "error", data: { error: err.message } },
        });
      },
      () => {
        if (assistantBuf) {
          conv.messages.push({ role: "assistant", content: assistantBuf, timestamp: Date.now() });
        }
        this._saveHistory();
        // Token meter: stop interval, push final stats
        if (this._statsInterval) { clearInterval(this._statsInterval); this._statsInterval = undefined; }
        this._sessionTokenTotal += this._tokenCount;
        this._pushTokenStats();
        this._post({ action: "streamEnd" });
        this._post({ action: "buildStatus", status: "complete", message: "Build completed" });
        this._abortStream = undefined;

        // Emit Antigravity-style completion Walkthrough Card
        const uniqueFiles = [...new Set(this._modifiedFiles)];
        if (uniqueFiles.length > 0 || this._executedCommands.length > 0) {
          this._handleWalkthroughEvent(workdir, {
            summary: "Changes completed for: " + task,
            files: uniqueFiles,
            commands: this._executedCommands,
            fileStats: this._fileStats
          });
        }

        // Auto-run generated code in sandbox terminal (only if no pending approval)
        if (this._modifiedFiles.length > 0 && !this._pendingChange) {
          this._sandboxRun(workdir);
        }
      }
    );
  }

  private _abort() {
    if (this._abortStream) { this._abortStream(); this._abortStream = undefined; }
  }

  /* ---- File Change Handling (Two-Mode) ---- */

  /** Files modified during the current stream (for sandbox auto-run). */
  private _modifiedFiles: string[] = [];
  private _fileStats: Record<string, { added: number; removed: number }> = {};
  private _executedCommands: Array<{ command: string; exitCode?: number }> = [];

  private async _handleToolCall(workdir: string, data: any) {
    const name = data.name;
    let args = data.arguments;
    if (typeof args === "string") {
      try { args = JSON.parse(args); } catch { args = {}; }
    }
    if (!args || !args.path) { return; }

    const relPath: string = args.path;
    const absPath = this._toLocalPath(relPath);
    const showDiffPreview = vscode.workspace
      .getConfiguration("alpiecode")
      .get<boolean>("showDiffPreview", false);

    if (name === "write_file") {
      const content = args.content || "";
      const dir = path.dirname(absPath);
      if (!fs.existsSync(dir)) { fs.mkdirSync(dir, { recursive: true }); }

      // Calculate line changes
      const existingText = fs.existsSync(absPath) ? (fs.readFileSync(absPath, "utf-8") || "") : "";
      const oldLineCount = existingText ? existingText.split("\n").length : 0;
      const newLineCount = content.split("\n").length;
      const added = Math.max(0, newLineCount - oldLineCount) || newLineCount;
      const removed = Math.max(0, oldLineCount - newLineCount);
      this._fileStats[relPath] = { added, removed };

      if (!showDiffPreview) {
        // Direct write mode: write directly without asking for accept approval
        fs.writeFileSync(absPath, content, "utf-8");
        try {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
          await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
        } catch {}
        this._modifiedFiles.push(relPath);
        this._autoFixRetries = 0;
      } else {
        const fileExists = fs.existsSync(absPath);
        let existingContent = "";
        if (fileExists) {
          try { existingContent = fs.readFileSync(absPath, "utf-8"); } catch {}
        }
        if (!fileExists) {
          fs.writeFileSync(absPath, content, "utf-8");
          try {
            const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
            await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
          } catch {}
          this._modifiedFiles.push(relPath);
          this._autoFixRetries = 0;
        } else {
          this._pendingChange = {
            workdir, relPath, absPath, newContent: content,
            oldContent: existingContent, toolName: "write_file", isNewFile: false
          };
          this._sendChangePlan();
        }
      }

    } else if (name === "edit_file") {
      let existing = "";
      try { existing = fs.readFileSync(absPath, "utf-8"); } catch {}
      const oldStr = args.old_str || "";
      const newStr = args.new_str || "";
      const newContent = oldStr ? existing.replace(oldStr, newStr) : newStr;

      const editOldLines = oldStr ? oldStr.split("\n").length : 0;
      const editNewLines = newStr ? newStr.split("\n").length : 0;
      this._fileStats[relPath] = { added: editNewLines, removed: editOldLines };

      if (!showDiffPreview) {
        // Direct edit mode: write directly without asking for accept approval
        const dir = path.dirname(absPath);
        if (!fs.existsSync(dir)) { fs.mkdirSync(dir, { recursive: true }); }
        fs.writeFileSync(absPath, newContent, "utf-8");
        try {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
          await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
        } catch {}
        this._modifiedFiles.push(relPath);
      } else {
        this._pendingChange = {
          workdir, relPath, absPath, newContent,
          oldContent: existing, toolName: "edit_file", isNewFile: false,
          oldStr, newStr
        };
        this._sendChangePlan();
      }
    }
  }

  /** Send a change plan card to the webview for user approval. */
  private _sendChangePlan() {
    if (!this._pendingChange) { return; }
    const pc = this._pendingChange;

    // Build a simple line-level diff for the webview
    const oldLines = pc.oldContent.split("\n");
    const newLines = pc.newContent.split("\n");
    const diffLines: { type: string; text: string }[] = [];

    // Simple diff: show removed and added lines
    if (pc.oldStr && pc.newStr) {
      // For edit_file: show the specific old_str → new_str change
      pc.oldStr.split("\n").forEach(l => diffLines.push({ type: "removed", text: l }));
      pc.newStr.split("\n").forEach(l => diffLines.push({ type: "added", text: l }));
    } else {
      // For write_file overwrite: show first few changed lines
      const maxLines = 20;
      let changes = 0;
      for (let i = 0; i < Math.max(oldLines.length, newLines.length) && changes < maxLines; i++) {
        if (i < oldLines.length && i < newLines.length && oldLines[i] === newLines[i]) {
          continue; // skip identical lines
        }
        if (i < oldLines.length) { diffLines.push({ type: "removed", text: oldLines[i] }); changes++; }
        if (i < newLines.length) { diffLines.push({ type: "added", text: newLines[i] }); changes++; }
      }
      if (changes >= maxLines) {
        diffLines.push({ type: "info", text: "... (more changes)" });
      }
    }

    this._post({
      action: "changePlan",
      data: {
        fileName: pc.relPath,
        toolName: pc.toolName,
        diff: diffLines,
        isNewFile: pc.isNewFile,
        summary: pc.toolName === "edit_file"
          ? "Edit: replacing code in " + pc.relPath
          : "Overwrite: replacing contents of " + pc.relPath
      }
    });
  }

  /** Open VS Code native side-by-side diff editor between current file and proposed change. */
  private async _openSideBySideDiff() {
    if (!this._pendingChange) { return; }
    const pc = this._pendingChange;
    try {
      const originalUri = vscode.Uri.file(pc.absPath);
      const tempPath = path.join(os.tmpdir(), "alpie_proposed_" + path.basename(pc.absPath));
      fs.writeFileSync(tempPath, pc.newContent, "utf-8");
      const proposedUri = vscode.Uri.file(tempPath);
      await vscode.commands.executeCommand(
        "vscode.diff",
        originalUri,
        proposedUri,
        `${path.basename(pc.absPath)} (Current ↔ Proposed Edits)`
      );
    } catch (err: any) {
      vscode.window.showErrorMessage("Could not open diff viewer: " + (err?.message || err));
    }
  }

  /** Apply the pending change to disk. */
  private _applyPendingChange() {
    if (!this._pendingChange) { return; }
    const pc = this._pendingChange;

    const dir = path.dirname(pc.absPath);
    if (!fs.existsSync(dir)) { fs.mkdirSync(dir, { recursive: true }); }
    fs.writeFileSync(pc.absPath, pc.newContent, "utf-8");

    // Open the file in editor
    vscode.workspace.openTextDocument(vscode.Uri.file(pc.absPath)).then(doc => {
      vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
    });

    this._modifiedFiles.push(pc.relPath);
    const workdir = pc.workdir;
    this._pendingChange = null;

    this._post({ action: "changeApplied", fileName: pc.relPath });

    // Auto-run after applying the change
    this._sandboxRun(workdir);
  }

  /* ---- Sandbox Execution ---- */
  private _runInTerminal(cmd: string, workdir: string) {
    let term = vscode.window.terminals.find(t => t.name === "AlpieCode Sandbox");
    if (!term) {
      term = vscode.window.createTerminal({
        name: "AlpieCode Sandbox",
      });
    }
    term.show(true);
    if (this._isWslWorkspace()) {
      term.sendText("wsl -d Ubuntu --cd \"" + workdir + "\" " + cmd);
    } else {
      term.sendText("cd \"" + workdir + "\" && " + cmd);
    }
  }


  private _detectRunCommand(files: string[], workdir: string): string | null {
    const mainPatterns = ["main", "app", "index", "server", "game"];
    const sorted = [...files].sort((a, b) => {
      const aBase = path.basename(a, path.extname(a)).toLowerCase();
      const bBase = path.basename(b, path.extname(b)).toLowerCase();
      const aMain = mainPatterns.some(p => aBase.includes(p)) ? 0 : 1;
      const bMain = mainPatterns.some(p => bBase.includes(p)) ? 0 : 1;
      return aMain - bMain;
    });

    for (const f of sorted) {
      const ext = path.extname(f).toLowerCase();
      const localF = this._toLocalPath(f);
      if (!fs.existsSync(localF)) { continue; }

      if (ext === ".py") {
        const venvPyBin = this._toLocalPath(path.join(".venv", "bin", "python3"));
        const venvPy = this._toLocalPath(path.join(".venv", "bin", "python"));
        const venvPyWin = this._toLocalPath(path.join(".venv", "Scripts", "python.exe"));

        if (fs.existsSync(venvPyBin)) {
          return ".venv/bin/python3 \"" + f + "\"";
        } else if (fs.existsSync(venvPy)) {
          return ".venv/bin/python \"" + f + "\"";
        } else if (fs.existsSync(venvPyWin)) {
          return ".venv\\Scripts\\python.exe \"" + f + "\"";
        }
        return (this._isWslWorkspace() || process.platform !== "win32") ? "python3 \"" + f + "\"" : "python \"" + f + "\"";
      }
      if (ext === ".js")   { return "node \"" + f + "\""; }
      if (ext === ".ts")   { return "npx ts-node \"" + f + "\""; }
      if (ext === ".cpp")  {
        const out = f.replace(/\.cpp$/, "");
        return "g++ -Wall -Wextra -std=c++17 -o \"" + out + "\" \"" + f + "\" && ./\"" + out + "\"";
      }
      if (ext === ".c")    {
        const out = f.replace(/\.c$/, "");
        return "gcc -Wall -Wextra -o \"" + out + "\" \"" + f + "\" && ./\"" + out + "\"";
      }
      if (ext === ".rs")   { return "rustc \"" + f + "\" -o main && ./main"; }
      if (ext === ".go")   { return "go run \"" + f + "\""; }
      if (ext === ".java") {
        const cls = path.basename(f, ".java");
        return "javac \"" + f + "\" && java \"" + cls + "\"";
      }
      if (ext === ".sh")   { return "bash \"" + f + "\""; }
      if (ext === ".html") { return null; }
    }
    return null;
  }

  private async _sandboxRun(workdir: string) {
    const autoRun = vscode.workspace
      .getConfiguration("alpiecode")
      .get<boolean>("autoRun", true);
    if (!autoRun) {
      this._promptGitPush(workdir);
      return;
    }

    const files = [...new Set(this._modifiedFiles)];
    if (files.length === 0) { return; }

    // Proactively check for missing dependencies before execution
    const missingPrompted = await this._checkFileDependencies(workdir, files);
    if (missingPrompted) {
      return; // Awaiting user decision on dependency installation
    }

    const runCmd = this._detectRunCommand(files, workdir);
    if (!runCmd) {
      this._promptGitPush(workdir);
      return;
    }

    const autoFix = vscode.workspace
      .getConfiguration("alpiecode")
      .get<boolean>("autoFix", true);

    const task = new vscode.Task(
      { type: "alpiecode-sandbox" },
      vscode.TaskScope.Workspace,
      "AlpieCode Sandbox",
      "AlpieCode",
      this._wslShellExec(runCmd, workdir)
    );
    task.presentationOptions = {
      reveal: vscode.TaskRevealKind.Always,
      panel: vscode.TaskPanelKind.Dedicated,
      focus: true,
      clear: true,
      echo: true,
    };

    this._post({
      action: "agentEvent",
      event: { type: "message", data: { content: "\n⚡ **Running in Terminal**: `" + runCmd + "`\n" } }
    });

    const execution = await vscode.tasks.executeTask(task);

    const disposable = vscode.tasks.onDidEndTaskProcess((e) => {
      if (e.execution === execution) {
        disposable.dispose();
        this._executedCommands.push({ command: runCmd, exitCode: e.exitCode || 0 });
        if (e.exitCode !== 0) {
          // Smart dep detection: check for missing packages BEFORE auto-fix
          this._detectMissingDep(workdir, files, runCmd).then(dep => {
            if (dep) {
              this._promptInstallDep(dep, workdir, files, runCmd);
            } else if (autoFix) {
              this._autoFixError(workdir, files, runCmd, e.exitCode || 1);
            }
          });
        } else {
          this._autoFixRetries = 0; // reset on success
          vscode.window.showInformationMessage("AlpieCode: Code executed successfully!");
          this._promptGitPush(workdir);
        }
      }
    });
  }

  private _autoFixError(workdir: string, files: string[], runCmd: string, exitCode: number) {
    // Guard: prevent infinite auto-fix loops
    this._autoFixRetries++;
    if (this._autoFixRetries > MAX_AUTO_FIX_RETRIES) {
      this._autoFixRetries = 0;
      this._post({
        action: "agentEvent",
        event: {
          type: "error",
          data: { error: "Auto-fix limit reached (" + MAX_AUTO_FIX_RETRIES + " attempts). Please fix the remaining errors manually." }
        }
      });
      vscode.window.showWarningMessage(
        "AlpieCode: Auto-fix limit reached after " + MAX_AUTO_FIX_RETRIES + " attempts. Please review the code manually."
      );
      return;
    }

    const errors: string[] = [];
    for (const f of files) {
      const absPath = path.isAbsolute(f) ? f : path.join(workdir, f);
      const uri = vscode.Uri.file(absPath);
      const diags = vscode.languages.getDiagnostics(uri);
      for (const d of diags) {
        if (d.severity === vscode.DiagnosticSeverity.Error) {
          errors.push(f + ":" + (d.range.start.line + 1) + ": " + d.message);
        }
      }
    }

    const errorSummary = errors.length > 0
      ? errors.slice(0, 10).join("\n")
      : "Command \"" + runCmd + "\" failed with exit code " + exitCode;

    let fixPrompt = "The code has errors (attempt " + this._autoFixRetries + "/" + MAX_AUTO_FIX_RETRIES + "). Fix them precisely.\n\n";
    fixPrompt += "Command: " + runCmd + "\nExit code: " + exitCode + "\n";
    if (errors.length > 0) {
      fixPrompt += "\nErrors:\n" + errorSummary;
    } else {
      fixPrompt += "\nThe command failed. Read the file, find the bug, and fix it.";
    }
    fixPrompt += "\n\nFiles: " + files.join(", ");

    setTimeout(() => {
      this._post({ action: "userMessage", text: "Auto-fixing errors (attempt " + this._autoFixRetries + "/" + MAX_AUTO_FIX_RETRIES + ")..." });
      this._stream(fixPrompt);
    }, 1500);
  }


  /* ---- Smart Dependency Detection ---- */
  /**
   * Proactively scan created/modified files for missing imported dependencies.
   * If a missing package is detected, triggers the install popup and returns true.
   */
  private async _checkFileDependencies(workdir: string, files: string[]): Promise<boolean> {
    for (const f of files) {
      const ext = path.extname(f).toLowerCase();
      const localPath = this._toLocalPath(f);
      if (!fs.existsSync(localPath)) { continue; }

      if (ext === ".py") {
        let content = "";
        try { content = fs.readFileSync(localPath, "utf-8"); } catch { continue; }

        // Find all imported module names
        const importRegex = /(?:^|\n)\s*(?:import|from)\s+([a-zA-Z0-9_]+)/g;
        const matches = new Set<string>();
        let match;
        while ((match = importRegex.exec(content)) !== null) {
          const mod = match[1];
          const localModPy = this._toLocalPath(mod + ".py");
          const localModDir = this._toLocalPath(mod);
          if (!PYTHON_STDLIB.has(mod) && !fs.existsSync(localModPy) && !fs.existsSync(localModDir)) {
            matches.add(mod);
          }
        }

        const venvPyBin = this._toLocalPath(path.join(".venv", "bin", "python3"));
        const venvPy = this._toLocalPath(path.join(".venv", "bin", "python"));
        const venvPyWin = this._toLocalPath(path.join(".venv", "Scripts", "python.exe"));

        let pyRunner = (this._isWslWorkspace() || process.platform !== "win32") ? "python3" : "python";
        if (fs.existsSync(venvPyBin)) {
          pyRunner = ".venv/bin/python3";
        } else if (fs.existsSync(venvPy)) {
          pyRunner = ".venv/bin/python";
        } else if (fs.existsSync(venvPyWin)) {
          pyRunner = ".venv\\Scripts\\python.exe";
        }

        for (const mod of matches) {
          let canImport = false;
          try {
            this._execSync(`${pyRunner} -c "import ${mod}"`, workdir, 3000);
            canImport = true;
          } catch {
            canImport = false;
          }

          if (!canImport) {
            const dep: MissingDep = {
              name: mod,
              type: "pylib",
              installCmd: `pip install ${mod}`
            };
            const runCmd = this._detectRunCommand(files, workdir) || `${pyRunner} "${f}"`;
            await this._promptInstallDep(dep, workdir, files, runCmd);
            return true; // Prompted -> pause auto-run until user responds
          }
        }
      }
    }
    return false;
  }


  /**
   * Detect missing dependencies by re-running the command briefly to capture stderr.
   * Missing import errors happen instantly (before any side effects), so this is safe.
   */
  private async _detectMissingDep(
    workdir: string, files: string[], runCmd: string
  ): Promise<MissingDep | null> {
    // 1. Check if the command binary itself is missing
    const cmdBin = runCmd.split(/\s+/)[0].replace(/"/g, "");
    try {
      this._execSync("which " + cmdBin, workdir, 2000);
    } catch {
      const aptPkg = GLOBAL_INSTALL_MAP[cmdBin] || cmdBin;
      return { name: cmdBin, type: "global", installCmd: "sudo apt install -y " + aptPkg };
    }

    // 2. Quick re-run to capture stderr (fails instantly on missing imports)
    try {
      this._execSync(runCmd, workdir, 8000);
      return null; // command succeeded — no missing dep
    } catch (err: any) {
      const output = (err.stderr || "") + "\n" + (err.stdout || "");

      // Python: ModuleNotFoundError / ImportError
      const pyMatch = output.match(/(?:ModuleNotFoundError|ImportError):\s*No module named\s*'([^']+)'/);
      if (pyMatch) {
        const modName = pyMatch[1].split(".")[0];
        if (PYTHON_STDLIB.has(modName)) { return null; } // stdlib — not a missing dep
        return { name: modName, type: "pylib", installCmd: "pip install " + modName };
      }

      // Node.js: Cannot find module
      const nodeMatch = output.match(/Cannot find module '([^']+)'/);
      if (nodeMatch) {
        const pkg = nodeMatch[1];
        if (pkg.startsWith(".") || pkg.startsWith("/")) { return null; } // local file
        return { name: pkg, type: "npm", installCmd: "npm install " + pkg };
      }

      // C/C++: fatal error: X.h: No such file or directory
      const cMatch = output.match(/fatal error:\s*(\S+\.h):\s*No such file or directory/);
      if (cMatch) {
        return { name: cMatch[1], type: "global", installCmd: "sudo apt install -y build-essential" };
      }

      return null; // no recognizable pattern
    }
  }

  /**
   * Show a VS Code popup asking the user whether to install a missing dependency.
   * For Python libraries: also offers virtual environment creation.
   */
  private async _promptInstallDep(
    dep: MissingDep, workdir: string, files: string[], runCmd: string
  ) {
    const isWinNative = !this._isWslWorkspace() && process.platform === "win32";
    if (dep.type === "pylib") {
      // Check if a venv already exists in the workdir using host-local path
      const venvFolder = this._toLocalPath(".venv");
      const venvExists = fs.existsSync(venvFolder);

      if (venvExists) {
        // Venv exists — offer to install inside it
        const choice = await vscode.window.showInformationMessage(
          `📦 Python package '${dep.name}' is not installed. Install into .venv?`,
          { modal: false },
          "Install in .venv",
          "Install Globally",
          "Skip"
        );
        if (choice === "Install in .venv") {
          let installCmd = "";
          if (isWinNative) {
            installCmd = ".venv\\Scripts\\pip install " + dep.name;
          } else {
            // In WSL / Linux / macOS: check uv, or venv pip, or python -m pip
            installCmd = `(command -v uv >/dev/null 2>&1 && uv pip install --python .venv ${dep.name}) || (.venv/bin/pip install ${dep.name}) || (.venv/bin/python3 -m pip install ${dep.name})`;
          }
          this._runInstallTask(installCmd, workdir, files, runCmd);
        } else if (choice === "Install Globally") {
          const pipCmd = isWinNative ? `pip install ${dep.name}` : `python3 -m pip install --user ${dep.name} || pip install ${dep.name}`;
          this._runInstallTask(pipCmd, workdir, files, runCmd);
        }
      } else {
        // No venv — offer to create one
        const choice = await vscode.window.showInformationMessage(
          `📦 '${dep.name}' is not installed.\n🐍 No virtual environment found. Create one?`,
          { modal: false },
          "Create .venv & Install",
          "Install Globally",
          "Skip"
        );
        if (choice === "Create .venv & Install") {
          let cmd = "";
          if (isWinNative) {
            cmd = `python -m venv .venv && .venv\\Scripts\\pip install ${dep.name}`;
          } else {
            // In WSL / Linux / macOS: prefer uv if available, or python3 -m venv with pip fallback
            cmd = `(command -v uv >/dev/null 2>&1 && uv venv .venv && uv pip install --python .venv ${dep.name}) || (python3 -m venv .venv && .venv/bin/pip install ${dep.name}) || (python3 -m pip install --user ${dep.name})`;
          }
          this._runInstallTask(cmd, workdir, files, runCmd);
        } else if (choice === "Install Globally") {
          const pipCmd = isWinNative ? `pip install ${dep.name}` : `python3 -m pip install --user ${dep.name} || pip install ${dep.name}`;
          this._runInstallTask(pipCmd, workdir, files, runCmd);
        }
      }

    } else if (dep.type === "npm") {
      const choice = await vscode.window.showInformationMessage(
        `📦 Node package '${dep.name}' is not installed.`,
        { modal: false },
        "Install (npm install)",
        "Skip"
      );
      if (choice === "Install (npm install)") {
        this._runInstallTask("npm install " + dep.name, workdir, files, runCmd);
      }

    } else if (dep.type === "global") {
      const choice = await vscode.window.showInformationMessage(
        `⚠️ System tool '${dep.name}' is not installed.`,
        { modal: false },
        "Install (" + dep.installCmd + ")",
        "Skip"
      );
      if (choice?.startsWith("Install")) {
        this._runInstallTask(dep.installCmd, workdir, files, runCmd);
      }
    }
  }

  /**
   * Run an install command in a VS Code terminal task.
   * On success, automatically re-runs the original sandbox command.
   */
  private async _runInstallTask(
    installCmd: string, workdir: string, files: string[], thenRunCmd: string
  ) {
    this._post({
      action: "agentEvent",
      event: { type: "message", data: { content: "\n📦 Installing: `" + installCmd + "`\n" } }
    });

    const installTask = new vscode.Task(
      { type: "alpiecode-install" },
      vscode.TaskScope.Workspace,
      "AlpieCode Install",
      "AlpieCode",
      this._wslShellExec(installCmd, workdir)
    );
    installTask.presentationOptions = {
      reveal: vscode.TaskRevealKind.Always,
      panel: vscode.TaskPanelKind.Shared,
      focus: true,
    };

    const execution = await vscode.tasks.executeTask(installTask);

    const disposable = vscode.tasks.onDidEndTaskProcess((e) => {
      if (e.execution === execution) {
        disposable.dispose();
        if (e.exitCode === 0) {
          vscode.window.showInformationMessage("✅ Installation complete! Re-running code...");
          this._post({
            action: "agentEvent",
            event: { type: "message", data: { content: "\n✅ Installation successful! Re-running...\n" } }
          });
          // Re-run the original sandbox command
          this._modifiedFiles = [...files];
          this._sandboxRun(workdir);
        } else {
          vscode.window.showErrorMessage("❌ Installation failed (exit code " + e.exitCode + "). Please install manually.");
        }
      }
    });
  }


  /* ---- Multimodal Image Picker ---- */

  private async _pickImage() {
    const uris = await vscode.window.showOpenDialog({
      canSelectFiles: true,
      canSelectFolders: false,
      canSelectMany: false,
      openLabel: "Attach Image",
      filters: {
        Images: ["png", "jpg", "jpeg", "webp", "svg", "gif"]
      }
    });

    if (!uris || uris.length === 0) { return; }

    const uri = uris[0];
    const filePath = uri.fsPath;
    const fileName = path.basename(filePath);

    try {
      const ext = path.extname(filePath).toLowerCase().replace(".", "");
      const mimeType = ext === "svg" ? "image/svg+xml" : (ext === "jpg" ? "image/jpeg" : "image/" + ext);
      const fileBytes = fs.readFileSync(filePath);
      const base64 = fileBytes.toString("base64");
      const dataUrl = "data:" + mimeType + ";base64," + base64;

      this._post({
        action: "imageAttached",
        path: filePath,
        dataUrl,
        name: fileName
      });
    } catch (err: any) {
      vscode.window.showErrorMessage("Failed to load image: " + (err?.message || err));
    }
  }

  /* ---- Message handler ---- */

  private _onMessage(m: any) {
    switch (m.action) {
      case "sendMessage":
        this._autoFixRetries = 0; // reset retries on new user message
        this._post({ action: "userMessage", text: m.text, image: m.image });
        this._stream(m.text, m.image, m.reasoningLevel);
        break;
      case "attachImage":
        this._pickImage();
        break;
      case "acceptChange":
        this._applyPendingChange();
        break;
      case "rejectChange":
        this._pendingChange = null;
        this._post({ action: "changeRejected" });
        break;
      case "openDiff":
        this._openSideBySideDiff();
        break;
      case "editRequest":
        this._pendingChange = null;
        if (m.text) {
          this._post({ action: "userMessage", text: m.text });
          this._stream(m.text);
        }
        break;
      case "cancelStream":
        this._abort();
        this._post({ action: "streamEnd" });
        break;
      case "checkStatus":
        this._healthCheck();
        break;
      case "startServer":
        this.startServer();
        break;
      case "newChat":
        this._abort();
        this._activeId = null;
        this._pendingChange = null;
        this._autoFixRetries = 0;
        this._saveHistory();
        this._pushHistoryList();
        break;
      case "loadConversation":
        this._abort();
        this._restoreConv(m.id);
        break;
      case "deleteConversation":
        this._deleteConv(m.id);
        break;
      case "getHistory":
        this._pushHistoryList();
        break;
      case "confirmGitPush":
        this._executeGitPush(m.workdir || this._workdir(), m.username, m.branch);
        break;
      case "dismissGitPush":
        this._gitPushPrompted = true;
        break;
      case "requestGitPush":
        this._promptGitPush(this._workdir(), true);
        break;
      case "insertCodeAtCursor":
        this._insertCodeAtCursor(m.code);
        break;
            case "openWalkthrough":
        this._openMarkdownPreview(m.path || "walkthrough.md");
        break;
      case "openDiffForFile":
        this._openDiffForFile(m.path);
        break;
      case "fixDiagnostics":
        this._handleFixDiagnostics();
        break;
      case "rollbackChanges":
        this._handleRollbackChanges();
        break;
      case "reviewChanges":
        this._openReviewChanges();
        break;
      case "openFile":
        this._openFileInEditor(m.path);
        break;
      case "insertCodeAtCursor":
        this._insertCodeAtCursor(m.code);
        break;
      case "copyToClipboard":
        if (m.text) { vscode.env.clipboard.writeText(m.text); }
        break;
      case "changeGitUsername":
        this._handleChangeGitUsername(m.workdir || this._workdir(), m.currentUsername, m.branch);
        break;
      case "dismissGitPush":
        this._post({
          action: "agentEvent",
          event: { type: "message", data: { content: "ℹ️ GitHub push skipped. Local changes saved." } }
        });
        break;
    }
  }



  private _handleWalkthroughEvent(workdir: string, data: any) {
    const summary = data.summary || "Completed project changes.";
    const files = data.files || [];
    const commands = data.commands || [];

    // Ensure walkthrough.md is written to disk in the workspace
    const localWalkthrough = this._toLocalPath("walkthrough.md");
    try {
      let content = `# Walkthrough\n\n## Summary\n${summary}\n\n## Changes Made\n`;
      if (files.length > 0) {
        files.forEach((f: string) => { content += `- \`${f}\`\n`; });
      } else {
        content += `- (No files changed)\n`;
      }
      if (commands.length > 0) {
        content += `\n## Verification\n`;
        commands.forEach((c: any) => { content += `- \`${c.command || c.cmd || c}\` (Verified)\n`; });
      }
      fs.writeFileSync(localWalkthrough, content, "utf-8");
    } catch {}

    this._post({
      action: "walkthrough",
      data: {
        path: "walkthrough.md",
        summary,
        files: [...new Set(files.concat(this._modifiedFiles))],
        commands: commands.length > 0 ? commands : this._executedCommands,
        fileStats: data.fileStats || this._fileStats
      }
    });
  }

  /* ---- Editor & Source Control Integrations ---- */

  /** Open VS Code native side-by-side diff for any file against git HEAD or empty base. */
  /** Open native VS Code Markdown Preview tab (Walkthrough (preview)). */
  private async _openMarkdownPreview(filePath: string) {
    if (!filePath) { filePath = "walkthrough.md"; }
    const local = this._toLocalPath(filePath);

    // If walkthrough.md does not exist on disk yet, generate it so it can be viewed
    if (!fs.existsSync(local)) {
      if (path.basename(local).toLowerCase() === "walkthrough.md") {
        try {
          const files = [...new Set(this._modifiedFiles)];
          const cmds = this._executedCommands;
          let content = `# Walkthrough\n\n## Summary\nCompleted project changes.\n\n## Changes Made\n`;
          if (files.length > 0) {
            files.forEach((f: string) => { content += `- \`${f}\`\n`; });
          } else {
            content += `- (No files changed)\n`;
          }
          if (cmds.length > 0) {
            content += `\n## Verification\n`;
            cmds.forEach((c: any) => { content += `- \`${c.command || c.cmd || c}\` (Verified)\n`; });
          }
          fs.writeFileSync(local, content, "utf-8");
        } catch (err) {
          vscode.window.showWarningMessage(`Could not generate ${filePath}: ${err}`);
          return;
        }
      } else {
        vscode.window.showWarningMessage(`File not found: ${filePath}`);
        return;
      }
    }

    const uri = vscode.Uri.file(local);
    try {
      await vscode.commands.executeCommand("markdown.showPreview", uri);
    } catch {
      try {
        await vscode.commands.executeCommand("markdown.showPreviewToSide", uri);
      } catch {
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.One });
      }
    }
  }

  private async _openDiffForFile(relPath: string) {
    if (!relPath) return;
    const absPath = this._toLocalPath(relPath);
    if (!fs.existsSync(absPath)) return;

    try {
      const workdir = this._workdir();
      let headContent = "";
      try {
        headContent = this._execSync(`git show HEAD:"${relPath}"`, workdir, 2500);
      } catch {
        headContent = "";
      }

      const tempDir = os.tmpdir();
      const headTempPath = path.join(tempDir, `head_${path.basename(relPath)}`);
      fs.writeFileSync(headTempPath, headContent, "utf-8");

      await vscode.commands.executeCommand(
        "vscode.diff",
        vscode.Uri.file(headTempPath),
        vscode.Uri.file(absPath),
        `${path.basename(relPath)} (HEAD ↔ Modified)`
      );
    } catch {
      this._openFileInEditor(relPath);
    }
  }

  /** Scan workspace for active compiler/linter diagnostics and auto-generate fix prompt. */
  private async _handleFixDiagnostics() {
    const allDiagnostics = vscode.languages.getDiagnostics();
    const errorList: string[] = [];

    for (const [uri, diags] of allDiagnostics) {
      const activeDiags = diags.filter(d => d.severity === vscode.DiagnosticSeverity.Error || d.severity === vscode.DiagnosticSeverity.Warning);
      if (activeDiags.length > 0) {
        const rel = vscode.workspace.asRelativePath(uri);
        if (rel.includes("node_modules") || rel.includes(".venv") || rel.startsWith("..")) continue;
        errorList.push(`\nFile: ${rel}`);
        for (const d of activeDiags.slice(0, 5)) {
          const sev = d.severity === vscode.DiagnosticSeverity.Error ? "ERROR" : "WARN";
          errorList.push(`  [Line ${d.range.start.line + 1}] [${sev}] ${d.message}`);
        }
      }
    }

    if (errorList.length === 0) {
      vscode.window.showInformationMessage("✨ No active compiler or syntax errors detected in workspace files.");
      this._post({
        action: "agentEvent",
        event: {
          type: "message",
          data: { content: "✨ **No active diagnostic errors or warnings detected in workspace files.**" }
        }
      });
      return;
    }

    const prompt = `Fix the following compilation/linter errors in the codebase:${errorList.join("\n")}\n\nInspect each file, fix the root cause, and verify.`;
    this._post({ action: "userMessage", text: "/fix - Auto-fixing active diagnostic errors..." });
    this._stream(prompt);
  }

  /** Rollback all uncommitted changes back to git HEAD. */
  private async _handleRollbackChanges() {
    const choice = await vscode.window.showWarningMessage(
      "Are you sure you want to rollback all uncommitted changes back to git HEAD?",
      { modal: true },
      "Rollback All Changes",
      "Cancel"
    );
    if (choice !== "Rollback All Changes") return;

    try {
      const workdir = this._workdir();
      this._execSync("git checkout -- .", workdir, 4000);
      vscode.window.showInformationMessage("⏪ All uncommitted modifications have been rolled back to HEAD.");
      this._post({
        action: "agentEvent",
        event: {
          type: "message",
          data: { content: "⏪ **All uncommitted modifications have been rolled back to HEAD.**" }
        }
      });
    } catch (err: any) {
      vscode.window.showErrorMessage("Rollback failed: " + (err?.message || err));
    }
  }

  private _openReviewChanges() {
    vscode.commands.executeCommand("workbench.view.scm");
    if (this._modifiedFiles.length > 0) {
      this._openFileInEditor(this._modifiedFiles[0]);
    }
  }

  private _openFileInEditor(filePath: string) {
    if (!filePath) return;
    const local = this._toLocalPath(filePath);
    if (fs.existsSync(local)) {
      vscode.workspace.openTextDocument(vscode.Uri.file(local)).then(doc => {
        vscode.window.showTextDocument(doc, { preview: true });
      });
    } else {
      vscode.window.showWarningMessage(`File not found: ${filePath}`);
    }
  }

  private _insertCodeAtCursor(code: string) {
    const editor = vscode.window.activeTextEditor;
    if (editor && code) {
      editor.edit(editBuilder => {
        editBuilder.insert(editor.selection.active, code);
      });
    }
  }

  /* ---- Live Building Log Descriptions ---- */

  private _toolBuildingDesc(data: any): string {
    const name = data.name || "action";
    let args = data.arguments;
    if (typeof args === "string") {
      try { args = JSON.parse(args); } catch { args = {}; }
    }
    if (name === "write_file") {
      return "Writing " + (args?.path || "file") + "...";
    }
    if (name === "edit_file") {
      return "Editing " + (args?.path || "file") + "...";
    }
    if (name === "read_file") {
      return "Inspecting " + (args?.path || "file") + "...";
    }
    if (name === "bash") {
      const cmd = (args?.command || "").trim();
      return "Running: " + (cmd.length > 50 ? cmd.substring(0, 47) + "..." : cmd);
    }
    if (name === "list_files") {
      return "Scanning project structure...";
    }
    return "Executing " + name + "...";
  }

  /* ---- GitHub Push Confirmation & Custom Push ID ---- */

  private _getGitUsername(workdir: string): string {
    // 1. Configured setting
    const cfgUser = vscode.workspace.getConfiguration("alpiecode").get<string>("githubUsername");
    if (cfgUser && cfgUser.trim()) { return cfgUser.trim(); }

    // 2. git config user.name
    try {
      const gitUser = this._execSync("git config user.name", workdir, 3000).trim();
      if (gitUser) { return gitUser; }
    } catch {}

    // 3. gh CLI if available
    try {
      const ghUser = this._execSync("gh api user -q .login", workdir, 4000).trim();
      if (ghUser) { return ghUser; }
    } catch {}

    // 4. OS user / fallback
    return os.userInfo().username || "developer";
  }

  private _getGitRemote(workdir: string): string | null {
    try {
      const remote = this._execSync("git remote get-url origin", workdir, 3000).trim();
      return remote || null;
    } catch {
      return null;
    }
  }

  private _getGitBranch(workdir: string): string {
    try {
      const branch = this._execSync("git rev-parse --abbrev-ref HEAD", workdir, 3000).trim();
      return branch || "main";
    } catch {
      return "main";
    }
  }

  private _promptGitPush(workdir: string, force: boolean = false) {
    const askBeforePush = vscode.workspace.getConfiguration("alpiecode").get<boolean>("askBeforePush", true);
    if (!askBeforePush && !force) { return; }
    if (this._modifiedFiles.length === 0 && !force) { return; }
    // Only ask once at last after completing the project
    if (this._gitPushPrompted && !force) { return; }
    if (this._autoFixRetries > 0) { return; }

    let isGit = false;
    try {
      this._execSync("git rev-parse --is-inside-work-tree", workdir, 3000);
      isGit = true;
    } catch {
      try {
        this._execSync("git init", workdir, 4000);
        isGit = true;
      } catch {}
    }

    if (!isGit) { return; }

    this._gitPushPrompted = true;

    const username = this._getGitUsername(workdir);
    const remote = this._getGitRemote(workdir);
    const branch = this._getGitBranch(workdir);

    this._post({
      action: "gitPushPrompt",
      data: {
        username,
        remote,
        branch,
        workdir,
        fileCount: this._modifiedFiles.length
      }
    });
  }

  private async _handleChangeGitUsername(workdir: string, currentUsername: string, branch?: string) {
    const newUsername = await vscode.window.showInputBox({
      prompt: "Enter GitHub Username / Push ID:",
      value: currentUsername || "",
      placeHolder: "e.g. octocat or your-github-handle",
      validateInput: (val) => val && val.trim().length > 0 ? null : "Username cannot be empty"
    });

    if (!newUsername || !newUsername.trim()) {
      return;
    }
    const cleaned = newUsername.trim();

    try {
      await vscode.workspace.getConfiguration("alpiecode").update("githubUsername", cleaned, vscode.ConfigurationTarget.Global);
    } catch {}

    try {
      this._execSync('git config user.name "' + cleaned + '"', workdir);
    } catch {}

    const remote = this._getGitRemote(workdir);
    const curBranch = branch || this._getGitBranch(workdir);

    this._post({
      action: "gitPushPrompt",
      data: { username: cleaned, remote, branch: curBranch, workdir, isUpdated: true }
    });
  }

  private async _executeGitPush(workdir: string, username: string, branch?: string) {
    const curBranch = branch || this._getGitBranch(workdir);
    let remote = this._getGitRemote(workdir);

    if (!remote) {
      const inputRemote = await vscode.window.showInputBox({
        prompt: "No remote 'origin' found. Enter GitHub repository URL for @" + username + ":",
        placeHolder: "https://github.com/" + username + "/my-repo.git",
        validateInput: (val) => val && val.trim().length > 0 ? null : "Repository URL cannot be empty"
      });
      if (!inputRemote || !inputRemote.trim()) {
        this._post({
          action: "agentEvent",
          event: { type: "message", data: { content: "❌ Push cancelled: No remote repository specified." } }
        });
        return;
      }
      let targetRemote = inputRemote.trim();
      if (!targetRemote.startsWith("http://") && !targetRemote.startsWith("https://") && !targetRemote.startsWith("git@")) {
        targetRemote = "https://github.com/" + targetRemote + ".git";
      }
      try {
        this._execSync("git remote add origin " + targetRemote, workdir);
        remote = targetRemote;
      } catch (e: any) {
        vscode.window.showErrorMessage("Failed to add git remote: " + (e?.message || e));
        return;
      }
    }

    this._post({
      action: "agentEvent",
      event: { type: "message", data: { content: "\n📤 **Pushing to GitHub**: `" + remote + "` as `@" + username + "` (branch: `" + curBranch + "`)...\n" } }
    });

    try {
      this._execSync("git add -A", workdir);
      try {
        this._execSync('git -c user.name="' + username + '" commit -m "feat: updates by AlpieCode agent" --allow-empty', workdir);
      } catch {}

      const pushOutput = this._execSync("git push -u origin " + curBranch, workdir, 30000);
      this._post({
        action: "gitPushResult",
        success: true,
        message: "Successfully pushed to GitHub (`" + curBranch + "`) as `@" + username + "`!",
        output: (pushOutput || "").trim()
      });
      vscode.window.showInformationMessage("AlpieCode: Pushed code to GitHub as @" + username + "!");
    } catch (err: any) {
      const errMsg = err?.stderr?.toString() || err?.message || String(err);
      this._post({
        action: "gitPushResult",
        success: false,
        error: "Push failed: " + errMsg
      });
      vscode.window.showErrorMessage("AlpieCode: Git push failed: " + errMsg.slice(0, 120));
    }
  }

  /* ---- WSL Detection & Command Wrapping ---- */

  /** Convert a workdir-relative or POSIX WSL path to a local path accessible by host Node fs */
  private _toLocalPath(filePath: string): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders?.length) { return filePath; }
    const rootFs = folders[0].uri.fsPath;

    if (!filePath || filePath === ".") {
      return rootFs;
    }

    // If already absolute Windows path or UNC path
    if (/^[a-zA-Z]:[\\/]/.test(filePath) || /^\\\\/.test(filePath)) {
      return filePath;
    }

    // Normalize forward slashes to inspect POSIX paths
    const norm = filePath.replace(/\\/g, "/");
    const normWorkdir = this._workdir().replace(/\\/g, "/");
    const posixPath = norm.startsWith("/") ? norm : "/" + norm;

    // If it's a POSIX WSL path like /home/singh/... or \home\singh...
    if (this._isWslWorkspace() && (norm.startsWith("/") || norm.startsWith("home/"))) {
      if (posixPath.startsWith(normWorkdir)) {
        const rel = posixPath.slice(normWorkdir.length).replace(/^\/+/, "");
        return path.join(rootFs, rel);
      }
    }

    // Relative path: strip leading slashes and join directly to rootFs
    const cleanRel = filePath.replace(/^[\\/]+/, "");
    return path.join(rootFs, cleanRel);
  }

  /** True when VS Code accesses WSL files via UNC path (\\wsl.localhost\...) */
  private _isWslWorkspace(): boolean {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders?.length) { return false; }
    const fp = folders[0].uri.fsPath;
    return /^\\\\wsl[\.\$]/i.test(fp);
  }

  /** Wrap a shell command for WSL execution when workspace is via UNC path. */
  private _wslShellExec(cmd: string, workdir: string): vscode.ShellExecution {
    if (this._isWslWorkspace()) {
      return new vscode.ShellExecution(
        "wsl", ["-d", "Ubuntu", "--cd", workdir, "bash", "-c", cmd]
      );
    }
    return new vscode.ShellExecution(cmd, { cwd: workdir });
  }

  /** Run a command synchronously, routing through WSL if needed. */
  private _execSync(cmd: string, workdir: string, timeout: number = 8000): string {
    if (this._isWslWorkspace()) {
      const escaped = cmd.replace(/'/g, "'\\''");
      return cp.execSync(
        "wsl -e bash -c \"cd '" + workdir + "' && " + escaped + "\"",
        { timeout, stdio: "pipe", encoding: "utf-8" }
      );
    }
    return cp.execSync(cmd, {
      cwd: workdir, timeout, stdio: "pipe", encoding: "utf-8",
    });
  }


  /* ---- Workdir (cross-platform) ---- */

  private _workdir(): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders?.length) { return os.homedir(); }

    const uri = folders[0].uri;

    if (uri.scheme === "vscode-remote" && uri.authority.startsWith("wsl")) {
      return uri.path;
    }
    if (uri.scheme === "vscode-remote") {
      return uri.path;
    }

    const fp = uri.fsPath;
    const wsl = fp.match(/^\\\\wsl[\.\$][^\\]*\\[^\\]+(.+)/i);
    if (wsl) { return wsl[1].replace(/\\/g, "/"); }
    return fp;
  }

  /* ---- Health & Server Lifecycle ---- */

  private _healthInterval?: NodeJS.Timeout;
  private _isStartingServer = false;

  private _startHealthMonitoring() {
    if (this._healthInterval) { clearInterval(this._healthInterval); }
    this._healthCheck();
    this._healthInterval = setInterval(() => {
      this._healthCheck();
    }, 4000);
  }

  private async _healthCheck() {
    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    const h = await checkHealth(url);
    if (h) {
      this._isStartingServer = false;
      this._post({
        action: "serverStatus",
        status: { online: true, backend: h.backend, version: h.version },
      });
    } else {
      this._post({
        action: "serverStatus",
        status: { online: false, starting: this._isStartingServer },
      });
    }
  }

  public async startServer(): Promise<boolean> {
    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    const h = await checkHealth(url);
    if (h) {
      this._isStartingServer = false;
      this._post({
        action: "serverStatus",
        status: { online: true, backend: h.backend, version: h.version },
      });
      return true;
    }

    this._isStartingServer = true;
    this._post({
      action: "serverStatus",
      status: { online: false, starting: true },
    });

    const workdir = this._workdir();
    try {
      if (this._isWslWorkspace()) {
        const startCmd = `cd '${workdir}' && (test -f .venv/bin/python && nohup .venv/bin/python -c "from codeagent.server import run_server; run_server()" > /tmp/alpiecode_serve.log 2>&1 &) || (nohup alpiecode serve > /tmp/alpiecode_serve.log 2>&1 &)`;
        cp.exec(`wsl -e bash -c "${startCmd.replace(/"/g, '\"')}"`);
      } else {
        const cmd = process.platform === "win32" ? "start /b alpiecode.exe serve" : "nohup alpiecode serve > /tmp/alpiecode_serve.log 2>&1 &";
        cp.exec(cmd, { cwd: workdir });
      }
    } catch (err) {
      console.error("Failed to start AlpieCode server process:", err);
    }

    // Poll for up to 10 seconds (20 iterations * 500ms)
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 500));
      const res = await checkHealth(url);
      if (res) {
        this._isStartingServer = false;
        this._post({
          action: "serverStatus",
          status: { online: true, backend: res.backend, version: res.version },
        });
        vscode.window.showInformationMessage(`AlpieCode Server is online (${res.backend || "Ready"})`);
        return true;
      }
    }

    this._isStartingServer = false;
    this._post({
      action: "serverStatus",
      status: { online: false, starting: false },
    });
    return false;
  }

  /* ---- History ---- */

  private _newConv(firstMsg: string): string {
    const id = "c_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
    const title = firstMsg.length > 60 ? firstMsg.slice(0, 60) + "\u2026" : firstMsg;
    this._gitPushPrompted = false;
    this._conversations.unshift({ id, title, messages: [], createdAt: Date.now() });
    if (this._conversations.length > 50) { this._conversations.length = 50; }
    this._activeId = id;
    this._saveHistory();
    this._pushHistoryList();
    return id;
  }

  private _activeConv(): Conversation | undefined {
    return this._conversations.find((c) => c.id === this._activeId);
  }

  private _restoreConv(id: string) {
    const conv = this._conversations.find((c) => c.id === id);
    if (!conv) { return; }
    this._activeId = id;
    this._saveHistory();
    this._post({ action: "restoreChat", messages: conv.messages });
  }

  private _deleteConv(id: string) {
    this._conversations = this._conversations.filter((c) => c.id !== id);
    if (this._activeId === id) { this._activeId = null; }
    this._saveHistory();
    this._pushHistoryList();
  }

  private _pushHistoryList() {
    this._post({
      action: "historyList",
      conversations: this._conversations.map((c) => ({
        id: c.id,
        title: c.title,
        messageCount: c.messages.length,
        createdAt: c.createdAt,
      })),
    });
  }

  private _loadHistory() {
    const d = this._ctx.globalState.get<any>("alpiecode.history");
    if (d?.conversations) {
      this._conversations = d.conversations;
      this._activeId = d.activeId || null;
    }
  }

  private static readonly MAX_SAVED_CONVERSATIONS = 50;

  private _saveHistory() {
    if (this._conversations.length > ChatViewProvider.MAX_SAVED_CONVERSATIONS) {
      this._conversations = this._conversations.slice(-ChatViewProvider.MAX_SAVED_CONVERSATIONS);
    }
    this._ctx.globalState.update("alpiecode.history", {
      conversations: this._conversations,
      activeId: this._activeId,
    });
  }

  /* ---- Helpers ---- */

  /** Push token speed and count to the webview header. */
  private _pushTokenStats() {
    const elapsed = (Date.now() - this._streamStartTime) / 1000;
    const tokPerSec = elapsed > 0.1 ? Math.round(this._tokenCount / elapsed) : 0;
    this._post({
      action: "tokenStats",
      tokPerSec,
      tokenCount: this._tokenCount,
      sessionTotal: this._sessionTokenTotal + this._tokenCount,
    });
  }

  private _post(m: any) { this._view?.webview.postMessage(m); }

  private _html(wv: vscode.Webview): string {
    const css = wv.asWebviewUri(vscode.Uri.joinPath(this._extUri, "media", "chat.css"));
    const js  = wv.asWebviewUri(vscode.Uri.joinPath(this._extUri, "media", "chat.js"));
    const n   = nonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; img-src ${wv.cspSource} data: blob: https:; style-src ${wv.cspSource} 'unsafe-inline'; script-src 'nonce-${n}';">
  <link rel="stylesheet" href="${css}">
  <title>AlpieCode</title>
</head>
<body>
<div id="app">
  <div id="header">
    <div id="header-left" title="Click to check or start AlpieCode server">
      <span id="status-dot" class="dot offline"></span>
      <span id="status-text">Connecting…</span>
      <button id="start-server-btn" class="start-server-btn hidden" title="Start AlpieCode Server">Start Server</button>
    </div>
    <div id="header-right">
      <span id="token-badge" class="token-badge" title="Generation speed and token usage"><span class="token-val">0 tok/s · 0 tok</span></span>
      <button id="history-btn" title="Chat History"><svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/></svg></button>
      <button id="new-chat-btn" title="New Chat">\uff0b</button>
    </div>
  </div>
  <div id="history-panel" class="hidden">
    <div id="history-header">
      <span>Chat History</span>
      <button id="history-close-btn">\u2715</button>
    </div>
    <div id="history-list"></div>
  </div>
  <div id="live-build-bar" class="live-build-bar hidden">
    <div class="stepper-track">
      <span class="stepper-step active" data-step="rephrase"><span class="step-num">1</span> Rephrase</span>
      <span class="stepper-arrow">›</span>
      <span class="stepper-step" data-step="plan"><span class="step-num">2</span> Plan</span>
      <span class="stepper-arrow">›</span>
      <span class="stepper-step" data-step="files"><span class="step-num">3</span> Files</span>
      <span class="stepper-arrow">›</span>
      <span class="stepper-step" data-step="verify"><span class="step-num">4</span> Verify</span>
      <span class="stepper-arrow">›</span>
      <span class="stepper-step" data-step="done"><span class="step-num">5</span> Done</span>
    </div>
    <div class="stepper-status-line">
      <span class="live-build-spinner"><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="28" stroke-dashoffset="10"/></svg></span>
      <span id="live-build-text" class="live-build-text">Building...</span>
    </div>
  </div>
  <button id="scroll-bottom-btn" class="scroll-bottom-btn hidden" title="Scroll to bottom">↓</button>
  <div id="chat-messages"></div>
  <div id="active-context-bar" class="active-context-bar hidden">
    <span class="ac-icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4 0h5.5v1H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6.5h1V14a3 3 0 0 1-3 3H4a3 3 0 0 1-3-3V3a3 3 0 0 1 3-3z"/><path d="M9.5 0v4.5A1.5 1.5 0 0 0 11 6h4.5l-6-6z"/></svg></span>
    <span id="ac-filename" class="ac-filename">file</span>
    <button id="ac-remove-btn" class="ac-remove-btn" title="Remove context">✕</button>
  </div>
  <div id="input-area">
    <div id="image-preview-bar" class="hidden">
      <div id="image-preview-item">
        <img id="image-preview-thumb" src="" alt="Attached image">
        <span id="image-preview-name"></span>
        <button id="image-preview-remove" title="Remove image">\u2715</button>
      </div>
    </div>
    <div id="slash-popup" class="slash-popup hidden">
      <div id="slash-list" class="slash-list"></div>
    </div>
    <div id="input-options">
      <div id="reasoning-selector" class="reasoning-selector">
        <button id="reasoning-btn" class="reasoning-btn" type="button" title="Model Thinking Mode">
          <span id="reasoning-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V15a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-1.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7zm2 13H6v-1h4v1zm1.75-2.82l-.46.32H4.71l-.46-.32A5.98 5.98 0 0 1 2 8a6 6 0 1 1 12 0c0 1.95-.94 3.7-2.25 4.88z"/></svg></span>
          <span id="reasoning-label">Thinking</span>
          <span class="reasoning-arrow">⌃</span>
        </button>
        <div id="reasoning-menu" class="reasoning-menu hidden">
          <div class="reasoning-option active" data-level="thinking">
            <span class="ro-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V15a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-1.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7zm2 13H6v-1h4v1zm1.75-2.82l-.46.32H4.71l-.46-.32A5.98 5.98 0 0 1 2 8a6 6 0 1 1 12 0c0 1.95-.94 3.7-2.25 4.88z"/></svg></span>
            <div class="ro-info">
              <div class="ro-title">Thinking Mode</div>
              <div class="ro-desc">Deep reasoning trace (collapsible)</div>
            </div>
          </div>
          <div class="reasoning-option" data-level="no-thinking">
            <span class="ro-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M11.251.068a.5.5 0 0 1 .42.58L10.077 6H14.5a.5.5 0 0 1 .372.832l-9.5 10.5a.5.5 0 0 1-.844-.512L5.923 10H1.5a.5.5 0 0 1-.372-.832l9.5-10.5a.5.5 0 0 1 .123-.1z"/></svg></span>
            <div class="ro-info">
              <div class="ro-title">No-Thinking Mode</div>
              <div class="ro-desc">Direct execution without reasoning trace</div>
            </div>
          </div>
        </div>
      </div>
      <button id="attach-img-btn" title="Attach Image / Screenshot"><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.502 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/><path d="M14.002 13a2 2 0 0 1-2 2h-10a2 2 0 0 1-2-2V5A2 2 0 0 1 2 3a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v8a2 2 0 0 1-1.998 2zM14 2H4a1 1 0 0 0-1 1h9.002a2 2 0 0 1 2 2v7A1 1 0 0 0 15 11V3a1 1 0 0 0-1-1zM2.002 4a1 1 0 0 0-1 1v8l2.646-2.354a.5.5 0 0 1 .63-.062l2.66 1.773 3.71-3.71a.5.5 0 0 1 .577-.094l1.777 1.947V5a1 1 0 0 0-1-1h-10z"/></svg> Image</button>
    </div>
    <div id="input-row">
      <textarea id="user-input" placeholder="Ask AlpieCode anything... (type / for commands, Shift+Enter for newline)" rows="3"></textarea>
      <button id="send-btn" title="Send (Ctrl+Enter)">\u27a4</button>
      <button id="cancel-btn" title="Stop" class="hidden">\u25a0</button>
    </div>
  </div>
</div>
<script nonce="${n}" src="${js}"></script>
</body>
</html>`;
  }
}

function nonce(): string {
  const c = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let s = "";
  for (let i = 0; i < 32; i++) { s += c[Math.floor(Math.random() * c.length)]; }
  return s;
}
