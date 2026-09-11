# ⚡ AlpieCode: Autonomous AI Software Engineering Agent & Full Developer Platform

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/alpiecode-v9.0.1-emerald.svg)](https://github.com/169Pi/codeagent-poc)
[![VS Code Extension](https://img.shields.io/badge/vscode%20extension-v8.0.8-blueviolet.svg)](https://marketplace.visualstudio.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Jupyter & Colab](https://img.shields.io/badge/Jupyter%20%7C%20Colab-Ready-f37726.svg)](https://colab.research.google.com/)
[![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20WSL2%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/169Pi/codeagent-poc)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Powered by 169Pi Alpie Vision-Language-Action Models (Local GGUF & Remote Cloud API)**  
> *An enterprise-grade, autonomous software engineering agent seamlessly integrated across the Command Line (CLI), VS Code Extension, FastAPI Backend Server, Python SDK, Jupyter Notebooks, and Google Colab.*

---

## 📑 Table of Contents
1. [🌟 Overview & Capabilities](#-overview--capabilities)
2. [🏗️ Core Architecture & Hybrid Dual-Engine](#️-core-architecture--hybrid-dual-engine)
3. [📦 Complete Installation Guide](#-complete-installation-guide)
4. [🚀 Backend API Server (`alpiecode serve`)](#-backend-api-server-alpiecode-serve)
5. [⌨️ Command-Line Interface (CLI) Full Reference](#️-command-line-interface-cli-full-reference)
6. [💻 VS Code Extension Deep-Dive](#-vs-code-extension-deep-dive)
7. [🐍 Python SDK Reference (Programmatic Usage)](#-python-sdk-reference-programmatic-usage)
8. [📓 Jupyter Notebooks, JupyterLab & Google Colab](#-jupyter-notebooks-jupyterlab--google-colab)
9. [🛠️ 15 Built-In Autonomous Agent Tools](#️-15-built-in-autonomous-agent-tools)
10. [🛡️ Safety Guardian, Git Checkpoints & Memory System](#️-safety-guardian-git-checkpoints--memory-system)
11. [⚙️ Configuration & Environment Variables](#️-configuration--environment-variables)
12. [❓ FAQ & Troubleshooting](#-faq--troubleshooting)

---

## 🌟 Overview & Capabilities

**AlpieCode** is an autonomous software engineering assistant that acts as a principal developer in your repository. Rather than simply generating isolated snippets, AlpieCode operates as a full-loop agent:
- **Discovers & Understands**: Recursively indexes codebases, reads files, and executes ripgrep regex searches.
- **Reasons & Plans**: Formulates implementation plans, manages checkpointed deliverables, and explains complex architectures.
- **Generates & Modifies**: Writes production code, applies surgical whitespace-accurate diff patches, and refactors existing components.
- **Executes & Self-Heals**: Executes commands in an isolated sandbox, automatically captures build/test errors, and iterates until tests pass.
- **Works Everywhere**: From the terminal and VS Code sidebar to automated Python scripts and interactive Google Colab notebooks.

### 🎯 Feature Matrix Across Interfaces
| Feature / Capability | CLI | VS Code Extension | Python SDK | Jupyter & Colab |
| :--- | :---: | :---: | :---: | :---: |
| **Autonomous Coding Loops (`run`)** | ✅ | ✅ | ✅ | ✅ |
| **Multi-Turn Interactive Chat** | ✅ | ✅ | ✅ | ✅ |
| **Architectural Planning (`plan`)** | ✅ | ✅ | ✅ | ✅ |
| **Deep Code Explanation (`explain`)** | ✅ | ✅ | ✅ | ✅ |
| **Interactive Diff / Plan-First Review** | — | ✅ (Accept/Reject/Edit) | — | — |
| **Inline Ghost-Text Code Autocomplete** | — | ✅ (Tab to accept) | — | — |
| **Live Token Speed & Counter Meter** | — | ✅ | — | ✅ |
| **Multimodal Vision (Images/Screenshots)** | ✅ (`--image`) | ✅ (Paste / Upload) | ✅ | ✅ |
| **Video & YouTube URL Analysis** | ✅ (`--video`, `--url`) | — | ✅ | — |
| **Autonomous GitHub Repo Analysis** | ✅ (`--github`) | ✅ | ✅ | — |
| **Proactive `.venv` & Dependency Setup** | ✅ | ✅ | ✅ | ✅ |
| **Persistent Project Memory** | ✅ | ✅ | ✅ | ✅ |
| **Zero-Crash Smart GGUF Fallback** | ✅ | ✅ | ✅ | ✅ |

---

## 🏗️ Core Architecture & Hybrid Dual-Engine

AlpieCode employs an intelligent **Hybrid Dual-Engine** routing system that pairs the speed and depth of cloud Vision-Language-Action models with the resilience of completely offline local GGUF models.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CLIENT LAYER                                       │
│   VS Code Extension        Terminal CLI          Python SDK       Jupyter / Colab      │
│   (Sidebar & Ghost-Text)  (alpiecode run/chat)  (import alpiecode)   (%alpie / %%alpie)│
└──────────────────────────┬───────────────────────┬──────────────────────┬──────────────┘
                           │                       │                      │
                           ▼                       ▼                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND SERVER (`alpiecode serve`)                      │
│   • POST /chat (SSE Stream)   • POST /completion (Inline Ghost)   • GET /sessions      │
│   • POST /cancel/{id}         • GET /health                       • GET /metrics       │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  AGENT ORCHESTRATOR                                    │
│   • 5-Layer Context Assembly (System + Summary + Anchors + Turns + Request)            │
│   • Rolling Compaction with Lazy-Cached Summaries                                      │
│   • Session State Isolation & Reentrancy Guards                                        │
│   • Persistent Cross-Session Memory (~/.alpiecode/memories/)                           │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               HYBRID DUAL-ENGINE ROUTER                                │
│                                                                                        │
│                   ┌──────────────────────────────────────────────┐                     │
│                   │        Active Internet Connectivity?         │                     │
│                   └──────────────┬────────────────┬──────────────┘                     │
│                                  │                │                                    │
│                            YES (Online)       NO (Offline)                             │
│                                  │                │                                    │
│                                  ▼                ▼                                    │
│                   ┌────────────────────────┐   ┌────────────────────────┐              │
│                   │      OpenAIBackend     │   │      LocalBackend      │              │
│                   │ (Remote 169Pi Cloud VLM│   │  (Local GGUF Engine)   │              │
│                   │   High-Throughput API) │   │  (Zero Internet Req.)  │              │
│                   └────────────────────────┘   └────────────────────────┘              │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             15 AUTONOMOUS AGENT TOOLS                                  │
│   write_file  •  edit_file  •  read_file  •  apply_patch  •  bash  •  list_files       │
│   file_search •  view_image •  fetch_url  •  web_search   •  clone_repo • update_plan  │
│   extract_memories • compact_context • diagnostics                                     │
│                                          │                                             │
│                                          ▼                                             │
│                           SAFETY GUARDIAN & SANDBOX GATE                               │
│              (Blocks destructive commands, enforces paths, sandbox execution)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### ⚡ Smart Fallback Resilience
- **Network-Aware Routing**: Local GGUF fallback triggers **only when internet is genuinely unavailable**, preventing unnecessary model loading on brief cloud API delays or transient server timeouts (which are retried automatically).
- **Sanitized Chat Templates**: Converts complex multi-turn OpenAI tool schemas and system structures into sanitized templates compatible with local Jinja2 GGUF renderers.
- **Zero Crashes**: If network drops mid-session, the agent gracefully recovers or provides clear diagnostic feedback.

---

## 📦 Complete Installation Guide

### 1. Prerequisites
- **Python**: `>= 3.9` (Recommended: Python 3.10, 3.11, or 3.12)
- **Platforms**:
  - **Linux**: Ubuntu 20.04+, Debian 11+, Fedora, Arch Linux
  - **Windows**: Native Windows 10/11 or Windows Subsystem for Linux (WSL2 / Ubuntu)
  - **macOS**: Apple Silicon (M1/M2/M3/M4) & Intel
- **Dev Tools (Recommended)**: `git`, `curl`, `ripgrep` (optional, falls back automatically)

---

### 2. Python Package Installation

#### Option A: Quick Install via pip (Any Virtual Environment)
Activate any virtual environment of your choice (`venv`, `conda`, `uv`, `virtualenv`, `poetry`) and install directly:
```bash
# 1. Activate your preferred virtual environment (e.g. venv)
python3 -m venv myenv
source myenv/bin/activate       # On Windows: myenv\Scripts\activate

# Or using Conda:
# conda create -n alpie python=3.11 -y && conda activate alpie

# 2. Install AlpieCode
pip install alpiecode
```

#### Option B: From Source / Editable Mode (Recommended for Developers)
```bash
# Clone the repository
git clone https://github.com/169Pi/codeagent-poc.git
cd codeagent-poc

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with all dependencies
pip install -e .
```

#### Option C: From Wheel (.whl)
```bash
# Build the distribution
python3 -m pip install --upgrade build
python3 -m build

# Install the wheel
pip install dist/alpiecode-9.0.1-py3-none-any.whl
```

#### Verify CLI Installation:
```bash
alpiecode version
# Output: alpiecode 9.0.1

alpiecode doctor
```

---

### 3. VS Code Extension Installation

The VS Code extension provides the AI sidebar, plan-first review, and inline ghost-text completions.

#### Automatic Installation (Zero Configuration)
Simply launch the AlpieCode backend server from your terminal:
```bash
alpiecode serve
```
If the VS Code extension is not already installed, AlpieCode **automatically packages and installs the `.vsix` into VS Code**!

#### Manual Installation via CLI:
```bash
# Using the pre-built VSIX file
code --install-extension vscode/alpiecode-8.0.8.vsix
```

#### Manual Packaging (For Extension Developers):
```bash
cd vscode
npm install
npm run compile
npx @vscode/vsce package
code --install-extension alpiecode-8.0.8.vsix
```

---

## 🚀 Backend API Server (`alpiecode serve`)

The AlpieCode FastAPI server runs as a high-concurrency daemon connecting local development environments, VS Code sidebars, remote IDEs, and external scripts to the autonomous agent engine.

### Launching the Server
```bash
# Default: binds to 127.0.0.1 on port 7169
alpiecode serve

# Custom Host and Port:
alpiecode serve --host 0.0.0.0 --port 8080
```

```text
    _    _     _      ____            _      
   / \  | |_ _| | ___ / ___|___   __| | ___ 
  / _ \ | | '_ \ |/ _ \ |   / _ \ / _` |/ _ \
 / ___ \| | |_) | |  __/ |__| (_) | (_| |  __/
/_/   \_\_|_.__/|_|\___|\____\___/ \__,_|\___|

✅ AlpieCode VS Code extension is installed.
🚀 Starting AlpieCode Server on http://127.0.0.1:7169
INFO:     Uvicorn running on http://127.0.0.1:7169 (Press CTRL+C to quit)
```

### REST & SSE API Endpoints Reference

| Method | Endpoint | Description | Payload / Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/chat` | Executes an agent task, streaming events in real time via **Server-Sent Events (SSE)**. | `{"task": str, "workdir": str, "session_id": Optional[str], "image": Optional[str], "reasoning_level": "thinking"\|"high"\|"low"}` |
| `POST` | `/completion` | Provides ultra-low-latency inline code completions (ghost text) ahead of cursor. | `{"prompt": str, "suffix": str, "language": str, "max_tokens": int}` |
| `GET` | `/health` | Health diagnostic check reporting server uptime, backend availability, and cache stats. | *None* |
| `GET` | `/sessions` | Lists active multi-turn sessions with token counts and workspace paths. | *None* |
| `DELETE`| `/sessions/{session_id}` | Deletes a session container and cleans up associated resources. | `session_id` in path |
| `POST` | `/cancel/{session_id}` | Gracefully cancels an in-progress agent task. | `session_id` in path |
| `GET` | `/metrics` | Returns token usage, speeds, and agent execution performance statistics. | *None* |

---

## ⌨️ Command-Line Interface (CLI) Full Reference

The `alpiecode` CLI provides a developer-friendly command suite:

```text
usage: alpiecode [-h] [-v] [--workdir WORKDIR] [--image IMAGE] [--video VIDEO]
                 [--url URL] [--github GITHUB] [--max-turns MAX_TURNS]
                 [--thinking] [--no-thinking] [--no-update] [--quiet] [--debug]
                 {version,init,serve,run,chat,plan,diff,undo,doctor,explain} ...
```

---

### 1. `alpiecode run "<task>"`
Executes an end-to-end autonomous software engineering task:
```bash
# Standard task in the current directory:
alpiecode run "Create a FastAPI app with SQLite auth and JWT tokens"

# Specify a target project directory:
alpiecode run "Fix all failing pytest tests" --workdir /path/to/project

# Multimodal image analysis (mockup to code, UI bug fix):
alpiecode run "Implement this dashboard layout in React and Tailwind" --image ./mockup.png

# Video walkthrough or screen recording analysis:
alpiecode run "Reproduce and fix the UI crash shown in this screen recording" --video ./bug_repro.mp4

# Analyze a YouTube tutorial or demonstration URL:
alpiecode run "Implement the architecture explained in this video" --url "https://youtube.com/watch?v=xyz"

# Analyze and clone an open-source GitHub repository:
alpiecode run "Analyze the plugin architecture of this repo and summarize it" --github "psf/requests"

# Force deep reasoning mode or fast execution mode:
alpiecode run "Audit the cryptographic security of auth.py" --thinking
alpiecode run "Add docstrings to all functions in utils.py" --no-thinking

# Show full agent discovery intelligence and tool arguments:
alpiecode run "Refactor database migrations" --debug
```

---

### 2. `alpiecode chat`
Starts a persistent, interactive terminal REPL with multi-turn memory:
```bash
alpiecode chat
```
*Features:*
- Retains context, variable names, and architectural decisions across turns.
- Rolling compaction prevents context window overflow.
- Checkpoints git state after each turn for easy rollback.
- Exit anytime by typing `exit`, `quit`, or pressing `Ctrl+C`.

---

### 3. `alpiecode plan "<task>"`
Generates an actionable architectural plan **without making file modifications**:
```bash
alpiecode plan "Migrate the frontend from JavaScript to TypeScript"
```
*Process:*
1. Explores existing files and types (`list_files`, `file_search`, `read_file`).
2. Synthesizes a structured checklist plan with milestones.
3. Outputs clear implementation steps and risk assessments.

---

### 4. `alpiecode explain "<target>"`
Deep-dives into a local file, function, or technical concept:
```bash
# Explain a local file:
alpiecode explain src/codeagent/orchestrator.py

# Explain a technical concept or codebase component:
alpiecode explain "How does the rolling context compaction work in AlpieCode?"
```

---

### 5. `alpiecode diff`
Inspects all file changes and diffs made by AlpieCode since the last git checkpoint:
```bash
alpiecode diff
```

---

### 6. `alpiecode undo`
Instantly rolls back all file edits made during the last AlpieCode session:
```bash
alpiecode undo
```

---

### 7. `alpiecode doctor`
Runs an instant system and environment diagnostic suite:
```bash
alpiecode doctor
```
*Health Checks:*
- **Python Runtime**: Python version and active virtual environment status.
- **Hardware Acceleration**: CUDA availability, GPU device name, and VRAM.
- **Network & Latency**: DNS resolution, ping latency (ms), and remote API reachability.
- **Compilers & Dev Tools**: Presence of `gcc`, `g++`, `git`, `node`, `java`, etc.
- **VS Code Extension**: Installation verification and version check.

---

### 8. `alpiecode init`
Interactive CLI wizard to configure endpoints, API keys, models, and defaults:
```bash
alpiecode init
```

---

## 💻 VS Code Extension Deep-Dive

The AlpieCode VS Code extension integrates directly into your daily IDE workflow.

```
┌────────────────────────────────────────────────────────┐
│  ALPIECODE CHAT                       ⚡ 48 tok/s · 1.4k│
├────────────────────────────────────────────────────────┤
│ 🤖 Mode: [Online Cloud VLM]    Reasoning: [High (Thinking)▼]
│                                                        │
│ 👤 Create a login endpoint with rate limiting.         │
│                                                        │
│ 🤖 ── Proposed Changes: auth.py ─────────────────────  │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 📋 Change Plan Card                                │ │
│ │ - from flask import Flask                          │ │
│ │ + from flask import Flask, request, jsonify        │ │
│ │ + from flask_limiter import Limiter                │ │
│ │                                                    │ │
│ │ [✅ Accept]      [❌ Reject]      [✏️ Edit Request]  │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ 📦 'flask_limiter' required but not installed.         │
│ [Create .venv & Install]   [Install Globally]  [Skip]  │
├────────────────────────────────────────────────────────┤
│ > Type /plan, /explain, /doctor, or ask a question...  │
│ [📎 Image] [📋 Plan-First: ON]             [Send ❯]    │
└────────────────────────────────────────────────────────┘
```

### 1. 📋 Plan-First Review & Change Approval Workflow
- When modifying existing files, AlpieCode presents an interactive **Change Plan Card** with side-by-side / unified diffs (`-` red / `+` green).
- **`✅ Accept`**: Commits the change, opens the file in your active editor, and runs verification.
- **`❌ Reject`**: Discards the modification cleanly.
- **`✏️ Edit Request`**: Opens an inline input box to provide steering instructions (e.g. *"Use Redis backend for rate limiting"*).

---

### 2. 🗂️ Persistent Multi-Turn Conversation History
- **Active Thread Context**: Each chat conversation maintains a persistent `sessionId`. The model retains all prior turns, files discussed, and tool results.
- **History Drawer**: Click the **History** button (`🕒`) in the sidebar header to view, reload, or delete up to **50 past conversations** saved in VS Code global storage.

---

### 3. 🧠 Reasoning Level Selector
Toggle model behavior directly in the sidebar dropdown:
- 🧠 **High (Thinking)**: Maximal chain-of-thought reasoning, multi-step problem solving, and complex architectural design.
- ⚡ **Low (Fast)**: Direct code generation with zero reasoning overhead for quick one-liners and docstring edits.

---

### 4. ⚡ Slash Commands (`/`)
Type **`/`** in the chat input to invoke quick commands:
- `📋 /plan <task>` — Creates a structured architectural plan without modifying code.
- `💡 /explain <file>` — Explains code, architecture, or algorithms step-by-step.
- `🩺 /doctor` — Executes full system diagnostic checks in the chat window.

---

### 5. 🖱️ Right-Click Context Menu Actions
Highlight any code in your editor, right-click, and choose:
- **Fix This Error**: Automatically aggregates language diagnostics (errors, warnings) and selected code to generate an instant fix.
- **Generate Tests**: Writes unit tests (pytest, jest, etc.) for the selected function or class.
- **Explain Code**: Explains the selected snippet line-by-line.
- **Refactor / Optimize**: Cleans, modernizes, and improves the performance of the highlighted block.
- **Ask About Selection**: Prompts for a custom question regarding the highlighted code.

---

### 6. 👻 Inline Ghost-Text Code Autocomplete
As you write code in any file, AlpieCode streams inline suggestions ahead of your cursor:
- Non-intrusive gray ghost-text suggestions.
- Press **`Tab`** to accept the suggestion, or keep typing to ignore.
- Intelligent debounce and circuit breakers ensure zero editor lag.

---

### 7. 🐍 Proactive Virtual Environment (`.venv`) Auto-Prompt
When generated code requires external libraries (`numpy`, `pandas`, `fastapi`, etc.):
- AlpieCode scans the AST imports before execution.
- If packages are missing, an interactive prompt appears:
  ```text
  📦 'fastapi' is required but not installed in your active environment.
  🐍 No virtual environment detected. Create one?

  [Create .venv & Install]   [Install Globally]   [Skip]
  ```
- Choosing **Create .venv & Install** automatically spins up `.venv`, installs the packages, and runs the script using `.venv/bin/python3`.

---

### 8. 📊 Live Token & Speed Meter
Displays real-time performance indicators in the sidebar header:
`🟢 Online API` ── `⚡ 46 tok/s · 📊 1,820 tokens`

---

### 9. 📎 Multimodal Image Attachment
- Drag-and-drop UI screenshots directly into the chat.
- Paste images directly from your clipboard (**`Ctrl+V`** / **`Cmd+V`**).
- Click **`📎 Image`** to browse and attach mockups, architecture diagrams, or error screenshots.

---

### 10. ⚙️ Extension Settings (`settings.json`)
Configure AlpieCode in your VS Code settings:
```json
{
  "alpiecode.serverUrl": "http://127.0.0.1:7169",
  "alpiecode.showReasoning": true,
  "alpiecode.enableAutocomplete": true,
  "alpiecode.autoRunCode": true,
  "alpiecode.autoFixErrors": true,
  "alpiecode.planFirstReview": true,
  "alpiecode.githubUsername": "my-github-handle",
  "alpiecode.confirmGitPush": true
}
```

---

## 🐍 Python SDK Reference (Programmatic Usage)

Automate engineering workflows directly in Python scripts and CI/CD pipelines:

```python
import alpiecode

# 1. Execute an autonomous engineering task
alpiecode.run(
    task="Build a benchmark script comparing Polars vs Pandas on 10M rows",
    workdir="./benchmarks",
    reasoning_level="thinking"  # "thinking" | "high" | "low"
)

# 2. Generate an implementation plan
alpiecode.plan(
    task="Refactor authentication layer to use OAuth2 and JWT tokens",
    workdir="."
)

# 3. Explain a file or architecture
alpiecode.explain(
    target="src/codeagent/orchestrator.py",
    workdir="."
)

# 4. Run system health diagnostics
status_code = alpiecode.doctor()
```

---

## 📓 Jupyter Notebooks, JupyterLab & Google Colab

AlpieCode delivers a first-class developer experience inside Jupyter Notebooks and Google Colab with reactive UI cards and live status badges.

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 AlpieCode Agent  [RUNNING]                              │
│ Task: Train an XGBoost model on iris dataset                │
│                                                             │
│ ✓ $ python -m pip install xgboost scikit-learn              │
│ ✓ write_file train.py                                       │
│ ✓ $ python train.py                                         │
│                                                             │
│ ✨ Code block automatically populated in next cell.        │
│ Hit Shift+Enter to run.                                     │
└─────────────────────────────────────────────────────────────┘
```

### 1. Setup in Colab or Jupyter
In any notebook cell:
```python
# Install AlpieCode (in Colab)
!pip install alpiecode

# Load the IPython magic extension
%load_ext alpiecode
```

---

### 2. Magic Commands

#### Single-Line Magic (`%alpie`)
```python
%alpie Create a function to calculate Fibonacci numbers using memoization
```

#### Multi-Line Cell Magic (`%%alpie`)
```python
%%alpie
Create an end-to-end data pipeline script data_pipeline.py:
1. Load dataset from https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv
2. Preprocess features with StandardScaler
3. Train an XGBoost classifier with 5-fold cross validation
4. Print the mean accuracy and confusion matrix
```

#### Auto-Insert Code into Next Cell (`--insert` / `--code`)
Use `--insert` to have AlpieCode **automatically populate the generated code into the very next notebook cell**, ready for you to press **`Shift+Enter`**:
```python
%alpie --insert Build a PyTorch neural network for MNIST digit classification
```

#### Specialized Notebook Magics:
```python
# Plan without modifying files
%alpie_plan Build a custom PyTorch dataset loader for audio spectrograms

# Explain code or notebook variables
%alpie_explain model.py

# System diagnostic check
%alpie_doctor

# Reset conversation context between notebook sections
%alpie_reset
```

---

## 🛠️ 15 Built-In Autonomous Agent Tools

The AlpieCode orchestrator autonomously selects and coordinates 15 specialized tools:

| # | Tool Name | Category | Description | Key Inputs |
| :-: | :--- | :--- | :--- | :--- |
| **1** | `write_file` | File System | Creates new files or completely overwrites existing files safely. | `path`, `content` |
| **2** | `edit_file` | File System | Replaces specific text blocks with surgical whitespace matching. | `path`, `old_str`, `new_str` |
| **3** | `read_file` | File System | Reads entire files or specific line ranges (`start_line`, `end_line`). | `path`, `start_line`, `end_line` |
| **4** | `apply_patch` | File System | Applies standard unified diff format patches. | `patch` |
| **5** | `bash` | Execution | Runs shell commands inside an isolated sandbox with safety gates. | `command`, `timeout` |
| **6** | `list_files` | Discovery | Recursively lists repository files with pattern matching & pruning. | `path`, `pattern`, `max_depth` |
| **7** | `file_search` | Discovery | High-speed ripgrep regex search across codebase contents. | `query`, `path`, `include` |
| **8** | `view_image` | Vision | Inspects and analyzes images, UI mockups, and screenshots. | `path` |
| **9** | `fetch_url` | Research | Fetches and extracts clean documentation and web pages. | `url` |
| **10**| `web_search` | Research | Queries DuckDuckGo for live API documentation and references. | `query`, `max_results` |
| **11**| `clone_repo` | Repository | Clones open-source repositories for local reference. | `repo_url`, `destination` |
| **12**| `update_plan` | Planning | Updates structured milestone checklists (`[x]` / `[ ]`). | `plan` |
| **13**| `extract_memories`| Memory | Extracts and persists project patterns and build commands. | `memories` |
| **14**| `compact_context` | Optimization| Compresses conversation history to prevent context overflow. | `summary` |
| **15**| `diagnostics` | Intelligence | Queries compiler and linter diagnostics for active files. | `path` |

---

## 🛡️ Safety Guardian, Git Checkpoints & Memory System

### 1. Safety Guardian Gate (`src/codeagent/guardian.py`)
- **Destructive Command Blocking**: Intercepts and blocks commands like `rm -rf /`, `mkfs`, raw disk partitioning, fork bombs, and system-level modifications.
- **Sandbox Boundary Enforcement**: Prohibits writes outside the active project root directory (`workdir`).
- **Rate-Limited Auto-Fix Loops**: Automatically stops recursive error-fixing loops after **3 attempts** to prevent token waste and infinite loops.

### 2. Git Checkpointing & Undo (`src/codeagent/git_ops.py`)
- **Automatic Checkpoints**: AlpieCode automatically creates temporary git checkpoints before executing tasks and after each multi-turn step.
- **One-Click Rollback**: Run `alpiecode undo` or reject a proposed plan in VS Code to restore your workspace to its exact prior state.

### 3. Persistent Cross-Session Memory (`src/codeagent/memory.py`)
- Automatically captures project architecture patterns, build scripts, test conventions, and known quirks.
- Persisted locally in `~/.alpiecode/memories/` and injected into future sessions so the agent never asks the same question twice.

### 4. Cross-Platform WSL2 Path Normalization
- Automatically translates Windows UNC paths (`\\wsl.localhost\...` and `\\wsl$\...`) to native Linux paths (`/home/...`) and routes commands through `wsl -d Ubuntu -- bash -c "..."` seamlessly.

---

## ⚙️ Configuration & Environment Variables

Configure AlpieCode globally via `alpiecode init` or by exporting environment variables:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OPENAI_API_BASE` | `https://test.169pi.ai/v1` | URL for the high-throughput 169Pi cloud VLM endpoint. |
| `OPENAI_API_KEY` | `EMPTY` | API authentication key (if required). |
| `ALPIECODE_MODEL` | `alpie_9b` | Target model name. |
| `ALPIECODE_SERVER_URL` | `http://127.0.0.1:7169` | Default URL for backend API server. |
| `ALPIECODE_N_CTX` | `262144` (Online) / `32768` (Offline) | Maximum context window size in tokens. |
| `ALPIECODE_TEMPERATURE` | `0.6` (Thinking) / `0.0` (Fast) | Model sampling temperature. |

---

## ❓ FAQ & Troubleshooting

#### Q: How does the agent decide when to use Local GGUF vs. the Online API?
> **A:** AlpieCode always prioritizes the high-throughput **Online Cloud API**. It only switches to the **Local GGUF Engine** if an internet check confirms the system is genuinely offline. Transient server delays or timeouts retry automatically rather than falling back.

#### Q: How do I reload the VS Code extension after updating the backend?
> **A:** In VS Code, press **`Ctrl+Shift+P`** (or **`Cmd+Shift+P`** on macOS) and select **`Developer: Reload Window`**.

#### Q: Port 7169 is already in use. How do I change the port?
> **A:** Start the server with a custom port:
> ```bash
> alpiecode serve --port 8080
> ```
> Then update the `alpiecode.serverUrl` setting in VS Code:
> ```json
> "alpiecode.serverUrl": "http://127.0.0.1:8080"
> ```

#### Q: Can I run AlpieCode completely offline on an airplane or air-gapped machine?
> **A:** Yes! AlpieCode includes full offline GGUF local model execution. Simply run any CLI command (`alpiecode run "..."`) or start the local server, and it will execute locally using CPU or CUDA hardware acceleration with zero internet access required.

---
