
  // ---- Active Selection Context Pill ----
  var activeSelectionContext = null;

  function renderSelectionPill(data) {
    removeSelectionPill();
    if (!data || !data.fileName) return;

    var pill = document.createElement("div");
    pill.id = "selection-pill";
    pill.className = "selection-pill";
    pill.innerHTML =
      '<span>📎 ' + escapeHtml(data.fileName + ':' + data.range) + '</span>' +
      '<span class="selection-pill-close" title="Dismiss">✕</span>';

    pill.querySelector(".selection-pill-close").addEventListener("click", function() {
      activeSelectionContext = null;
      removeSelectionPill();
    });

    var inputArea = document.getElementById("input-area");
    if (inputArea) {
      inputArea.insertBefore(pill, inputArea.firstChild);
    }
  }

  function removeSelectionPill() {
    var existing = document.getElementById("selection-pill");
    if (existing) existing.remove();
  }
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

  // ---- Monochromatic Vector Iconography (Google Antigravity Standard) ----
  const ICONS = {
    sparkle: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M7.5 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0V.5a.5.5 0 0 1 .5-.5zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2a.5.5 0 0 1 .5-.5zm7.5-5.5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zm-13 0a.5.5 0 0 1-.5.5H.5a.5.5 0 0 1 0-1h1a.5.5 0 0 1 .5.5zM8 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/></svg>',
    document: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4 0h5.5v1H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6.5h1V14a3 3 0 0 1-3 3H4a3 3 0 0 1-3-3V3a3 3 0 0 1 3-3z"/><path d="M9.5 0v4.5A1.5 1.5 0 0 0 11 6h4.5l-6-6z"/></svg>',
    terminal: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M1.5 2.5a.5.5 0 0 0-.5.5v10a.5.5 0 0 0 .5.5h13a.5.5 0 0 0 .5-.5V3a.5.5 0 0 0-.5-.5h-13zM0 3a1.5 1.5 0 0 1 1.5-1.5h13A1.5 1.5 0 0 1 16 3v10a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 13V3zm3.854 2.146a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708-.708L2.793 6 1.646 4.854a.5.5 0 1 1 .708-.708l1.5 1.5zM6.5 8.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H7a.5.5 0 0 1-.5-.5z"/></svg>',
    check: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>',
    cross: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/></svg>',
    github: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>',
    diff: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M1 2.5A1.5 1.5 0 0 1 2.5 1h11A1.5 1.5 0 0 1 15 2.5v11a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5v11a.5.5 0 0 0 .5.5h5V2h-5zm6 12h5a.5.5 0 0 0 .5-.5v-11a.5.5 0 0 0-.5-.5h-5v12z"/></svg>',
    bolt: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M11.251.068a.5.5 0 0 1 .42.58L10.077 6H14.5a.5.5 0 0 1 .372.832l-9.5 10.5a.5.5 0 0 1-.844-.512L5.923 10H1.5a.5.5 0 0 1-.372-.832l9.5-10.5a.5.5 0 0 1 .123-.1z"/></svg>',
    brain: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V15a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-1.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7zm2 13H6v-1h4v1zm1.75-2.82l-.46.32H4.71l-.46-.32A5.98 5.98 0 0 1 2 8a6 6 0 1 1 12 0c0 1.95-.94 3.7-2.25 4.88z"/></svg>',
    pencil: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708l-3-3zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207l6.5-6.5zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.499.499 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11l.178-.178z"/></svg>',
    search: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>',
    folder: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M.54 3.87.5 3a2 2 0 0 1 2-2h3.672a2 2 0 0 1 1.414.586l.828.828A2 2 0 0 0 9.828 3h4.672a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2.5a2 2 0 0 1-2-2V4.5a2 2 0 0 1 .04-.63zM1.5 4.5v7.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1H9.828a3 3 0 0 1-2.12-.879l-.83-.828A1 1 0 0 0 6.172 2H2.5a1 1 0 0 0-1 1v1.5z"/></svg>',
    copy: '<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/></svg>',
  };

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
  const headerLeft        = document.getElementById("header-left");
  const startServerBtn    = document.getElementById("start-server-btn");
  const thinkingCheck     = document.getElementById("thinking-check");
  const tokenBadge        = document.getElementById("token-badge");
  const liveBuildBar      = document.getElementById("live-build-bar");
  const liveBuildText     = document.getElementById("live-build-text");
  const scrollBottomBtn   = document.getElementById("scroll-bottom-btn");
  const activeContextBar  = document.getElementById("active-context-bar");
  const acFilename        = document.getElementById("ac-filename");
  const acRemoveBtn       = document.getElementById("ac-remove-btn");
  let lastTokenStats      = { tokPerSec: 0, tokenCount: 0, sessionTotal: 0 };

  // Slash Commands DOM
  const slashPopup        = document.getElementById("slash-popup");
  const slashList         = document.getElementById("slash-list");

  // Reasoning Selector DOM
  const reasoningBtn      = document.getElementById("reasoning-btn");
  const reasoningMenu     = document.getElementById("reasoning-menu");
  const reasoningIcon     = document.getElementById("reasoning-icon");
  const reasoningLabel    = document.getElementById("reasoning-label");
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


  // ---- Slash Commands Registry ----
  const SLASH_COMMANDS = [
    {
      cmd: "/fix",
      title: "fix",
      desc: "Auto-scan workspace diagnostics & linter errors and comprehensively fix them",
      icon: ICONS.pencil,
      action: "fix"
    },
    {
      cmd: "/rollback",
      title: "rollback",
      desc: "Revert all uncommitted modifications back to last git commit",
      icon: ICONS.cross,
      action: "rollback"
    },
    {
      cmd: "/plan",
      title: "plan",
      desc: "Analyze codebase & generate an implementation plan without making changes",
      icon: ICONS.document,
      prompt: "/plan "
    },
    {
      cmd: "/explain",
      title: "explain",
      desc: "Explain a file, function, architecture, or codebase concept in detail",
      icon: ICONS.sparkle,
      prompt: "/explain "
    },
    {
      cmd: "/doctor",
      title: "doctor",
      desc: "Run system diagnostic health checks (Python, CUDA, Compilers, Network)",
      icon: ICONS.bolt,
      prompt: "Run alpiecode doctor diagnostic checks and summarize results"
    },
    {
      cmd: "/test",
      title: "test",
      desc: "Generate comprehensive unit tests and execute automated verification",
      icon: ICONS.terminal,
      prompt: "Generate unit tests for this project, run them in sandbox, and ensure all tests pass"
    },
    {
      cmd: "/diff",
      title: "diff",
      desc: "Show recent changes made by AlpieCode since last checkpoint",
      icon: ICONS.diff,
      prompt: "Show git diff of recent changes made in this session"
    },
    {
      cmd: "/push",
      title: "push",
      desc: "Push completed project changes to GitHub repository",
      icon: ICONS.github,
      action: "push"
    },
    {
      cmd: "/clear",
      title: "clear",
      desc: "Start a fresh, clean conversation session",
      icon: ICONS.cross,
      action: "clear"
    }
  ];

  let activeSlashIndex = 0;
  let currentFilteredCommands = [];
  let currentReasoningLevel = "thinking";

  try {
    const saved = localStorage.getItem("alpiecode.reasoningLevel");
    if (saved === "no-thinking" || saved === "low") {
      currentReasoningLevel = "no-thinking";
    } else if (saved === "thinking" || saved === "high" || saved === "medium") {
      currentReasoningLevel = "thinking";
    }
  } catch(e) {}
  updateReasoningUI(currentReasoningLevel);

  // ---- Reasoning Level Dropdown (Thinking vs No-Thinking) ----
  if (reasoningBtn && reasoningMenu) {
    reasoningBtn.addEventListener("click", function(e) {
      e.stopPropagation();
      reasoningMenu.classList.toggle("hidden");
    });

    document.addEventListener("click", function(e) {
      if (!reasoningBtn.contains(e.target) && !reasoningMenu.contains(e.target)) {
        reasoningMenu.classList.add("hidden");
      }
    });

    document.querySelectorAll(".reasoning-option").forEach(function(opt) {
      opt.addEventListener("click", function() {
        const level = opt.getAttribute("data-level");
        if (level) {
          currentReasoningLevel = level;
          try { localStorage.setItem("alpiecode.reasoningLevel", level); } catch(e) {}
          updateReasoningUI(level);
          reasoningMenu.classList.add("hidden");
        }
      });
    });
  }

  function updateReasoningUI(level) {
    if (!reasoningIcon || !reasoningLabel) return;
    const labels = {
      "thinking": { icon: ICONS.brain, text: "Thinking" },
      "no-thinking": { icon: ICONS.bolt, text: "No-Thinking" },
      // Backward compatibility aliases
      "high": { icon: ICONS.brain, text: "Thinking" },
      "medium": { icon: ICONS.brain, text: "Thinking" },
      "low": { icon: ICONS.bolt, text: "No-Thinking" }
    };
    const info = labels[level] || labels["thinking"];
    reasoningIcon.innerHTML = info.icon;
    reasoningLabel.textContent = info.text;

    document.querySelectorAll(".reasoning-option").forEach(function(opt) {
      opt.classList.toggle("active", opt.getAttribute("data-level") === level);
    });
  }

  // ---- Slash Commands Popup Logic ----
  function checkSlashTrigger() {
    const val = inputEl.value;
    if (val.startsWith("/")) {
      const query = val.slice(1).toLowerCase().trim();
      currentFilteredCommands = SLASH_COMMANDS.filter(function(c) {
        return c.cmd.slice(1).toLowerCase().startsWith(query) || c.title.toLowerCase().includes(query);
      });

      if (currentFilteredCommands.length > 0) {
        activeSlashIndex = 0;
        renderSlashPopup();
        slashPopup.classList.remove("hidden");
      } else {
        hideSlashPopup();
      }
    } else {
      hideSlashPopup();
    }
  }

  function hideSlashPopup() {
    if (slashPopup) slashPopup.classList.add("hidden");
  }

  function renderSlashPopup() {
    if (!slashList) return;
    slashList.innerHTML = "";

    currentFilteredCommands.forEach(function(item, idx) {
      const el = document.createElement("div");
      el.className = "slash-item" + (idx === activeSlashIndex ? " active" : "");
      el.innerHTML =
        '<span class="slash-item-icon">' + item.icon + '</span>' +
        '<div class="slash-item-info">' +
        '  <span class="slash-item-cmd">' + item.cmd + '</span>' +
        '  <span class="slash-item-desc">' + item.desc + '</span>' +
        '</div>';

      el.addEventListener("click", function() {
        selectSlashCommand(item);
      });

      slashList.appendChild(el);
    });
  }

  function selectSlashCommand(item) {
    hideSlashPopup();
    if (item.action === "clear") {
      newChatBtn.click();
      return;
    }
    if (item.action === "push") {
      vscode.postMessage({ action: "requestGitPush" });
      return;
    }
    if (item.action === "fix") {
      vscode.postMessage({ action: "fixDiagnostics" });
      return;
    }
    if (item.action === "rollback") {
      vscode.postMessage({ action: "rollbackChanges" });
      return;
    }
    inputEl.value = item.prompt || (item.cmd + " ");
    inputEl.focus();
    inputEl.style.height = "auto";
    inputEl.style.height = Math.max(72, Math.min(inputEl.scrollHeight, 220)) + "px";
  }

  if (acRemoveBtn && activeContextBar) {
    acRemoveBtn.addEventListener("click", function() {
      activeContextBar.classList.add("hidden");
      activeContextBar.removeAttribute("data-path");
    });
  }

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
    // Slash popup navigation
    if (slashPopup && !slashPopup.classList.contains("hidden") && currentFilteredCommands.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeSlashIndex = (activeSlashIndex + 1) % currentFilteredCommands.length;
        renderSlashPopup();
        return;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeSlashIndex = (activeSlashIndex - 1 + currentFilteredCommands.length) % currentFilteredCommands.length;
        renderSlashPopup();
        return;
      } else if (e.key === "Enter" || e.key === "Tab") {
        if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
          e.preventDefault();
          selectSlashCommand(currentFilteredCommands[activeSlashIndex]);
          return;
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        hideSlashPopup();
        return;
      }
    }

    if (e.key === "Enter") {
      if (e.shiftKey) {
        // Shift+Enter: allow default multiline newline
        return;
      }
      e.preventDefault();
      sendMessage();
    }
  });

  inputEl.addEventListener("input", function() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.max(72, Math.min(inputEl.scrollHeight, 220)) + "px";
    checkSlashTrigger();
  });

  if (headerLeft) {
    headerLeft.addEventListener("click", function() {
      if (!statusDot.classList.contains("online")) {
        statusText.textContent = "Starting server…";
        statusDot.className = "dot starting";
        if (startServerBtn) startServerBtn.classList.add("hidden");
        vscode.postMessage({ action: "startServer" });
      } else {
        vscode.postMessage({ action: "checkStatus" });
      }
    });
  }

  if (startServerBtn) {
    startServerBtn.addEventListener("click", function(e) {
      e.stopPropagation();
      statusText.textContent = "Starting server…";
      statusDot.className = "dot starting";
      startServerBtn.classList.add("hidden");
      vscode.postMessage({ action: "startServer" });
    });
  }

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


  // ---- Live Build Status Bar & Stepper ----
  function updateBuildStatus(data) {
    var bar = document.getElementById("live-build-bar");
    var txt = document.getElementById("live-build-text");
    if (!bar || !txt) return;

    if (!data || data.status === "idle") {
      bar.classList.add("hidden");
      return;
    }

    bar.classList.remove("hidden");
    var status = data.status || "building";
    var msg = data.message || "Building...";

    // Map status/phase to step index (1-based)
    var stepIndex = 1;
    if (status === "rephrasing") { stepIndex = 1; }
    else if (status === "plan") { stepIndex = 2; }
    else if (status === "files" || status === "building") { stepIndex = 3; }
    else if (status === "verify") { stepIndex = 4; }
    else if (status === "complete") { stepIndex = 5; }

    var steps = bar.querySelectorAll(".stepper-step");
    var stepNames = ["rephrase", "plan", "files", "verify", "done"];

    steps.forEach(function(s, idx) {
      var sIdx = idx + 1;
      s.classList.remove("active", "completed");
      if (sIdx < stepIndex || (status === "complete" && sIdx <= 5)) {
        s.classList.add("completed");
      } else if (sIdx === stepIndex) {
        s.classList.add("active");
      }
    });

    var spinner = bar.querySelector(".live-build-spinner");
    if (spinner) {
      spinner.innerHTML = status === "rephrasing" ? ICONS.sparkle : (status === "complete" ? ICONS.check : ICONS.terminal);
    }
    txt.textContent = msg;

    if (status === "complete") {
      setTimeout(function() {
        bar.classList.add("hidden");
      }, 4000);
    }
  }

  // ---- Interactive GitHub Push Card ----
  function renderGitPushPrompt(data) {
    var existing = document.getElementById("github-push-card");
    if (existing) existing.remove();

    var card = document.createElement("div");
    card.id = "github-push-card";
    card.className = "github-push-card";

    var username = escapeHtml(data.username || "developer");
    var branch = escapeHtml(data.branch || "main");
    var remoteText = data.remote ? escapeHtml(data.remote) : "New Remote Repository";

    card.innerHTML =
      '<div class="github-push-header">' +
        '<span class="github-icon">' + ICONS.github + '</span>' +
        '<span class="github-push-title">GitHub Code Push</span>' +
      '</div>' +
      '<div class="github-push-body">' +
        '<p class="github-push-question">Do you want to push the code to GitHub with username <strong class="github-user-tag">@' + username + '</strong>?</p>' +
        '<div class="github-push-meta">' +
          '<span>Branch: <code>' + branch + '</code></span>' +
          '<span>Target: <code>' + remoteText + '</code></span>' +
        '</div>' +
      '</div>' +
      '<div class="github-push-actions">' +
        '<button id="push-confirm-btn" class="push-btn-confirm">' + ICONS.check + ' Yes, Push to GitHub</button>' +
        '<button id="push-change-btn" class="push-btn-change">' + ICONS.pencil + ' Change Push ID</button>' +
        '<button id="push-skip-btn" class="push-btn-skip">' + ICONS.cross + ' Skip</button>' +
      '</div>';

    card.querySelector("#push-confirm-btn").addEventListener("click", function() {
      card.querySelector(".github-push-actions").innerHTML = '<span class="push-spinner">⏳ Pushing code to GitHub...</span>';
      vscode.postMessage({
        action: "confirmGitPush",
        username: data.username,
        branch: data.branch,
        workdir: data.workdir
      });
    });

    card.querySelector("#push-change-btn").addEventListener("click", function() {
      vscode.postMessage({
        action: "changeGitUsername",
        currentUsername: data.username,
        branch: data.branch,
        workdir: data.workdir
      });
    });

    card.querySelector("#push-skip-btn").addEventListener("click", function() {
      card.remove();
      vscode.postMessage({ action: "dismissGitPush" });
    });

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  // ---- Webview Message Handler ----
  window.addEventListener("message", function(e) {
    var message = e.data;
    switch (message.action) {
      case "serverStatus":
        updateStatus(message.status);
        break;
      case "walkthrough":
        renderWalkthroughCard(message.data);
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
        unifiedWorkBlock = null;
        unifiedWorkHeader = null;
        unifiedWorkContent = null;
        unifiedStartTime = Date.now();
        break;
      case "streamEnd":
        setStreaming(false);
        finalizeAssistantMessage();
        updateBuildStatus({ status: "complete" });
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
      case "activeFileContext":
        if (activeContextBar && acFilename && message.data) {
          activeContextBar.classList.remove("hidden");
          acFilename.textContent = message.data.fileName || message.data.filePath;
          activeContextBar.setAttribute("data-path", message.data.filePath);
        }
        break;
      case "updateSelectionContext":
        activeSelectionContext = message.data;
        renderSelectionPill(message.data);
        break;
      case "clearSelectionContext":
        if (activeSelectionContext && !activeSelectionContext.pinned) {
          activeSelectionContext = null;
          removeSelectionPill();
        }
        break;
      case "tokenStats":
        updateTokenStats(message);
        break;
      case "buildStatus":
        updateBuildStatus(message);
        break;
      case "gitPushPrompt":
        renderGitPushPrompt(message.data);
        break;
      case "gitPushResult":
        var pushCard = document.getElementById("github-push-card");
        if (pushCard) pushCard.remove();
        if (message.success) {
          appendSystemMessage("✅ **" + message.message + "**" + (message.output ? "\n```\n" + message.output + "\n```" : ""));
        } else {
          appendError("❌ " + message.error);
        }
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
    inputEl.style.height = "72px";

    updateBuildStatus({ status: "rephrasing", message: "Solidifying prompt requirements..." });

    vscode.postMessage({
      action: "sendMessage",
      text: text || "Analyze this image",
      image: imgToSend ? (imgToSend.path || imgToSend.dataUrl) : undefined,
      reasoningLevel: currentReasoningLevel
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
        '<div class="welcome-header">' +
          '<div class="welcome-icon">' + ICONS.sparkle + '</div>' +
          '<h2>AlpieCode Agent</h2>' +
          '<p class="welcome-sub">Autonomous AI pair programmer powered by 169Pi</p>' +
        '</div>' +
        '<div class="starter-chips-container">' +
          '<div class="starter-chips-label">Quick Actions</div>' +
          '<div class="starter-chips">' +
            '<button class="starter-chip" data-prompt="Generate comprehensive unit tests for this project and verify them" type="button">' +
              '<span class="chip-icon">' + ICONS.terminal + '</span> Unit Tests' +
            '</button>' +
            '<button class="starter-chip" data-prompt="Audit this codebase, identify bugs or bottlenecks, and optimize them" type="button">' +
              '<span class="chip-icon">' + ICONS.search + '</span> Fix Bugs & Audit' +
            '</button>' +
            '<button class="starter-chip" data-prompt="Explain the architecture, key workflows, and data structures in this project" type="button">' +
              '<span class="chip-icon">' + ICONS.document + '</span> Explain Architecture' +
            '</button>' +
            '<button class="starter-chip" data-prompt="Create an implementation plan to build a new feature cleanly" type="button">' +
              '<span class="chip-icon">' + ICONS.pencil + '</span> Plan Feature' +
            '</button>' +
          '</div>' +
        '</div>';

      welcome.querySelectorAll(".starter-chip").forEach(function(chip) {
        chip.addEventListener("click", function() {
          var prompt = chip.getAttribute("data-prompt") || "";
          inputEl.value = prompt;
          inputEl.focus();
          inputEl.style.height = "auto";
          inputEl.style.height = Math.max(72, Math.min(inputEl.scrollHeight, 220)) + "px";
        });
      });

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
      case "status":
        updateBuildStatus(event.data);
        break;
      case "thinking_start":
        startThinkingCapsule(event.data);
        break;
      case "thinking_delta":
        appendThinkingDelta(event.data);
        break;
      case "thinking_end":
        endThinkingCapsule(event.data);
        break;
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
      case "stall_intervention":
        appendSystemMessage("🔄 Progress stall detected. Agent is adjusting strategy...");
        break;
      case "safety_ceiling":
        appendSystemMessage("🛑 Safety ceiling reached (emergency stop).");
        finalizeAssistantMessage();
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

    var diffBtn = document.createElement("button");
    diffBtn.className = "cp-btn cp-diff";
    diffBtn.textContent = "🔍 Review Diff";
    diffBtn.title = "Open side-by-side diff in VS Code editor";
    diffBtn.addEventListener("click", function() {
      vscode.postMessage({ action: "openDiff" });
    });
    actions.appendChild(diffBtn);

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

  // ---- Antigravity Unified Work Capsule System (Single Collapsible Work Header) ----
  var unifiedWorkBlock = null;
  var unifiedWorkHeader = null;
  var unifiedWorkContent = null;
  var unifiedStartTime = 0;
  var unifiedTimerInterval = null;

  function startWorkTimer() {
    if (unifiedTimerInterval) clearInterval(unifiedTimerInterval);
    if (!unifiedStartTime) unifiedStartTime = Date.now();
    unifiedTimerInterval = setInterval(function() {
      if (!unifiedWorkHeader) return;
      var elapsed = Math.max(1, Math.round((Date.now() - unifiedStartTime) / 1000));
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl && titleEl.classList.contains("running")) {
        titleEl.textContent = "Thinking (" + elapsed + "s)...";
      }
    }, 1000);
  }

  function pauseWorkTimer() {
    if (unifiedTimerInterval) {
      clearInterval(unifiedTimerInterval);
      unifiedTimerInterval = null;
    }
    if (!unifiedWorkHeader) return;
    var elapsed = Math.max(1, Math.round((Date.now() - unifiedStartTime) / 1000));
    var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
    if (titleEl) {
      titleEl.className = "thought-capsule-title";
      titleEl.textContent = "Worked for " + elapsed + "s";
    }
    unifiedWorkHeader.classList.remove("expanded");
    if (unifiedWorkContent) {
      unifiedWorkContent.classList.add("collapsed");
    }
  }

  function ensureWorkCapsule() {
    if (unifiedWorkBlock) return;

    unifiedStartTime = Date.now();

    var block = document.createElement("div");
    block.className = "thought-capsule-block";

    var hdr = document.createElement("div");
    hdr.className = "thought-capsule-header expanded";
    hdr.setAttribute("role", "button");
    hdr.setAttribute("tabindex", "0");
    hdr.innerHTML =
      '<span class="thought-capsule-title running">Thinking (1s)...</span>' +
      '<span class="thought-capsule-chevron">›</span>';

    var content = document.createElement("div");
    content.className = "thought-capsule-content";
    content.textContent = "";

    hdr.addEventListener("click", function() {
      var isExp = hdr.classList.toggle("expanded");
      content.classList.toggle("collapsed", !isExp);
    });

    block.appendChild(hdr);
    block.appendChild(content);
    messagesEl.appendChild(block);

    unifiedWorkBlock = block;
    unifiedWorkHeader = hdr;
    unifiedWorkContent = content;
    currentThinkingEl = content;

    startWorkTimer();
    scrollToBottom();
  }

  function appendThinkingDelta(data) {
    var delta = (data && data.delta) ? data.delta : (typeof data === "string" ? data : "");
    if (!delta) return;
    ensureWorkCapsule();

    // Keep header active and expanded while reasoning is streaming
    if (unifiedWorkHeader) {
      unifiedWorkHeader.classList.add("expanded");
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl && !titleEl.classList.contains("running")) {
        titleEl.classList.add("running");
        startWorkTimer();
      }
    }
    if (unifiedWorkContent) {
      unifiedWorkContent.classList.remove("collapsed");
      unifiedWorkContent.textContent += delta;
      unifiedWorkContent.scrollTop = unifiedWorkContent.scrollHeight;
    }
    scrollToBottom();
  }

  function appendThinking(text) {
    if (!text) return;
    ensureWorkCapsule();
    if (unifiedWorkHeader) {
      unifiedWorkHeader.classList.add("expanded");
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl && !titleEl.classList.contains("running")) {
        titleEl.classList.add("running");
        startWorkTimer();
      }
    }
    if (unifiedWorkContent) {
      unifiedWorkContent.classList.remove("collapsed");
      if (unifiedWorkContent.textContent.trim()) {
        unifiedWorkContent.textContent += "\n\n" + text;
      } else {
        unifiedWorkContent.textContent = text;
      }
      unifiedWorkContent.scrollTop = unifiedWorkContent.scrollHeight;
    }
    scrollToBottom();
  }

  function finalizeWorkCapsule(durationSec) {
    pauseWorkTimer();
    if (durationSec && unifiedWorkHeader) {
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl) {
        titleEl.textContent = "Worked for " + durationSec + "s";
      }
    }
  }

  function startThinkingCapsule(data) {
    ensureWorkCapsule();
    if (unifiedWorkHeader) {
      unifiedWorkHeader.classList.add("expanded");
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl) {
        titleEl.classList.add("running");
        titleEl.textContent = "Thinking (1s)...";
      }
      startWorkTimer();
    }
    if (unifiedWorkContent) {
      unifiedWorkContent.classList.remove("collapsed");
    }
  }

  function endThinkingCapsule(data) {
    // Keep content visible during execution; will collapse when assistant response starts
    if (data && data.duration && unifiedWorkHeader) {
      var titleEl = unifiedWorkHeader.querySelector(".thought-capsule-title");
      if (titleEl) {
        titleEl.textContent = "Worked for " + Math.round(data.duration) + "s";
      }
    }
  }

  // ---- Antigravity Artifact Card for walkthrough.md ----
  function renderWalkthroughCard(data) {
    if (!data) return;
    var existing = document.getElementById("walkthrough-card");
    if (existing) existing.remove();

    var card = document.createElement("div");
    card.id = "walkthrough-card";
    card.className = "antigravity-artifact-card";

    var filePath = data.path || "walkthrough.md";
    var files = data.files || [];
    var commands = data.commands || [];

    var fileStats = data.fileStats || {};
    var filesHtml = "";
    files.forEach(function(f) {
      var safeF = escapeHtml(f);
      var stat = fileStats[f] || fileStats[safeF] || null;
      var statBadge = "";
      if (stat) {
        statBadge = '<span class="diff-stat-badge"><span class="diff-add">+' + (stat.added || 0) + '</span><span class="diff-del">-' + (stat.removed || 0) + '</span></span>';
      }
      filesHtml +=
        '<div class="walkthrough-file-item" data-path="' + safeF + '" title="Click to inspect diff for ' + safeF + '">' +
          '<div class="file-item-left">' +
            '<span class="file-badge edit">' + (safeF.endsWith(".md") ? "DOC" : "EDIT") + '</span>' +
            '<span class="file-name">' + safeF + '</span>' +
          '</div>' +
          '<div class="file-item-right">' +
            statBadge +
            '<button class="file-diff-btn" data-path="' + safeF + '" title="Open side-by-side diff">' + ICONS.diff + '</button>' +
          '</div>' +
        '</div>';
    });

    var cmdsHtml = "";
    commands.forEach(function(c) {
      var cmdStr = escapeHtml(c.command || c.cmd || "");
      var isPass = (c.exit_code === 0 || c.exitCode === 0 || c.exitCode === undefined);
      cmdsHtml +=
        '<div class="walkthrough-cmd-item">' +
          '<span class="vector-icon">' + ICONS.terminal + '</span>' +
          '<span class="cmd-text">' + cmdStr + '</span>' +
          '<span class="cmd-badge ' + (isPass ? 'pass' : 'fail') + '">' + (isPass ? 'Verified' : 'Failed') + '</span>' +
        '</div>';
    });

    card.innerHTML =
      '<div class="artifact-card-header">' +
        '<div class="artifact-card-left">' +
          '<span class="artifact-doc-icon">' + ICONS.document + '</span>' +
          '<div class="artifact-info">' +
            '<span class="artifact-title">walkthrough.md</span>' +
            '<span class="artifact-desc">Project Walkthrough &bull; Changes &amp; Verification</span>' +
          '</div>' +
        '</div>' +
        '<button class="artifact-open-btn" id="open-walkthrough-btn" type="button" title="Open walkthrough.md in editor">Open</button>' +
      '</div>' +
      '<div class="artifact-card-body">' +
        (filesHtml ? '<div class="walkthrough-section-title">Files Created / Modified</div><div class="walkthrough-files-grid">' + filesHtml + '</div>' : '') +
        (cmdsHtml ? '<div class="walkthrough-section-title">Verification</div><div class="walkthrough-cmds-list">' + cmdsHtml + '</div>' : '') +
      '</div>' +
      '<div class="artifact-card-footer">' +
        '<div class="artifact-stats">' +
          '<span>' + files.length + ' file' + (files.length === 1 ? '' : 's') + ' touched</span>' +
          (commands.length > 0 ? '<span> &bull; ' + commands.length + ' command' + (commands.length === 1 ? '' : 's') + '</span>' : '') +
        '</div>' +
        '<button class="review-changes-btn" id="review-changes-btn" type="button" title="View native Git diff of changes">' +
          '<span class="vector-icon">' + ICONS.diff + '</span>' +
          '<span>Review Changes</span>' +
        '</button>' +
      '</div>';

    // Click file to open in editor or diff
    card.querySelectorAll(".walkthrough-file-item").forEach(function(item) {
      item.addEventListener("click", function(evt) {
        var diffBtn = evt.target.closest(".file-diff-btn");
        var p = item.getAttribute("data-path");
        if (diffBtn && p) {
          vscode.postMessage({ action: "openDiffForFile", path: p });
          evt.stopPropagation();
        } else if (p) {
          vscode.postMessage({ action: "openFile", path: p });
        }
      });
    });

    // Click card header or open button to open native Walkthrough Preview (Antigravity standard!)
    var cardHdr = card.querySelector(".artifact-card-header");
    if (cardHdr) {
      cardHdr.addEventListener("click", function() {
        vscode.postMessage({ action: "openWalkthrough" });
      });
    }
    var openBtn = card.querySelector("#open-walkthrough-btn");
    if (openBtn) {
      openBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        vscode.postMessage({ action: "openWalkthrough" });
      });
    }

    // Review changes action button
    var reviewBtn = card.querySelector("#review-changes-btn");
    if (reviewBtn) {
      reviewBtn.addEventListener("click", function() {
        vscode.postMessage({ action: "reviewChanges" });
      });
    }

    messagesEl.appendChild(card);
    scrollToBottom();
  }

  var lastToolCard = null;

  function formatToolSummary(name, args) {
    if (!args || typeof args !== "object") return "";
    if (name === "bash") {
      var cmd = (args.command || "").trim();
      return cmd.length > 45 ? "$ " + cmd.substring(0, 42) + "..." : "$ " + cmd;
    }
    if (name === "write_file" || name === "edit_file" || name === "read_file") {
      var p = args.path || "";
      var extra = "";
      if (name === "write_file" && args.content) {
        var lines = String(args.content).split("\n").length;
        extra = " (" + lines + " lines)";
      }
      return p + extra;
    }
    if (name === "list_files") return args.path || ".";
    if (name === "search" || name === "web_search") return '"' + (args.query || "") + '"';
    return Object.keys(args).filter(function(k) { return k !== "content"; }).map(function(k) {
      return k + "=" + JSON.stringify(args[k]).substring(0, 20);
    }).join(" ");
  }

  function appendToolCall(data) {
    var row = document.createElement("div");
    row.className = "tool-badge-row";

    var icon = getToolIcon(data.name);
    var args = data.arguments;
    if (typeof args === "string") {
      args = tryParse(args);
    }
    var summary = formatToolSummary(data.name, args);

    row.innerHTML =
      '<div class="tool-badge-header">' +
        '<div class="tool-badge-title">' +
          '<span class="tool-badge-icon">' + icon + '</span> ' +
          '<span class="tool-badge-name">' + escapeHtml(data.name || "tool") + '</span> ' +
          '<span class="tool-badge-summary">' + escapeHtml(summary) + '</span>' +
        '</div>' +
        '<span class="tool-badge-status running">⏳</span>' +
      '</div>' +
      '<div class="tool-badge-drawer hidden"></div>';

    var header = row.querySelector(".tool-badge-header");
    var drawer = row.querySelector(".tool-badge-drawer");
    header.addEventListener("click", function() {
      drawer.classList.toggle("hidden");
    });

    messagesEl.appendChild(row);
    lastToolCard = { row: row, drawer: drawer, name: data.name };
    scrollToBottom();
  }

  function appendToolResult(data) {
    var output = data.output || data.content || data.result || "";
    var text = typeof output === "string" ? output : JSON.stringify(output, null, 2);
    var isError = text.toLowerCase().indexOf("error:") !== -1 || text.indexOf('"exit_code": 1') !== -1;

    if (lastToolCard && lastToolCard.row) {
      var statusEl = lastToolCard.row.querySelector(".tool-badge-status");
      if (statusEl) {
        statusEl.className = "tool-badge-status " + (isError ? "error" : "success");
        statusEl.textContent = isError ? "✗" : "✓";
      }
      if (lastToolCard.drawer) {
        var display = text.length > 800 ? text.substring(0, 800) + "\n... (truncated)" : text;
        lastToolCard.drawer.textContent = display;
      }
      lastToolCard = null;
    } else if (isError) {
      // Only display fallback result if it is an actual error
      var fallback = document.createElement("div");
      fallback.className = "tool-badge-row";
      fallback.innerHTML =
        '<div class="tool-badge-header">' +
          '<span class="tool-badge-name">command</span> ' +
          '<span class="tool-badge-status error">✗</span>' +
        '</div>' +
        '<div class="tool-badge-drawer">' + escapeHtml(text.substring(0, 400)) + '</div>';
      messagesEl.appendChild(fallback);
    }
    scrollToBottom();
  }

  function appendAssistantToken(text) {
    if (unifiedWorkHeader && unifiedWorkHeader.querySelector(".thought-capsule-title.running")) {
      pauseWorkTimer();
    }
    currentThinkingEl = null;
    if (!currentAssistantEl) {
      currentAssistantEl = document.createElement("div");
      currentAssistantEl.className = "msg assistant";
      messagesEl.appendChild(currentAssistantEl);
      currentAssistantText = "";
    }
    currentAssistantText += text;

    var trimmed = currentAssistantText.trimEnd();
    var rendered = renderMarkdown(trimmed);
    if (rendered.endsWith("</p>")) {
      rendered = rendered.slice(0, -4) + '<span class="streaming-dot"></span></p>';
    } else {
      rendered += '<span class="streaming-dot"></span>';
    }
    currentAssistantEl.innerHTML = rendered;
    scrollToBottom();
  }

  function finalizeAssistantMessage() {
    finalizeWorkCapsule();
    if (currentAssistantEl) {
      var dot = currentAssistantEl.querySelector(".streaming-dot");
      if (dot) dot.remove();

      var trimmed = (currentAssistantText || "").trim();
      if (!trimmed) {
        currentAssistantEl.remove();
      } else {
        var footer = "";
        if (lastTokenStats.tokenCount > 0) {
          var spd = lastTokenStats.tokPerSec > 0 ? lastTokenStats.tokPerSec + " tok/s" : "";
          var tok = lastTokenStats.tokenCount + " tokens";
          footer = '<div class="msg-token-footer"><span class="token-icon">⚡</span> ' + (spd ? spd + ' · ' : '') + tok + '</div>';
        }
        currentAssistantEl.innerHTML = renderMarkdown(trimmed) + footer;
      }
    }
    currentAssistantEl = null;
    unifiedWorkBlock = null;
    unifiedWorkHeader = null;
    unifiedWorkContent = null;
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
    statusDot.className = "dot " + (status.online ? "online" : (status.starting ? "starting" : "offline"));
    if (status.online) {
      var backend = status.backend || "";
      if (backend.length > 35) backend = backend.substring(0, 35) + "…";
      statusText.textContent = "Connected · " + backend;
      if (startServerBtn) startServerBtn.classList.add("hidden");
    } else if (status.starting) {
      statusText.textContent = "Starting server…";
      if (startServerBtn) startServerBtn.classList.add("hidden");
    } else {
      statusText.textContent = "Offline — click to start";
      if (startServerBtn) startServerBtn.classList.remove("hidden");
    }
  }

  let userScrolledUp = false;

  messagesEl.addEventListener("scroll", function() {
    var threshold = 45;
    var distFromBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
    userScrolledUp = distFromBottom > threshold;
    if (scrollBottomBtn) {
      scrollBottomBtn.classList.toggle("hidden", !userScrolledUp);
    }
  });

  if (scrollBottomBtn) {
    scrollBottomBtn.addEventListener("click", function() {
      userScrolledUp = false;
      scrollToBottom(true);
      scrollBottomBtn.classList.add("hidden");
    });
  }

  function scrollToBottom(force) {
    if (!force && userScrolledUp) {
      return; // Smart Scroll Lock: preserve reading position
    }
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
    var html = text.replace(/\r\n/g, "\n").replace(/\n{3,}/g, "\n\n");

    // 1. Code blocks with Antigravity-style Toolbar (Language Tag + Copy + Insert at Cursor)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(_, lang, code) {
      var language = (lang || "code").toLowerCase();
      var cleanCode = code.trim();
      var enc = encodeURIComponent(cleanCode);

      return '<div class="code-block-wrapper">' +
        '<div class="code-header">' +
          '<span class="code-lang-tag">' + escapeHtml(language.toUpperCase()) + '</span>' +
          '<div class="code-actions">' +
            '<button class="code-action-btn copy-code-btn" type="button" data-code="' + enc + '" title="Copy code snippet">📋 Copy</button>' +
            '<button class="code-action-btn insert-code-btn" type="button" data-code="' + enc + '" title="Insert snippet at cursor in editor">📥 Insert</button>' +
          '</div>' +
        '</div>' +
        '<pre><code class="language-' + escapeHtml(language) + '">' +
          escapeHtml(cleanCode) +
        '</code></pre>' +
      '</div>';
    });

    // 2. GFM Tables Parser
    html = html.replace(/((?:\|[^\n]+\|\r?\n)+)/g, function(tableBlock) {
      var lines = tableBlock.trim().split("\n");
      if (lines.length < 2) return tableBlock;
      var headerLine = lines[0];
      var sepLine = lines[1];
      if (sepLine.indexOf("-") === -1) return tableBlock;

      var parseCells = function(row, tag) {
        var cells = row.split("|").slice(1, -1);
        return "<tr>" + cells.map(function(c) {
          return "<" + tag + ">" + escapeHtml(c.trim()) + "</" + tag + ">";
        }).join("") + "</tr>";
      };

      var thead = "<thead>" + parseCells(headerLine, "th") + "</thead>";
      var tbody = "<tbody>" + lines.slice(2).map(function(l) { return parseCells(l, "td"); }).join("") + "</tbody>";
      return '<div class="table-wrapper"><table class="markdown-table">' + thead + tbody + "</table></div>";
    });

    // 3. Inline formatting
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
