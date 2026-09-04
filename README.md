# ⚡ AlpieCode: The Autonomous AI Coding Agent & Full Developer Platform
> **Powered by 169Pi Alpie Vision-Language-Action Models (Local GGUF & Remote Cloud API)**  
> *Seamlessly integrated across VS Code, Command Line (CLI), Python SDK, Jupyter Notebooks, and Google Colab.*

---

## 📑 Table of Contents
1. [🌟 Executive Overview](#-executive-overview)
2. [🏗️ Core Architecture & Hybrid Dual-Engine](#️-core-architecture--hybrid-dual-engine)
3. [📦 Installation & Getting Started](#-installation--getting-started)
4. [💻 VS Code Extension Deep-Dive](#-vs-code-extension-deep-dive)
5. [⌨️ Command-Line Interface (CLI) Guide](#️-command-line-interface-cli-guide)
6. [📓 Jupyter Notebooks, JupyterLab & Google Colab](#-jupyter-notebooks-jupyterlab--google-colab)
7. [🛠️ 15 Built-In Agentic Tools](#️-15-built-in-agentic-tools)
8. [🛡️ Safety Guardian, Virtual Environment & Guardrails](#️-safety-guardian-virtual-environment--guardrails)
9. [❓ FAQ & Troubleshooting](#-faq--troubleshooting)

---

## 🌟 Executive Overview

**AlpieCode** is a full-stack, state-of-the-art autonomous software engineering agent designed to reason, plan, write, test, debug, and explain code across multiple environments.

### 🎯 Key Capabilities at a Glance
| Environment | Key Features |
| :--- | :--- |
| **VS Code Extension** | Plan-First Review Cards, Slash Commands (`/`), Reasoning Selector (`High/Med/Low`), Proactive `.venv` Auto-Prompt, Live Token/Speed Meter, Multimodal Screenshot Attachment, Inline Ghost Text (`Tab` to complete), Sandbox Output Cards |
| **Terminal CLI** | `alpiecode serve`, `alpiecode run`, `alpiecode chat`, `alpiecode plan`, `alpiecode explain`, `alpiecode doctor`, `alpiecode diff`, `alpiecode init` |
| **Notebooks & Colab** | `%load_ext alpiecode`, `%alpie <task>`, `%%alpie <multiline>`, `%alpie_plan`, `%alpie_explain`, `%alpie_doctor` |
| **Python SDK** | `import alpiecode; alpiecode.run("...")`, `alpiecode.plan()`, `alpiecode.explain()`, `alpiecode.doctor()` |

---

## 🏗️ Core Architecture & Hybrid Dual-Engine

AlpieCode features an intelligent **Hybrid Dual-Engine** routing architecture:

```
                          ┌───────────────────────────┐
                          │    User Prompt / Task     │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │ Server Reachability Ping  │
                          └──────┬─────────────┬──────┘
                                 │             │
                    Online (Port 8000 Up)   Offline (No Connection)
                                 │             │
                                 ▼             ▼
                    ┌─────────────────┐   ┌──────────────────────┐
                    │ OpenAIBackend   │   │ LocalBackend         │
                    │ (Azure VLM API) │   │ (Local GGUF Engine)  │
                    │ 169Pi Remote    │   │ 169Pi Offline Model  │
                    └────────┬────────┘   └──────────┬───────────┘
                             │                       │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │  Agent Orchestrator   │
                             │  • Context Compaction │
                             │  • Tool Executor      │
                             │  • Memory Extraction  │
                             └───────────┬───────────┘
                                         ▼
                       SSE Stream Events / Terminal Output
```

1. **Online Cloud VLM API** (`OpenAIBackend`): When connected to the network, queries the high-throughput 169Pi model hosted on cloud infrastructure.
2. **Local GGUF Offline Engine** (`LocalBackend`): If internet is lost or the remote server is offline, AlpieCode **automatically falls back to local GGUF weights** (`169Pi/Alpie_learn_prototype_GGUF_NEW`) using CPU/GPU CUDA acceleration — zero crashes.

---

## 📦 Installation & Getting Started

### 1. Requirements
- **Python**: `>= 3.9` (Recommended: Python 3.10 – 3.12)
- **Platforms**: Linux (Ubuntu/Debian), Windows (Native & WSL2), macOS (Apple Silicon & Intel)
- **Editor (Optional)**: VS Code / Cursor / VSCodium (for extension support)

### 2. Python Package Installation
```bash
# Option A: Install from local repository (Editable Mode)
git clone https://github.com/169Pi/codeagent-poc.git
cd codeagent-poc
pip install -e .

# Option B: Install via pre-built Wheel
pip install alpiecode-2.0.7-py3-none-any.whl
```

### 3. Launching the AlpieCode API Server
The API server coordinates between the agent engine and the VS Code extension / SDK:
```bash
alpiecode serve
```
*Output:*
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

---

## 💻 VS Code Extension Deep-Dive

The AlpieCode VS Code extension provides an IDE sidebar pairing modern AI interaction patterns with developer control:

### 1. ⚡ Slash Commands Autocomplete (`/`)
Type **`/`** in the chat input area to trigger a floating command palette:
- `📋 /plan <task>` — Generate an architectural plan without making destructive file edits.
- `💡 /explain <file>` — Explain a file, function, or concept step-by-step.
- `🩺 /doctor` — Run full system diagnostic health checks in the chat.
- `🧪 /test` — Automatically generate unit tests and execute verification.
- `🔍 /diff` — Inspect recent changes made by AlpieCode in this session.
- `🗑️ /clear` — Reset and start a fresh chat session.

### 2. 🧠 169Pi Reasoning Effort Dropdown Selector (`⌃`)
Situated directly in the bottom options bar:
- ⚖️ **Medium (Default)**: Balanced reasoning depth and generation speed (`temperature: 0.1`).
- 🧠 **High**: Deep chain-of-thought step-by-step reasoning, full context, maximal accuracy (`temperature: 0.2`).
- ⚡ **Low (Fast)**: Direct code generation without reasoning traces (`temperature: 0.0`) for quick edits and one-liners.

### 3. 📋 Plan-First Review & Change Approval Workflow
- **New Files**: Written directly to disk, opened in the editor, and auto-executed in the sandbox.
- **Modifying Existing Files**: Displays an interactive **Change Plan Card** in chat with an inline line-by-line diff preview (`-` red / `+` green):
  - **`✅ Accept`**: Applies the change, opens the file, and runs verification.
  - **`❌ Reject`**: Discards the proposed modification cleanly.
  - **`✏️ Edit Request`**: Opens an inline input box to type custom instructions (e.g., *"Use an iterative approach instead of recursion"*).

### 4. 🐍 Proactive Virtual Environment (`.venv`) Auto-Detection
When generated Python code imports external packages (`numpy`, `pandas`, `flask`, etc.):
- AlpieCode scans the AST imports before execution.
- If the package is not installed, it pops up:
  ```text
  📦 'numpy' is required by matrix_multiplication.py but not installed.
  🐍 No virtual environment found. Create one?

  [Create .venv & Install]   [Install Globally]   [Skip]
  ```
- Selecting **Create .venv & Install** creates `.venv`, installs the package, and executes the script using `.venv/bin/python3`!

### 5. 📊 Live Token & Speed Meter
Top-right header displays real-time generation speed and token accumulation:
`🟢 Online API` ── `⚡ 42 tok/s · 📊 1,240 tokens`

### 6. 📎 Multimodal Image Attachment
Drag-and-drop screenshots, paste from clipboard (`Ctrl+V`), or click **`📎 Image`** to send mockups, diagrams, and error screenshots to the VLM.

### 7. 👻 Inline Ghost Text Code Completions
As you type in any code editor, AlpieCode streams gray inline suggestions ahead of your cursor (press **`Tab`** to accept).

---

## ⌨️ Command-Line Interface (CLI) Guide

AlpieCode offers a complete suite of standalone terminal commands:

### `alpiecode run "<task>"`
Runs an autonomous coding task in the current repository:
```bash
alpiecode run "Create a FastAPI service with SQLite database and CRUD endpoints"
```

### `alpiecode chat`
Starts an interactive terminal chat REPL with multi-turn conversation memory:
```bash
alpiecode chat
```

### `alpiecode plan "<task>"`
Generates a structured implementation plan without making any file edits:
```bash
alpiecode plan "Refactor authentication layer to use OAuth2 and JWT tokens"
```

### `alpiecode explain "<target>"`
Explains any file, class, function, or concept:
```bash
# Explain a local file:
alpiecode explain src/codeagent/orchestrator.py

# Explain a concept:
alpiecode explain "How does the tool calling loop work in AlpieCode?"
```

### `alpiecode doctor`
Runs an instant system health and environment diagnostic:
```bash
alpiecode doctor
```
*Checks:*
- Python version & Virtual Environment status
- CUDA / GPU hardware acceleration
- General Internet connectivity (8.8.8.8) & Remote VLM latency (ms)
- Compilers & runtimes (`gcc`, `g++`, `git`, `node`, `java`, etc.)
- VS Code extension installation status

### `alpiecode diff`
Shows all code modifications made by AlpieCode since the last git checkpoint:
```bash
alpiecode diff
```

### `alpiecode init`
Interactively configures custom model endpoints, API keys, and context parameters:
```bash
alpiecode init
```

---

## 📓 Jupyter Notebooks, JupyterLab & Google Colab

### 1. 🪄 IPython Magic Commands

Load AlpieCode in any Jupyter / Colab cell:
```python
%load_ext alpiecode
```

#### Line Magic (`%alpie`)
```python
%alpie create a python function to compute moving averages on a pandas Series
```

#### Cell Magic (`%%alpie`)
```python
%%alpie
Create a script train_model.py that:
1. Loads dataset from data.csv
2. Preprocesses numerical and categorical columns with ColumnTransformer
3. Trains an XGBoost classifier and evaluates with ROC-AUC score
4. Saves the model with joblib
```

#### Specialized Notebook Magics:
```python
%alpie_plan Build a custom PyTorch dataset loader for audio spectrograms
%alpie_explain model.py
%alpie_doctor
```

---

### 2. 🐍 Python SDK API (Programmatic Usage)

```python
import alpiecode

# 1. Execute task
alpiecode.run("Create a benchmark script comparing numpy vs cupy matrix multiplication")

# 2. Plan a project
alpiecode.plan("Implement a Redis caching layer for API responses")

# 3. Explain code
alpiecode.explain("src/codeagent/tools.py")

# 4. System health check
alpiecode.doctor()
```

---

### 3. ☁️ Google Colab Setup Guide

In Google Colab:
```python
# Cell 1: Install AlpieCode wheel
!pip install alpiecode

# Cell 2: Load Extension
%load_ext alpiecode

# Cell 3: Execute Task
%alpie build a random forest regressor on housing data and display metrics
```

---

## 🛠️ 15 Built-In Agentic Tools

The AlpieCode agent autonomously orchestrates **15 specialized tools**:

| Tool Name | Category | Purpose |
| :--- | :--- | :--- |
| `write_file` | File System | Creates new files or overwrites existing files safely |
| `edit_file` | File System | Precise replacement of target text blocks with exact whitespace matching |
| `read_file` | File System | Reads complete files or specific line ranges (`start_line`, `end_line`) |
| `apply_patch` | File System | Applies standard unified diff format patches |
| `bash` | System Execution | Runs shell commands with environment isolation & guardian safety gate |
| `list_files` | Workspace Discovery | Recursive directory listing with pattern filtering |
| `file_search` | Workspace Discovery | Ripgrep regex search across the entire codebase |
| `view_image` | Multimodal Vision | Inspects and analyzes image files and UI screenshots |
| `fetch_url` | Web & Research | Fetches live documentation and web pages |
| `web_search` | Web & Research | Searches technical references and API docs online |
| `clone_repo` | Repository | Clones public git repositories into workspace for reference |
| `update_plan` | Agent Planning | Updates structured implementation plan checkpoints (`[x]` / `[ ]`) |
| `extract_memories` | Memory | Saves long-term user preferences and project patterns |
| `compact_context` | Optimization | Compresses multi-turn conversation context to prevent token overflows |
| `diagnostics` | Code Intelligence | Inspects compiler and linter diagnostics |

---

## 🛡️ Safety Guardian, Virtual Environment & Guardrails

1. **Safety Guardian Gate** (`src/codeagent/guardian.py`):
   - Blocks destructive shell commands (e.g. `rm -rf /`, `mkfs`, raw disk writes).
   - Enforces execution inside the designated project root directory (`workdir`).
2. **Auto-Fix Loop Rate Limiting**:
   - Caps automated error retry loops at **3 attempts max** to prevent infinite error-fix cycles.
   - Prompts the user with actionable diagnostics if errors persist.
3. **Cross-Platform WSL & Shell Normalization**:
   - Automatically detects Windows UNC paths (`\\wsl.localhost\...` / `\\wsl$\...`) and routes commands through `wsl -e bash -c`.
   - Native execution on PowerShell, macOS (zsh), and Linux (bash).
4. **Context Window Compaction**:
   - Compresses long multi-turn sessions into concise summaries when context approaches token limits.

---

## ❓ FAQ & Troubleshooting

#### Q: The extension shows "Local GGUF" even though I am connected to the internet. Why?
> **A:** AlpieCode checks reachability of the specific remote model API (`https://test.169pi.ai/v1`). If the remote endpoint is unreachable, it automatically switches to **Local GGUF** so you can continue coding without interruption. Run `alpiecode doctor` to verify.

#### Q: How do I test the extension after updates?
> **A:** In VS Code, press **`Ctrl+Shift+P`** → select **`Developer: Reload Window`**.

#### Q: Can I use AlpieCode offline without internet?
> **A:** Yes! AlpieCode includes full offline GGUF inference (`169Pi/Alpie_learn_prototype_GGUF_NEW`) with local tool execution.

---

*Generated by AlpieCode AI Platform — Version 2.0.7 / Extension v0.8.5*
