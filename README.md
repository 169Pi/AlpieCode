# 🤖 AlpieCode

> **Autonomous AI Software Engineering Agent** powered by 169Pi. Operates locally on your device (CPU/GPU) with zero internet, or connects to high-speed cloud VLM endpoints. Integrates seamlessly into **CLI**, **REST/SSE API**, and **VS Code IDE**.

```
    _    _     _      ____            _      
   / \  | |_ _| | ___ / ___|___   __| | ___ 
  / _ \ | | '_ \ |/ _ \ |   / _ \ / _` |/ _  / ___ \| | |_) | |  __/ |__| (_) | (_| |  __/
/_/   \_\_|_.__/|_|\___|\____\___/ \__,_|\___|
```

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com)
[![VS Code Extension](https://img.shields.io/badge/VS%20Code-Extension-blue.svg)](./vscode)

---

## ⚡ Quick Start

### 1. Installation
```bash
pip install --upgrade alpiecode
```
*Or install from source with uv:*
```bash
git clone https://github.com/169pi/codeagent-poc.git
cd codeagent-poc
uv venv && source .venv/bin/activate
uv pip install -e .
```

### 2. Run Autonomous Coding Tasks (CLI)
```bash
# Direct task execution
alpiecode run "Create a FastAPI REST API for a todo app with full test coverage"

# Dry-run planning (read-only)
alpiecode plan "Refactor database connection to async SQLModel"

# Multimodal UI generation from image / screenshot
alpiecode run "Build an HTML/CSS landing page matching this design" --image ./mockup.png
```

### 3. Launch Backend & VS Code Extension
```bash
alpiecode serve
```
*Starts the background API and automatically installs the AlpieCode VS Code Extension.*

---

## 🌟 Key Highlights

- 🌐 **Dual Online & Offline Modes**: High-speed cloud VLM (80-120 tok/s) when online, automatic fallback to local GGUF (`169Pi/Alpie_learn_prototype_GGUF_NEW`) on CPU/GPU when offline.
- 💭 **Thinking & Non-Thinking Modes**: Deep chain-of-thought reasoning for complex multi-file projects, or instant low-latency mode for rapid edits.
- 🖼️ **Multimodal Perception**: Analyze UI mockups, screenshots, video recordings (`--video`), YouTube links (`--url`), and GitHub repos (`--github`).
- ⚡ **VS Code Ghost-Text Autocomplete**: Real-time Fill-In-Middle inline suggestions. Press `Tab` to accept.
- 📝 **Native Side-by-Side Diff Previews**: Inspect `Original ↔ Modified` diffs with one-click `Accept` or `Reject` in VS Code before writing to disk.
- 🛡️ **Guardian Safety Gate**: Automatically classifies shell commands into `SAFE`, `WARNING`, and hard-blocks `DANGEROUS` operations (`rm -rf /`, `sudo`, `mkfs`).
- 🧠 **Cross-Session Memory & Plan Preservation**: Automatically remembers working build/test commands and project architecture across chat sessions.

---

## 📖 Complete Documentation

For the full detailed manual covering all 14 tools, CLI flags, REST API endpoints, vision extraction, and offline GGUF setup:

👉 **[Read the Full Documentation (DOCUMENTATION.md)](./DOCUMENTATION.md)**

---

## 🛠️ CLI Cheat Sheet

| Command | Description |
|:---|:---|
| `alpiecode run "<task>"` | Execute an autonomous software engineering task |
| `alpiecode chat` | Multi-turn interactive terminal REPL |
| `alpiecode plan "<task>"` | Generate a structured execution plan (read-only dry run) |
| `alpiecode diff` | Show git diff of all modifications made by AlpieCode |
| `alpiecode serve` | Start API server on `http://127.0.0.1:7169` & install VS Code plugin |
| `alpiecode init` | Guided setup wizard (pre-download offline GGUF model) |

### Important Flags
- `--image <path>` : Analyze screenshot/diagram for vision tasks
- `--video <path>` : Extract keyframes from video for debugging
- `--url <url>` : Analyze YouTube tutorial/bug report
- `--github <repo>` : Explore open-source repo (e.g. `facebook/react`)
- `--no-thinking` : Disable reasoning tokens for instant execution
- `--max-turns <n>` : Set maximum turn limit (default: `50`)
- `--workdir <dir>` : Set target workspace directory

---

## 📄 License
MIT License. Built by the **169Pi AI Research Team**.
