/**
 * AlpieCode Chat — Webview Script (v3)
 *
 * Clean, fast, multimodal chat interface with:
 * - Fresh chat session by default on launch
 * - Multimodal image attachment (file picker, drag & drop, clipboard paste)
 * - Image thumbnail preview & removal
 * - Thinking toggle (show/hide reasoning traces)
 * - Chat history panel (switch between conversations)
 * - Markdown rendering with syntax-styled code blocks
 * - Tool call and result cards
 */

(function () {
  const vscode = acquireVsCodeApi();

  // DOM Elements
  const messagesEl        = document.getElementById("chat-messages");
  const inputEl           = document.getElementById("user-input");
  const inputArea         = document.getElementById("input-area");
  const sendBtn           = document.getElementById("send-btn");
  const cancelBtn         = document.getElementById("cancel-btn");
  const newChatBtn        = document.getElementById("new-chat-btn");
  const historyBtn        = document.getElementById("history-btn");
  const historyPanel      = document.getElementById("history-panel");
  const historyCloseBtn   = document.getElementById("history-close-btn");
  const historyListEl     = document.getElementById("history-list");
  const statusDot         = document.getElementById("status-dot");
  const statusText        = document.getElementById("status-text");
  const thinkingCheck     = document.getElementById("thinking-check");

  // Image Attachment DOM Elements
  const attachImgBtn      = document.getElementById("attach-img-btn");
  const imagePreviewBar   = document.getElementById("image-preview-bar");
  const imagePreviewThumb = document.getElementById("image-preview-thumb");
  const imagePreviewName  = document.getElementById("image-preview-name");
  const imagePreviewRemove= document.getElementById("image-preview-remove");

  let isStreaming = false;
  let currentAssistantEl = null;
  let currentAssistantText = "";
  let currentThinkingEl = null;
  let showThinking = thinkingCheck ? thinkingCheck.checked : true;
  let activeConversationId = null;
  let currentAttachedImage = null; // { path: string|null, dataUrl: string, name: string }

  // ---- Initialize (Clean Welcome State) ----
  showWelcome();
  vscode.postMessage({ action: "checkStatus" });
  vscode.postMessage({ action: "getHistory" });

  // ---- Event Listeners ----
  sendBtn.addEventListener("click", sendMessage);
  cancelBtn.addEventListener("click", () => vscode.postMessage({ action: "cancelStream" }));

  newChatBtn.addEventListener("click", () => {
    vscode.postMessage({ action: "newChat" });
    activeConversationId = null;
    clearAttachedImage();
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

  if (thinkingCheck) {
    thinkingCheck.addEventListener("change", () => {
      showThinking = thinkingCheck.checked;
      document.querySelectorAll(".thinking-block").forEach((el) => {
        el.style.display = showThinking ? "" : "none";
      });
    });
  }

  // Multimodal Image Attachment Buttons
  if (attachImgBtn) {
    attachImgBtn.addEventListener("click", () => {
      vscode.postMessage({ action: "attachImage" });
    });
  }

  if (imagePreviewRemove) {
    imagePreviewRemove.addEventListener("click", clearAttachedImage);
  }

  // Keyboard Shortcuts
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
  });

  // Clipboard Paste Support (Images)
  document.addEventListener("paste", (e) => {
    const items = e.clipboardData ? e.clipboardData.items : null;
    if (!items) return;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf("image") !== -1) {
        const blob = item.getAsFile();
        if (blob) {
          const reader = new FileReader();
          reader.onload = (evt) => {
            setAttachedImage({
              path: null,
              dataUrl: evt.target.result,
              name: "pasted-image.png"
            });
          };
          reader.readAsDataURL(blob);
          e.preventDefault();
          break;
        }
      }
    }
  });

  // Drag and Drop Support (Images)
  if (inputArea) {
    inputArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      inputArea.classList.add("drag-over");
    });
    inputArea.addEventListener("dragleave", () => {
      inputArea.classList.remove("drag-over");
    });
    inputArea.addEventListener("drop", (e) => {
      e.preventDefault();
      inputArea.classList.remove("drag-over");
      const files = e.dataTransfer ? e.dataTransfer.files : null;
      if (files && files.length > 0 && files[0].type.startsWith("image/")) {
        const file = files[0];
        const reader = new FileReader();
        reader.onload = (evt) => {
          setAttachedImage({
            path: file.path || null,
            dataUrl: evt.target.result,
            name: file.name
          });
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // ---- Webview Message Handler ----
  window.addEventListener("message", (e) => {
    const message = e.data;
    switch (message.action) {
      case "serverStatus":
        updateStatus(message.status);
        break;

      case "userMessage":
        clearWelcome();
        appendUserMessage(message.text, message.image);
        break;

      case "imageAttached":
        setAttachedImage(message);
        break;

      case "streamStart":
        setStreaming(true);
        currentAssistantEl = null;
        currentAssistantText = "";
        currentThinkingEl = null;
        break;

      case "streamEnd":
        setStreaming(false);
        finalizeAssistantMessage();
        break;

      case "agentEvent":
        handleAgentEvent(message.event);
        break;

      case "historyList":
        renderHistoryList(message.conversations);
        break;

      case "restoreChat":
        restoreChat(message.messages);
        break;
    }
  });

  // ---- Image Handling ----

  function setAttachedImage(imgData) {
    if (!imgData || !imgData.dataUrl) return;
    currentAttachedImage = imgData;
    if (imagePreviewBar && imagePreviewThumb && imagePreviewName) {
      imagePreviewThumb.src = imgData.dataUrl;
      imagePreviewName.textContent = imgData.name || "image.png";
      imagePreviewBar.classList.remove("hidden");
    }
  }

  function clearAttachedImage() {
    currentAttachedImage = null;
    if (imagePreviewBar && imagePreviewThumb && imagePreviewName) {
      imagePreviewThumb.src = "";
      imagePreviewName.textContent = "";
      imagePreviewBar.classList.add("hidden");
    }
  }

  // ---- Chat Logic ----

  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text && !currentAttachedImage) return;
    if (isStreaming) return;

    clearWelcome();
    const imgToSend = currentAttachedImage;
    clearAttachedImage();

    inputEl.value = "";
    inputEl.style.height = "auto";

    vscode.postMessage({
      action: "sendMessage",
      text: text || "Analyze this image and execute the task",
      image: imgToSend ? (imgToSend.path || imgToSend.dataUrl) : undefined
    });

    setStreaming(true);
  }

  function closeHistory() {
    historyPanel.classList.add("hidden");
  }

  function showWelcome() {
    if (messagesEl.children.length === 0) {
      const welcome = document.createElement("div");
      welcome.className = "welcome";
      welcome.id = "welcome-card";
      welcome.innerHTML = `
        <div class="welcome-icon">⚡</div>
        <h2>AlpieCode AI Agent</h2>
        <p>Ask a question, request code generation, or attach mockups & screenshots (📎).</p>
      `;
      messagesEl.appendChild(welcome);
    }
  }

  function clearWelcome() {
    const w = document.getElementById("welcome-card");
    if (w) w.remove();
  }

  function handleAgentEvent(event) {
    if (!event) return;

    switch (event.type) {
      case "thinking": {
        const text = event.data.content || event.data.text || event.data.delta || "";
        if (text) appendThinking(text);
        break;
      }
      case "message":
      case "token": {
        const text = event.data.content || event.data.text || event.data.delta || "";
        if (text) appendAssistantToken(text);
        break;
      }
      case "tool_call":
        appendToolCall(event.data);
        break;
      case "tool_result":
        appendToolResult(event.data);
        break;
      case "error":
        appendError(event.data.error || "An error occurred");
        break;
      case "done":
        finalizeAssistantMessage();
        break;
    }
  }

  function appendUserMessage(text, imageSrc) {
    const el = document.createElement("div");
    el.className = "msg user";

    if (imageSrc) {
      const imgEl = document.createElement("img");
      imgEl.className = "msg-user-img";
      imgEl.src = imageSrc;
      imgEl.alt = "Attached image";
      el.appendChild(imgEl);
    }

    const textEl = document.createElement("div");
    textEl.className = "msg-user-text";
    textEl.textContent = text;
    el.appendChild(textEl);

    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function appendThinking(text) {
    if (!currentThinkingEl) {
      const block = document.createElement("div");
      block.className = "thinking-block";
      if (!showThinking) block.style.display = "none";

      const header = document.createElement("div");
      header.className = "thinking-header";
      header.innerHTML = '<span class="chevron">▼</span> <span>💭 Thinking Process</span>';

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
      currentThinkingEl = content;
    } else {
      currentThinkingEl.textContent += (currentThinkingEl.textContent ? "\n" : "") + text;
    }
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
    currentThinkingEl = null;
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

      item.querySelector(".history-item-content").addEventListener("click", () => {
        activeConversationId = conv.id;
        vscode.postMessage({ action: "loadConversation", id: conv.id });
        closeHistory();
      });

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
        appendUserMessage(msg.content, msg.image);
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
      bash: "⚡", file_search: "🔍", list_files: "📁",
      apply_patch: "🩹", web_search: "🌐", fetch_url: "🔗",
      view_image: "🖼️", clone_repo: "🐙", update_plan: "📋"
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

  function renderMarkdown(text) {
    if (!text) return "";
    let html = text;

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      return '<pre><code class="language-' + (lang || "text") + '">' +
        escapeHtml(code.trim()) + "</code></pre>";
    });

    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");
    html = html.replace(/^[-*] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
    html = html.replace(/\n{2,}/g, "</p><p>");
    if (!html.startsWith("<")) html = "<p>" + html;
    if (!html.endsWith(">")) html += "</p>";
    html = html.replace(/<p>\s*<\/p>/g, "");

    return html;
  }
})();
