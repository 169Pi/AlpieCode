/**
 * Chat sidebar webview provider for AlpieCode.
 *
 * Cross-platform (Windows / Linux / macOS).
 * Manages webview lifecycle, SSE streaming, chat history, and workdir resolution.
 */

import * as vscode from "vscode";
import * as os from "os";
import * as path from "path";
import * as fs from "fs";
import { streamChat, checkHealth, AgentEvent } from "./sseClient";
import { showDiffPreview } from "./diffHelper";

/* ------------------------------------------------------------------ */
/*  Data models                                                       */
/* ------------------------------------------------------------------ */

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  sessionId?: string;
  createdAt: number;
}

/* ------------------------------------------------------------------ */
/*  Provider                                                          */
/* ------------------------------------------------------------------ */

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "alpiecode.chatView";

  private _view?: vscode.WebviewView;
  private _abortStream?: () => void;

  private _conversations: Conversation[] = [];
  private _activeId: string | null = null;

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
    // Small delay so webview script is ready before we push data
    setTimeout(() => {
      this._pushHistoryList();
      if (this._activeId) { this._restoreConv(this._activeId); }
    }, 200);
  }

  /* ---- Public (called from code actions) ---- */

  public sendTask(task: string) {
    if (!this._view) {
      vscode.window.showErrorMessage("AlpieCode panel not open.");
      return;
    }
    this._view.show?.(true);
    this._post({ action: "userMessage", text: task });
    this._stream(task);
  }

  /* ---- Streaming ---- */

  private _stream(task: string) {
    this._abort();

    if (!this._activeId) { this._newConv(task); }
    const conv = this._activeConv();
    if (!conv) { return; }

    conv.messages.push({ role: "user", content: task, timestamp: Date.now() });
    this._saveHistory();

    const url = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    const workdir = this._workdir();

    this._post({ action: "streamStart" });

    let assistantBuf = "";
    this._modifiedFiles = [];

    this._abortStream = streamChat(
      url,
      { task, workdir, sessionId: conv.sessionId },
      (ev) => {
        if (ev.type === "start" && ev.data.session_id) {
          conv.sessionId = ev.data.session_id;
        }
        if (ev.type === "message" || ev.type === "token") {
          assistantBuf += ev.data.content || ev.data.text || "";
        }
        if (ev.type === "tool_call") {
          this._handleToolCallDiff(workdir, ev.data);
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
        this._post({ action: "streamEnd" });
        this._abortStream = undefined;

        // Auto-run generated code in sandbox terminal
        if (this._modifiedFiles.length > 0) {
          this._sandboxRun(workdir);
        }
      }
    );
  }

  private _abort() {
    if (this._abortStream) { this._abortStream(); this._abortStream = undefined; }
  }

  /** Files modified during the current stream (for sandbox auto-run). */
  private _modifiedFiles: string[] = [];

  private async _handleToolCallDiff(workdir: string, data: any) {
    const name = data.name;
    let args = data.arguments;
    if (typeof args === "string") {
      try { args = JSON.parse(args); } catch { args = {}; }
    }
    if (!args || !args.path) { return; }

    const relPath: string = args.path;
    const absPath = path.isAbsolute(relPath) ? relPath : path.join(workdir, relPath);

    const showDiffs = vscode.workspace
      .getConfiguration("alpiecode")
      .get<boolean>("showDiffPreview", false);

    if (name === "write_file") {
      const content = args.content || "";
      const fileExists = fs.existsSync(absPath);

      if (showDiffs && fileExists) {
        await showDiffPreview(workdir, relPath, content, "write_file");
      } else {
        const dir = path.dirname(absPath);
        if (!fs.existsSync(dir)) { fs.mkdirSync(dir, { recursive: true }); }
        fs.writeFileSync(absPath, content, "utf-8");
        try {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
          await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
        } catch { /* file may be binary or unsupported */ }
      }
      this._modifiedFiles.push(relPath);

    } else if (name === "edit_file") {
      let existing = "";
      try { existing = fs.readFileSync(absPath, "utf-8"); } catch {}
      const oldStr = args.old_str || "";
      const newStr = args.new_str || "";
      const newContent = oldStr ? existing.replace(oldStr, newStr) : newStr;

      if (showDiffs) {
        await showDiffPreview(workdir, relPath, newContent, "edit_file");
      } else {
        fs.writeFileSync(absPath, newContent, "utf-8");
        try {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(absPath));
          await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: true });
        } catch {}
      }
      this._modifiedFiles.push(relPath);
    }
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

      if (ext === ".py")   { return "python3 \"" + f + "\""; }
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
      new vscode.ShellExecution(runCmd, { cwd: workdir })
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
            this._autoFixError(workdir, files, runCmd, e.exitCode || 1);
          } else {
            vscode.window.showInformationMessage("AlpieCode: Code executed successfully!");
          }
        }
      });
    }
  }

  private _autoFixError(workdir: string, files: string[], runCmd: string, exitCode: number) {
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

    let fixPrompt = "The code I just wrote has errors. Fix them and make it work correctly.\n\n";
    fixPrompt += "Execution command: " + runCmd + "\n";
    fixPrompt += "Exit code: " + exitCode + "\n";
    if (errors.length > 0) {
      fixPrompt += "\nDiagnostic errors:\n" + errorSummary;
    } else {
      fixPrompt += "\nThe command failed. Read the file, find the bug, and fix it.";
    }
    fixPrompt += "\n\nFiles to fix: " + files.join(", ");

    setTimeout(() => {
      this._post({ action: "userMessage", text: "Auto-fixing execution errors..." });
      this._stream(fixPrompt);
    }, 1500);
  }

  /* ---- Message handler ---- */

  private _onMessage(m: any) {
    switch (m.action) {
      case "sendMessage":
        this._post({ action: "userMessage", text: m.text });
        this._stream(m.text);
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

  /* ---- Workdir (cross-platform) ---- */

  private _workdir(): string {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders?.length) { return os.homedir(); }

    const uri = folders[0].uri;

    // VS Code Remote — WSL
    if (uri.scheme === "vscode-remote" && uri.authority.startsWith("wsl")) {
      return uri.path; // Already Linux path
    }

    // VS Code Remote — SSH / Dev Containers / etc.
    if (uri.scheme === "vscode-remote") {
      return uri.path;
    }

    const fp = uri.fsPath;

    // Windows accessing WSL files: \\wsl.localhost\Ubuntu\home\... or \\wsl$\Ubuntu\home\...
    const wsl = fp.match(/^\\\\wsl[\.\$][^\\]*\\[^\\]+(.+)/i);
    if (wsl) { return wsl[1].replace(/\\/g, "/"); }

    // Native path (Windows C:\..., Linux /home/..., macOS /Users/...)
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
    const id = `c_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const title = firstMsg.length > 60 ? firstMsg.slice(0, 60) + "…" : firstMsg;
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
    content="default-src 'none'; style-src ${wv.cspSource} 'unsafe-inline'; script-src 'nonce-${n}';">
  <link rel="stylesheet" href="${css}">
  <title>AlpieCode</title>
</head>
<body>
<div id="app">
  <div id="header">
    <div id="header-left">
      <span id="status-dot" class="dot offline"></span>
      <span id="status-text">Connecting…</span>
    </div>
    <div id="header-right">
      <button id="history-btn" title="Chat History">📋</button>
      <button id="new-chat-btn" title="New Chat">＋</button>
    </div>
  </div>
  <div id="history-panel" class="hidden">
    <div id="history-header">
      <span>Chat History</span>
      <button id="history-close-btn">✕</button>
    </div>
    <div id="history-list"></div>
  </div>
  <div id="chat-messages"></div>
  <div id="input-area">
    <div id="input-options">
      <label id="thinking-toggle" title="Show thinking traces">
        <input type="checkbox" id="thinking-check" checked>
        <span>💭 Thinking</span>
      </label>
    </div>
    <div id="input-row">
      <textarea id="user-input" placeholder="Ask AlpieCode anything…" rows="1"></textarea>
      <button id="send-btn" title="Send (Ctrl+Enter)">➤</button>
      <button id="cancel-btn" title="Stop" class="hidden">■</button>
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
