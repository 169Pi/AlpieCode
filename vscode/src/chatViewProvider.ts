/**
 * Chat sidebar webview provider for AlpieCode.
 *
 * Cross-platform (Windows / Linux / macOS).
 * Manages webview lifecycle, SSE streaming, chat history, and workdir resolution.
 */

import * as vscode from "vscode";
import * as os from "os";
import { streamChat, checkHealth, AgentEvent } from "./sseClient";

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
      }
    );
  }

  private _abort() {
    if (this._abortStream) { this._abortStream(); this._abortStream = undefined; }
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
