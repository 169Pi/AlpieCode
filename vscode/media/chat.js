/**
 * AlpieCode Chat — Webview Script (v4)
 *
 * Simplified flow:
 * - New files: written directly, opened, auto-executed
 * - Edits to existing files: Change Plan card with Accept/Reject/Edit Request
 * - Multimodal image attachment (file picker, drag & drop, clipboard paste)
 * - Thinking toggle, history panel, markdown rendering
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
  let currentAttachedImage = null;
  let lastServerStatus = "";

  // ---- Initialize ----
  showWelcome();
  vscode.postMessage({ action: "checkStatus" });
  vscode.postMessage({ action: "getHistory" });

  // ---- Event Listeners ----
  sendBtn.addEventListener("click", sendMessage);
  cancelBtn.addEventListener("click", function() { vscode.postMessage({ action: "cancelStream" }); });

  newChatBtn.addEventListener("click", function() {
    vscode.postMessage({ action: "newChat" });
    activeConversationId = null;
    clearAttachedImage();
    messagesEl.innerHTML = "";
    showWelcome();
    closeHistory();
  });

  historyBtn.addEventListener("click", function() {
    historyPanel.classList.toggle("hidden");
    if (!historyPanel.classList.contains("hidden")) {
      vscode.postMessage({ action: "getHistory" });
    }
  });

  historyCloseBtn.addEventListener("click", closeHistory);

  if (thinkingCheck) {
    thinkingCheck.addEventListener("change", function() {
      showThinking = thinkingCheck.checked;
      document.querySelectorAll(".thinking-block").forEach(function(el) {
        el.style.display = showThinking ? "" : "none";
      });
    });
  }

  if (attachImgBtn) {
    attachImgBtn.addEventListener("click", function() {
      vscode.postMessage({ action: "attachImage" });
    });
  }

  if (imagePreviewRemove) {
    imagePreviewRemove.addEventListener("click", clearAttachedImage);
  }

  inputEl.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
  });

  inputEl.addEventListener("input", function() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
  });

  // Clipboard paste (images)
  document.addEventListener("paste", function(e) {
    var items = e.clipboardData ? e.clipboardData.items : null;
    if (!items) return;
    for (var i = 0; i < items.length; i++) {
      if (items[i].type.indexOf("image") !== -1) {
        var blob = items[i].getAsFile();
        if (blob) {
          var reader = new FileReader();
          reader.onload = function(evt) {
            setAttachedImage({ path: null, dataUrl: evt.target.result, name: "pasted-image.png" });
          };
          reader.readAsDataURL(blob);
          e.preventDefault();
          break;
        }
      }
    }
  });

  // Drag and drop (images)
  if (inputArea) {
    inputArea.addEventListener("dragover", function(e) { e.preventDefault(); inputArea.classList.add("drag-over"); });
    inputArea.addEventListener("dragleave", function() { inputArea.classList.remove("drag-over"); });
    inputArea.addEventListener("drop", function(e) {
      e.preventDefault();
      inputArea.classList.remove("drag-over");
      var files = e.dataTransfer ? e.dataTransfer.files : null;
      if (files && files.length > 0 && files[0].type.startsWith("image/")) {
        var reader = new FileReader();
        reader.onload = function(evt) {
          setAttachedImage({ path: files[0].path || null, dataUrl: evt.target.result, name: files[0].name });
        };
        reader.readAsDataURL(files[0]);
      }
    });
  }

  // ---- Webview Message Handler ----
  window.addEventListener("message", function(e) {
    var message = e.data;
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
      case "changePlan":
        renderChangePlan(message.data);
        break;
      case "changeApplied":
        appendSystemMessage("✅ Changes applied to " + message.fileName);
        break;
      case "changeRejected":
        appendSystemMessage("❌ Changes rejected.");
        break;
      case "tokenStats":
        updateTokenStats(message);
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
    var text = inputEl.value.trim();
    if (!text && !currentAttachedImage) return;
    if (isStreaming) return;

    clearWelcome();
    var imgToSend = currentAttachedImage;
    clearAttachedImage();
    inputEl.value = "";
    inputEl.style.height = "auto";

    vscode.postMessage({
      action: "sendMessage",
      text: text || "Analyze this image",
      image: imgToSend ? (imgToSend.path || imgToSend.dataUrl) : undefined
    });

    setStreaming(true);
  }

  function closeHistory() {
    historyPanel.classList.add("hidden");
  }

  function showWelcome() {
    if (messagesEl.children.length === 0) {
      var welcome = document.createElement("div");
      welcome.className = "welcome";
      welcome.id = "welcome-card";
      welcome.innerHTML =
        '<div class="welcome-icon">\u26a1</div>' +
        '<h2>AlpieCode AI Agent</h2>' +
        '<p>Ask a question, request code generation, or attach screenshots (\ud83d\udcce).</p>';
      messagesEl.appendChild(welcome);
    }
  }

  function clearWelcome() {
    var w = document.getElementById("welcome-card");
    if (w) w.remove();
  }

  // ---- Agent Event Handler ----

  function handleAgentEvent(event) {
    if (!event) return;
    switch (event.type) {
      case "thinking":
        var thinkText = event.data.content || event.data.text || event.data.delta || "";
        if (thinkText) appendThinking(thinkText);
        break;
      case "message":
      case "token":
        var tokenText = event.data.content || event.data.text || event.data.delta || "";
        if (tokenText) appendAssistantToken(tokenText);
        break;
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

  // ---- Change Plan Card ----

  function renderChangePlan(data) {
    finalizeAssistantMessage(); // close any open assistant message

    var card = document.createElement("div");
    card.className = "change-plan-card";

    // Header
    var header = document.createElement("div");
    header.className = "change-plan-header";
    header.innerHTML =
      '<span class="change-plan-icon">\ud83d\udccb</span>' +
      '<span class="change-plan-title">Proposed Change Plan</span>';
    card.appendChild(header);

    // File info
    var fileInfo = document.createElement("div");
    fileInfo.className = "change-plan-file";
    fileInfo.textContent = "\ud83d\udcc4 " + (data.fileName || "file");
    card.appendChild(fileInfo);

    // Summary
    if (data.summary) {
      var summary = document.createElement("div");
      summary.className = "change-plan-summary";
      summary.textContent = data.summary;
      card.appendChild(summary);
    }

    // Diff view
    if (data.diff && data.diff.length > 0) {
      var diffBlock = document.createElement("div");
      diffBlock.className = "change-plan-diff";

      data.diff.forEach(function(line) {
        var lineEl = document.createElement("div");
        lineEl.className = "diff-line diff-" + line.type;
        var prefix = line.type === "removed" ? "- " : (line.type === "added" ? "+ " : "  ");
        lineEl.textContent = prefix + line.text;
        diffBlock.appendChild(lineEl);
      });

      card.appendChild(diffBlock);
    }

    // Action buttons
    var actions = document.createElement("div");
    actions.className = "change-plan-actions";

    var acceptBtn = document.createElement("button");
    acceptBtn.className = "cp-btn cp-accept";
    acceptBtn.textContent = "\u2705 Accept";
    acceptBtn.addEventListener("click", function() {
      acceptBtn.disabled = true;
      rejectBtn.disabled = true;
      editBtn.disabled = true;
      card.classList.add("change-plan-resolved");
      appendSystemMessage("\u2705 Change accepted — applying...");
      vscode.postMessage({ action: "acceptChange" });
    });

    var rejectBtn = document.createElement("button");
    rejectBtn.className = "cp-btn cp-reject";
    rejectBtn.textContent = "\u274c Reject";
    rejectBtn.addEventListener("click", function() {
      acceptBtn.disabled = true;
      rejectBtn.disabled = true;
      editBtn.disabled = true;
      card.classList.add("change-plan-resolved");
      vscode.postMessage({ action: "rejectChange" });
    });

    var editBtn = document.createElement("button");
    editBtn.className = "cp-btn cp-edit";
    editBtn.textContent = "\u270f\ufe0f Edit Request";
    editBtn.addEventListener("click", function() {
      // Toggle inline feedback textarea
      var existing = card.querySelector(".edit-request-container");
      if (existing) {
        existing.remove();
        return;
      }

      var container = document.createElement("div");
      container.className = "edit-request-container";

      var textarea = document.createElement("textarea");
      textarea.className = "edit-request-input";
      textarea.placeholder = "Describe what you want changed instead...";
      textarea.rows = 3;

      var submitBtn = document.createElement("button");
      submitBtn.className = "cp-btn cp-accept";
      submitBtn.textContent = "Send \u27a4";
      submitBtn.addEventListener("click", function() {
        var feedback = textarea.value.trim();
        if (!feedback) return;
        acceptBtn.disabled = true;
        rejectBtn.disabled = true;
        editBtn.disabled = true;
        card.classList.add("change-plan-resolved");
        vscode.postMessage({ action: "editRequest", text: feedback });
      });

      textarea.addEventListener("keydown", function(e) {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          submitBtn.click();
        }
      });

      container.appendChild(textarea);
      container.appendChild(submitBtn);
      card.appendChild(container);
      textarea.focus();
    });

    actions.appendChild(acceptBtn);
    actions.appendChild(rejectBtn);
    actions.appendChild(editBtn);
    card.appendChild(actions);

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  // ---- Message Renderers ----

  function appendUserMessage(text, imageSrc) {
    var el = document.createElement("div");
    el.className = "msg user";

    if (imageSrc) {
      var imgEl = document.createElement("img");
      imgEl.className = "msg-user-img";
      imgEl.src = imageSrc;
      imgEl.alt = "Attached image";
      el.appendChild(imgEl);
    }

    var textEl = document.createElement("div");
    textEl.className = "msg-user-text";
    textEl.textContent = text;
    el.appendChild(textEl);

    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function appendSystemMessage(text) {
    var el = document.createElement("div");
    el.className = "system-message";
    el.textContent = text;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function appendThinking(text) {
    if (!currentThinkingEl) {
      var block = document.createElement("div");
      block.className = "thinking-block";
      if (!showThinking) block.style.display = "none";

      var hdr = document.createElement("div");
      hdr.className = "thinking-header";
      hdr.innerHTML = '<span class="chevron">\u25bc</span> <span>\ud83d\udcad Thinking</span>';

      var content = document.createElement("div");
      content.className = "thinking-content";
      content.textContent = text;

      hdr.addEventListener("click", function() {
        hdr.classList.toggle("collapsed");
        content.classList.toggle("collapsed");
      });

      block.appendChild(hdr);
      block.appendChild(content);
      messagesEl.appendChild(block);
      currentThinkingEl = content;
    } else {
      currentThinkingEl.textContent += (currentThinkingEl.textContent ? "\n" : "") + text;
    }
    scrollToBottom();
  }

  function appendToolCall(data) {
    var card = document.createElement("div");
    card.className = "tool-card";

    var icon = getToolIcon(data.name);
    var argsText = "";
    if (data.arguments) {
      var args = typeof data.arguments === "string" ? tryParse(data.arguments) : data.arguments;
      argsText = formatArgs(args);
    }

    card.innerHTML =
      '<div class="tool-header"><span>' + icon + '</span> <span>' + escapeHtml(data.name || "tool") + '</span></div>' +
      (argsText ? '<div class="tool-args">' + escapeHtml(argsText) + '</div>' : "");

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  function appendToolResult(data) {
    var card = document.createElement("div");
    card.className = "tool-result";

    var output = data.output || data.content || data.result || JSON.stringify(data);
    var display = typeof output === "string"
      ? (output.length > 400 ? output.substring(0, 400) + "..." : output)
      : JSON.stringify(output, null, 2);

    card.innerHTML =
      '<div class="tool-result-header"><span>\u2705</span> <span>Result</span></div>' +
      '<div class="tool-result-content">' + escapeHtml(display) + '</div>';

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
    var el = document.createElement("div");
    el.className = "error-card";
    el.textContent = "\u274c " + text;
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
      var backend = status.backend || "";
      if (backend.length > 35) backend = backend.substring(0, 35) + "\u2026";
      statusText.textContent = "Connected \u00b7 " + backend;
    } else {
      statusText.textContent = "Offline \u2014 run: alpiecode serve";
    }
  }

  function scrollToBottom() {
    requestAnimationFrame(function() {
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
    conversations.forEach(function(conv) {
      var item = document.createElement("div");
      item.className = "history-item" + (conv.id === activeConversationId ? " active" : "");
      var ago = timeAgo(conv.createdAt);

      item.innerHTML =
        '<div class="history-item-content">' +
        '  <div class="history-title">' + escapeHtml(conv.title) + '</div>' +
        '  <div class="history-meta">' + conv.messageCount + ' messages \u00b7 ' + ago + '</div>' +
        '</div>' +
        '<button class="history-delete" title="Delete">\ud83d\uddd1</button>';

      item.querySelector(".history-item-content").addEventListener("click", function() {
        activeConversationId = conv.id;
        vscode.postMessage({ action: "loadConversation", id: conv.id });
        closeHistory();
      });

      item.querySelector(".history-delete").addEventListener("click", function(e) {
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
    messages.forEach(function(msg) {
      if (msg.role === "user") {
        appendUserMessage(msg.content, msg.image);
      } else if (msg.role === "assistant" && msg.content) {
        var el = document.createElement("div");
        el.className = "msg assistant";
        el.innerHTML = renderMarkdown(msg.content);
        messagesEl.appendChild(el);
      }
    });
    scrollToBottom();
  }

  // ---- Utilities ----

  function getToolIcon(name) {
    var icons = {
      write_file: "\ud83d\udcdd", edit_file: "\u270f\ufe0f", read_file: "\ud83d\udcd6",
      bash: "\u26a1", file_search: "\ud83d\udd0d", list_files: "\ud83d\udcc1",
      apply_patch: "\ud83e\de79", web_search: "\ud83c\udf10", fetch_url: "\ud83d\udd17",
      view_image: "\ud83d\uddbc\ufe0f", clone_repo: "\ud83d\udc19", update_plan: "\ud83d\udccb"
    };
    return icons[name] || "\ud83d\udd27";
  }

  function formatArgs(args) {
    if (!args || typeof args !== "object") return String(args || "");
    var lines = [];
    for (var key in args) {
      if (!args.hasOwnProperty(key)) continue;
      var val = typeof args[key] === "string"
        ? (args[key].length > 150 ? args[key].substring(0, 150) + "..." : args[key])
        : JSON.stringify(args[key]);
      lines.push(key + ": " + val);
    }
    return lines.join("\n");
  }

  function tryParse(str) {
    try { return JSON.parse(str); } catch(e) { return str; }
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function timeAgo(ts) {
    var diff = Date.now() - ts;
    var mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    var hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    var days = Math.floor(hrs / 24);
    return days + "d ago";
  }

  function renderMarkdown(text) {
    if (!text) return "";
    var html = text;

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(_, lang, code) {
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
