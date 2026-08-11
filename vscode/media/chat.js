/**
 * AlpieCode Chat — Webview Script (v2)
 *
 * Clean chat interface with:
 * - No turn/badge noise — just user and assistant messages
 * - Thinking toggle (show/hide reasoning traces)
 * - Chat history panel (switch between conversations)
 * - Markdown rendering with code blocks
 * - Tool call and result cards
 */

(function () {
  const vscode = acquireVsCodeApi();

  // DOM
  const messagesEl    = document.getElementById("chat-messages");
  const inputEl       = document.getElementById("user-input");
  const sendBtn       = document.getElementById("send-btn");
  const cancelBtn     = document.getElementById("cancel-btn");
  const newChatBtn    = document.getElementById("new-chat-btn");
  const historyBtn    = document.getElementById("history-btn");
  const historyPanel  = document.getElementById("history-panel");
  const historyCloseBtn = document.getElementById("history-close-btn");
  const historyListEl = document.getElementById("history-list");
  const statusDot     = document.getElementById("status-dot");
  const statusText    = document.getElementById("status-text");
  const thinkingCheck = document.getElementById("thinking-check");

  let isStreaming = false;
  let currentAssistantEl = null;
  let currentAssistantText = "";
  let showThinking = thinkingCheck.checked;
  let activeConversationId = null;

  // ---- Init ----
  showWelcome();
  vscode.postMessage({ action: "checkStatus" });
  vscode.postMessage({ action: "getHistory" });

  // ---- Event Listeners ----
  sendBtn.addEventListener("click", sendMessage);
  cancelBtn.addEventListener("click", () => vscode.postMessage({ action: "cancelStream" }));

  newChatBtn.addEventListener("click", () => {
    vscode.postMessage({ action: "newChat" });
    activeConversationId = null;
    messagesEl.innerHTML = "";
    showWelcome();
    closeHistory();
  });

  historyBtn.addEventListener("click", () => {
    historyPanel.classList.toggle("hidden");
    if (!historyPanel.classList.contains("hidden")) {
      vscode.postMessage({ action: "getHistory" });
    }
  });

  historyCloseBtn.addEventListener("click", closeHistory);

  thinkingCheck.addEventListener("change", () => {
    showThinking = thinkingCheck.checked;
    // Show/hide existing thinking blocks
    document.querySelectorAll(".thinking-block").forEach((el) => {
      el.style.display = showThinking ? "" : "none";
    });
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
    // Allow Enter for newlines (no auto-send)
  });

  // Auto-resize textarea
  inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + "px";
  });

  // ---- Message Handler from Extension ----
  window.addEventListener("message", (event) => {
    const msg = event.data;
    switch (msg.action) {
      case "userMessage":
        appendUserMessage(msg.text);
        break;
      case "agentEvent":
        handleAgentEvent(msg.event);
        break;
      case "streamStart":
        setStreaming(true);
        break;
      case "streamEnd":
        finalizeAssistantMessage();
        setStreaming(false);
        break;
      case "serverStatus":
        updateStatus(msg.status);
        break;
      case "historyList":
        renderHistoryList(msg.conversations);
        break;
      case "restoreChat":
        restoreChat(msg.messages);
        break;
    }
  });

  // ---- Core Functions ----

  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || isStreaming) return;
    vscode.postMessage({ action: "sendMessage", text });
    inputEl.value = "";
    inputEl.style.height = "auto";
  }

  function closeHistory() {
    historyPanel.classList.add("hidden");
  }

  function showWelcome() {
    messagesEl.innerHTML = `
      <div class="welcome">
        <h2>AlpieCode</h2>
        <p>AI coding agent by 169Pi. Write code, fix bugs, generate tests, or ask anything.</p>
        <p style="margin-top:10px;font-size:11px;">💡 Right-click code for quick actions</p>
      </div>
    `;
  }

  function clearWelcome() {
    const w = messagesEl.querySelector(".welcome");
    if (w) w.remove();
  }

  function appendUserMessage(text) {
    clearWelcome();
    const el = document.createElement("div");
    el.className = "msg user";
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function handleAgentEvent(event) {
    clearWelcome();

    switch (event.type) {
      case "start":
      case "adaptive_mode":
      case "turn_start":
        // Silently consume these — no visual noise
        break;

      case "thinking":
        appendThinking(event.data.content || event.data.text || "");
        break;

      case "tool_call":
        finalizeAssistantMessage();
        appendToolCall(event.data);
        break;

      case "tool_result":
        appendToolResult(event.data);
        break;

      case "message":
      case "token":
        appendAssistantToken(event.data.content || event.data.text || "");
        break;

      case "error":
        finalizeAssistantMessage();
        appendError(event.data.error || event.data.message || "Unknown error");
        break;

      case "done":
        finalizeAssistantMessage();
        break;

      default:
        // Silently ignore unknown events
        break;
    }
  }

  function appendThinking(text) {
    if (!text) return;
    finalizeAssistantMessage();

    const block = document.createElement("div");
    block.className = "thinking-block";
    block.style.display = showThinking ? "" : "none";

    const header = document.createElement("div");
    header.className = "thinking-header";
    header.innerHTML = '<span class="chevron">▼</span> 💭 Thinking...';

    const content = document.createElement("div");
    content.className = "thinking-content";
    content.textContent = text;

    header.addEventListener("click", () => {
      header.classList.toggle("collapsed");
      content.classList.toggle("collapsed");
    });

    block.appendChild(header);
    block.appendChild(content);
    messagesEl.appendChild(block);
    scrollToBottom();
  }

  function appendToolCall(data) {
    const card = document.createElement("div");
    card.className = "tool-card";

    const icon = getToolIcon(data.name);
    let argsText = "";

    if (data.arguments) {
      const args = typeof data.arguments === "string"
        ? tryParse(data.arguments)
        : data.arguments;
      argsText = formatArgs(args);
    }

    card.innerHTML = `
      <div class="tool-header">
        <span>${icon}</span>
        <span>${escapeHtml(data.name || "tool")}</span>
      </div>
      ${argsText ? `<div class="tool-args">${escapeHtml(argsText)}</div>` : ""}
    `;

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  function appendToolResult(data) {
    const card = document.createElement("div");
    card.className = "tool-result";

    const output = data.output || data.content || data.result || JSON.stringify(data);
    const display = typeof output === "string"
      ? (output.length > 400 ? output.substring(0, 400) + "..." : output)
      : JSON.stringify(output, null, 2);

    card.innerHTML = `
      <div class="tool-result-header"><span>✅</span> <span>Result</span></div>
      <div class="tool-result-content">${escapeHtml(display)}</div>
    `;

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  function appendAssistantToken(text) {
    if (!currentAssistantEl) {
      currentAssistantEl = document.createElement("div");
      currentAssistantEl.className = "msg assistant";
      messagesEl.appendChild(currentAssistantEl);
      currentAssistantText = "";
    }
    currentAssistantText += text;
    currentAssistantEl.innerHTML = renderMarkdown(currentAssistantText) +
      '<span class="streaming-dot"></span>';
    scrollToBottom();
  }

  function finalizeAssistantMessage() {
    if (currentAssistantEl && currentAssistantText) {
      currentAssistantEl.innerHTML = renderMarkdown(currentAssistantText);
    }
    currentAssistantEl = null;
    currentAssistantText = "";
  }

  function appendError(text) {
    const el = document.createElement("div");
    el.className = "error-card";
    el.textContent = "❌ " + text;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function setStreaming(streaming) {
    isStreaming = streaming;
    sendBtn.disabled = streaming;
    sendBtn.classList.toggle("hidden", streaming);
    cancelBtn.classList.toggle("hidden", !streaming);
    inputEl.placeholder = streaming ? "Generating..." : "Ask AlpieCode anything...";
  }

  function updateStatus(status) {
    statusDot.className = "dot " + (status.online ? "online" : "offline");
    if (status.online) {
      // Show short backend name
      let backend = status.backend || "";
      if (backend.length > 35) backend = backend.substring(0, 35) + "…";
      statusText.textContent = "Connected · " + backend;
    } else {
      statusText.textContent = "Offline — run: alpiecode serve";
    }
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  // ---- History ----

  function renderHistoryList(conversations) {
    if (!conversations || conversations.length === 0) {
      historyListEl.innerHTML = '<div class="history-empty">No chat history yet</div>';
      return;
    }

    historyListEl.innerHTML = "";
    conversations.forEach((conv) => {
      const item = document.createElement("div");
      item.className = "history-item" + (conv.id === activeConversationId ? " active" : "");

      const ago = timeAgo(conv.createdAt);

      item.innerHTML = `
        <div class="history-item-content">
          <div class="history-title">${escapeHtml(conv.title)}</div>
          <div class="history-meta">${conv.messageCount} messages · ${ago}</div>
        </div>
        <button class="history-delete" title="Delete">🗑</button>
      `;

      // Click to load conversation
      item.querySelector(".history-item-content").addEventListener("click", () => {
        activeConversationId = conv.id;
        vscode.postMessage({ action: "loadConversation", id: conv.id });
        closeHistory();
      });

      // Delete button
      item.querySelector(".history-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        vscode.postMessage({ action: "deleteConversation", id: conv.id });
      });

      historyListEl.appendChild(item);
    });
  }

  function restoreChat(messages) {
    messagesEl.innerHTML = "";
    currentAssistantEl = null;
    currentAssistantText = "";

    if (!messages || messages.length === 0) {
      showWelcome();
      return;
    }

    clearWelcome();
    messages.forEach((msg) => {
      if (msg.role === "user") {
        appendUserMessage(msg.content);
      } else if (msg.role === "assistant" && msg.content) {
        const el = document.createElement("div");
        el.className = "msg assistant";
        el.innerHTML = renderMarkdown(msg.content);
        messagesEl.appendChild(el);
      }
    });
    scrollToBottom();
  }

  // ---- Utilities ----

  function getToolIcon(name) {
    const icons = {
      write_file: "📝", edit_file: "✏️", read_file: "📖",
      run_command: "⚡", search_files: "🔍", list_directory: "📁",
      delete_file: "🗑️", web_search: "🌐", create_directory: "📂",
    };
    return icons[name] || "🔧";
  }

  function formatArgs(args) {
    if (!args || typeof args !== "object") return String(args || "");
    const lines = [];
    for (const [key, value] of Object.entries(args)) {
      const val = typeof value === "string"
        ? (value.length > 150 ? value.substring(0, 150) + "..." : value)
        : JSON.stringify(value);
      lines.push(key + ": " + val);
    }
    return lines.join("\n");
  }

  function tryParse(str) {
    try { return JSON.parse(str); } catch { return str; }
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function timeAgo(ts) {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    const days = Math.floor(hrs / 24);
    return days + "d ago";
  }

  /**
   * Lightweight markdown renderer.
   */
  function renderMarkdown(text) {
    if (!text) return "";
    let html = text;

    // Fenced code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      return '<pre><code class="language-' + (lang || "text") + '">' +
        escapeHtml(code.trim()) + "</code></pre>";
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Headers
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

    // Bold & italic
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

    // Blockquotes
    html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");

    // Unordered lists
    html = html.replace(/^[-*] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

    // Paragraphs
    html = html.replace(/\n{2,}/g, "</p><p>");
    if (!html.startsWith("<")) html = "<p>" + html;
    if (!html.endsWith(">")) html += "</p>";
    html = html.replace(/<p>\s*<\/p>/g, "");

    return html;
  }
})();
