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
    wv.onDidDispose(() => { this._abort(); this._view = undefined; });

    this._healthCheck();

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

  private _stream(task: string, image?: string) {
    this._abort();

    if (!this._activeId) { this._newConv(task); }
    const conv = this._activeConv();
    if (!conv) { return; }

    conv.messages.push({ role: "user", content: task, image, timestamp: Date.now() });
    this._saveHistory();

    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    const workdir = this._workdir();

    this._post({ action: "streamStart" });

    // Token meter: reset counters
    this._tokenCount = 0;
    this._streamStartTime = Date.now();
    if (this._statsInterval) { clearInterval(this._statsInterval); }
    this._statsInterval = setInterval(() => this._pushTokenStats(), 500);

    let assistantBuf = "";
    this._modifiedFiles = [];

    this._abortStream = streamChat(
      url,
      { task, workdir, sessionId: conv.sessionId, image },
      (ev) => {
        if (ev.type === "start" && ev.data.session_id) {
          conv.sessionId = ev.data.session_id;
        }
        if (ev.type === "message" || ev.type === "token") {
          const chunk = ev.data.content || ev.data.text || "";
          assistantBuf += chunk;
          // Token meter: approximate token count (rough: ~4 chars per token)
          this._tokenCount += Math.max(1, Math.ceil(chunk.length / 4));
        }
        if (ev.type === "tool_call") {
          this._handleToolCall(workdir, ev.data);
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
        this._abortStream = undefined;

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

  private async _handleToolCall(workdir: string, data: any) {
    const name = data.name;
    let args = data.arguments;
    if (typeof args === "string") {
      try { args = JSON.parse(args); } catch { args = {}; }
    }
    if (!args || !args.path) { return; }

    const relPath: string = args.path;
    const absPath = path.isAbsolute(relPath) ? relPath : path.join(workdir, relPath);

    if (name === "write_file") {
      const content = args.content || "";
      const fileExists = fs.existsSync(absPath);
      let existingContent = "";
      if (fileExists) {
        try { existingContent = fs.readFileSync(absPath, "utf-8"); } catch {}
      }

      if (!fileExists) {
        // MODE 1: New file — write directly, no approval needed
        const dir = path.dirname(absPath);
        if (!fs.existsSync(dir)) { fs.mkdirSync(dir, { recursive: true }); }
        fs.writeFileSync(absPath, content, "utf-8");
        try {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
          await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
        } catch {}
        this._modifiedFiles.push(relPath);
        this._autoFixRetries = 0; // reset retries on new file creation
      } else {
        // MODE 2: Existing file — show change plan for approval
        this._pendingChange = {
          workdir, relPath, absPath, newContent: content,
          oldContent: existingContent, toolName: "write_file", isNewFile: false
        };
        this._sendChangePlan();
      }

    } else if (name === "edit_file") {
      let existing = "";
      try { existing = fs.readFileSync(absPath, "utf-8"); } catch {}
      const oldStr = args.old_str || "";
      const newStr = args.new_str || "";
      const newContent = oldStr ? existing.replace(oldStr, newStr) : newStr;

      // MODE 2: Edit to existing file — show change plan for approval
      this._pendingChange = {
        workdir, relPath, absPath, newContent,
        oldContent: existing, toolName: "edit_file", isNewFile: false,
        oldStr, newStr
      };
      this._sendChangePlan();
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
      const absF = path.isAbsolute(f) ? f : path.join(workdir, f);
      if (!fs.existsSync(absF)) { continue; }

      if (ext === ".py") {
        const venvPy = path.join(workdir, ".venv", "bin", "python3");
        const venvPyWin = path.join(workdir, ".venv", "Scripts", "python.exe");
        if (fs.existsSync(venvPy)) {
          return ".venv/bin/python3 \"" + f + "\"";
        } else if (fs.existsSync(venvPyWin)) {
          return ".venv/Scripts/python.exe \"" + f + "\"";
        }
        return "python3 \"" + f + "\"";
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
    if (!autoRun) { return; }

    const files = [...new Set(this._modifiedFiles)];
    if (files.length === 0) { return; }

    // Proactively check for missing dependencies before execution
    const missingPrompted = await this._checkFileDependencies(workdir, files);
    if (missingPrompted) {
      return; // Awaiting user decision on dependency installation
    }

    const runCmd = this._detectRunCommand(files, workdir);
    if (!runCmd) { return; }

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
      panel: vscode.TaskPanelKind.Shared,
      focus: false,
    };

    const execution = await vscode.tasks.executeTask(task);

    if (autoFix) {
      const disposable = vscode.tasks.onDidEndTaskProcess((e) => {
        if (e.execution === execution) {
          disposable.dispose();
          if (e.exitCode !== 0) {
            // Smart dep detection: check for missing packages BEFORE auto-fix
            this._detectMissingDep(workdir, files, runCmd).then(dep => {
              if (dep) {
                this._promptInstallDep(dep, workdir, files, runCmd);
              } else {
                this._autoFixError(workdir, files, runCmd, e.exitCode || 1);
              }
            });
          } else {
            this._autoFixRetries = 0; // reset on success
            vscode.window.showInformationMessage("AlpieCode: Code executed successfully!");
          }
        }
      });
    }
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
      const absPath = path.isAbsolute(f) ? f : path.join(workdir, f);
      if (!fs.existsSync(absPath)) { continue; }

      if (ext === ".py") {
        let content = "";
        try { content = fs.readFileSync(absPath, "utf-8"); } catch { continue; }

        // Find all imported module names
        const importRegex = /(?:^|\n)\s*(?:import|from)\s+([a-zA-Z0-9_]+)/g;
        const matches = new Set<string>();
        let match;
        while ((match = importRegex.exec(content)) !== null) {
          const mod = match[1];
          if (!PYTHON_STDLIB.has(mod) && !fs.existsSync(path.join(workdir, mod + ".py")) && !fs.existsSync(path.join(workdir, mod))) {
            matches.add(mod);
          }
        }

        const venvPy = path.join(workdir, ".venv", "bin", "python3");
        const venvExists = fs.existsSync(path.join(workdir, ".venv"));
        const pyRunner = fs.existsSync(venvPy) ? ".venv/bin/python3" : "python3";

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
            const runCmd = this._detectRunCommand(files, workdir) || `python3 "${f}"`;
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
    if (dep.type === "pylib") {
      // Check if a venv already exists in the workdir
      const venvPath = path.join(workdir, ".venv");
      const venvExists = fs.existsSync(venvPath);

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
          const pipPath = path.join(".venv", "bin", "pip");
          this._runInstallTask(pipPath + " install " + dep.name, workdir, files, runCmd);
        } else if (choice === "Install Globally") {
          this._runInstallTask("pip install " + dep.name, workdir, files, runCmd);
        }
        // else Skip → do nothing

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
          const cmd = "python3 -m venv .venv && .venv/bin/pip install " + dep.name;
          this._runInstallTask(cmd, workdir, files, runCmd);
        } else if (choice === "Install Globally") {
          this._runInstallTask("pip install " + dep.name, workdir, files, runCmd);
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
        this._stream(m.text, m.image);
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
    }
  }


  /* ---- WSL Detection & Command Wrapping ---- */

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
      const escaped = cmd.replace(/'/g, "'\\''");
      return new vscode.ShellExecution(
        "wsl", ["-e", "bash", "-c", "cd '" + workdir + "' && " + escaped]
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

  /* ---- Health ---- */

  private async _healthCheck() {
    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    const h = await checkHealth(url);
    this._post({
      action: "serverStatus",
      status: h
        ? { online: true, backend: h.backend, version: h.version }
        : { online: false },
    });
  }

  /* ---- History ---- */

  private _newConv(firstMsg: string): string {
    const id = "c_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
    const title = firstMsg.length > 60 ? firstMsg.slice(0, 60) + "\u2026" : firstMsg;
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

  private _saveHistory() {
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
    <div id="header-left">
      <span id="status-dot" class="dot offline"></span>
      <span id="status-text">Connecting\u2026</span>
    </div>
    <div id="header-right">
      <button id="history-btn" title="Chat History">\ud83d\udccb</button>
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
  <div id="chat-messages"></div>
  <div id="input-area">
    <div id="image-preview-bar" class="hidden">
      <div id="image-preview-item">
        <img id="image-preview-thumb" src="" alt="Attached image">
        <span id="image-preview-name"></span>
        <button id="image-preview-remove" title="Remove image">\u2715</button>
      </div>
    </div>
    <div id="input-options">
      <label id="thinking-toggle" title="Show thinking traces">
        <input type="checkbox" id="thinking-check" checked>
        <span>\ud83d\udcad Thinking</span>
      </label>
      <button id="attach-img-btn" title="Attach Image / Screenshot">\ud83d\udcce Image</button>
    </div>
    <div id="input-row">
      <textarea id="user-input" placeholder="Ask AlpieCode anything..." rows="1"></textarea>
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
