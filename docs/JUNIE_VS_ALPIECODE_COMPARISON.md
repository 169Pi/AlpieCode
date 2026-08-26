# 🏛️ Architecture Comparison: JetBrains Junie Local vs. AlpieCode CodeAgent

> **Deep Architectural Analysis & Comparative Evaluation**  
> Comparing **JetBrains Junie Local** (`https://junie.jetbrains.com/docs/junie-local.html`) with **AlpieCode Autonomous CodeAgent** (`v2.0.7`).

---

## 📑 Executive Summary

| Dimension | JetBrains Junie Local | AlpieCode CodeAgent |
| :--- | :--- | :--- |
| **Primary Focus** | Local macOS MLX inference server for JetBrains IDEs & Junie CLI | Full-stack autonomous AI coding platform (VS Code, CLI, Jupyter/Colab, SDK) |
| **Engine Architecture** | Pure Local MLX (`mlx-vlm`) on Apple Silicon | **Hybrid Dual-Engine** (Remote Azure VLM API + Local GGUF `llama-cpp` fallback) |
| **Hardware Barrier** | **High**: Apple Silicon Mac (M5+), **64 GB+ RAM**, macOS 26+ | **Low/Universal**: Runs on **8–16 GB RAM** (Linux, Windows, WSL, macOS, CUDA GPU/CPU) |
| **Model Stack** | Qwen3.6-27B-4bit + Qwen3.6-27B-MTP-4bit (Speculative Decoding) | 169Pi GRPO merged VLM (Cloud) & 169Pi GGUF Quantized (Local) |
| **Integration Surfaces** | Junie CLI, JetBrains IDEs (ACP protocol) | VS Code Extension, Terminal CLI, Jupyter Notebooks, Google Colab, Python SDK |
| **Agentic Tool Count** | Standard CLI tool suite (via ACP) | **15 Autonomous Tools** (file ops, bash, search, vision, web, git, memory, plan) |
| **Governance Flow** | Standard prompt-to-diff execution | **Plan-First Review Card** (`Accept` / `Reject` / `Edit Request`) |
| **Environment Management**| Manual developer setup | **Proactive Import Scanner & Automated `.venv` Setup** |

---

## 🏗️ 1. Inference Engine & Hardware Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                          JETBRAINS JUNIE LOCAL                                │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                         macOS Apple Silicon (M5+, 64GB+)
                                       │
                                       ▼
                       junie-mlx-vlm Background Server
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
    Qwen3.6-27B-MLX (Main)                            Qwen3.6-27B-MTP (Draft)
    [~15 GB 4-bit VLM]                                [Speculative Decoding ~250MB]
                                       │
                                       ▼
                        localhost:19239/v1/chat/completions
                                       │
                                       ▼
                          Junie CLI / JetBrains IDEs

═════════════════════════════════════════════════════════════════════════════════

┌───────────────────────────────────────────────────────────────────────────────┐
│                          ALPIECODE CODEAGENT                                  │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │
                    Any OS: Linux / Windows WSL / macOS
                          (Consumer 8GB–16GB+ RAM)
                                       │
                                       ▼
                    Agent Orchestrator Reachability Ping
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼ (Online)                                            ▼ (Offline)
    OpenAIBackend (Azure VM)                              LocalBackend (GGUF)
    169Pi GRPO VLM API                                    169Pi GGUF + llama-cpp
    (32k–131k context window)                             (CPU / CUDA GPU Offload)
                                       │
                                       ▼
                        AlpieCode Server (Port 7169)
                                       │
        ┌───────────────────┬──────────┴────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼
  VS Code Extension    Terminal CLI      Jupyter & Colab       Python SDK
  (Sidebar Chat UI)    (alpiecode run)   (%alpie Magics)       (import alpiecode)
```

### Junie Local Architectural Characteristics:
1. **Tied to Apple MLX**: Junie Local is built exclusively on `mlx-vlm`, Apple's proprietary framework for Apple Silicon unified memory. It cannot run on Linux servers, Windows workstations, or NVIDIA GPUs.
2. **High Hardware Floor**: Requires **64 GB RAM or more** on modern Apple Silicon (M5 or newer) and macOS 26+.
3. **Speculative Decoding Engine**: Integrates a 250 MB draft model (`Qwen3.6-27B-MTP-4bit`) alongside the main 27B model for multi-token prediction (MTP), improving local tokens/sec.
4. **Standalone Daemon (`serverctl.sh`)**: Managed by a shell script that handles `start`, `stop`, `status`, `health`, and `uninstall` on `localhost:19239`.

### AlpieCode Architectural Characteristics:
1. **Hybrid Dual-Engine with Automatic Fallback**: AlpieCode seamlessly blends **high-speed Cloud Inference** with **Offline GGUF Execution**:
   - Pings `http://20.245.200.125:8000/v1` (with a 0.4s fast check).
   - If online, utilizes high-throughput cloud VLM resources.
   - If offline or disconnected, automatically switches to `LocalBackend` with `llama-cpp-python` — no manual commands needed.
2. **Universal Accessibility**: Runs comfortably on consumer PCs, standard Linux VMs, Windows WSL2, and Mac laptops (8GB–16GB RAM) using quantized GGUF weights.
3. **Cross-Platform Process Management**: Packaged as a Python package (`uv`/`pip`) with built-in FastAPI ASGI server (`alpiecode serve` on port 7169).

---

## 🛠️ 2. Agentic Tooling & System Execution

| Capability | JetBrains Junie Local | AlpieCode CodeAgent |
| :--- | :--- | :--- |
| **Tool Execution Core** | ACP (Agent Client Protocol) IDE bridge | Internal `ToolExecutor` with 15 specialized tools |
| **File Editing** | Standard file diff application | Dual mode: direct write for new files, structured `edit_file` with whitespace matching for existing |
| **Execution Sandboxing** | Standard subprocess / IDE runner | Dedicated VS Code Task terminal + Cross-platform WSL shell router + output capture |
| **Auto-Fix Loop** | IDE diagnostics feedback | **Smart Guardrail Auto-Fix**: Automatically re-runs failing code with diagnostic capture (capped at 3 retries max) |
| **Vision / Multimodal** | Qwen VLM image ingestion | Native multimodal pipeline (`view_image`, clipboard paste, drag & drop, video URL analysis) |
| **Web & Research** | IDE context | `web_search`, `fetch_url`, `clone_repo` for live external documentation lookup |
| **Context Management** | Standard sliding window | `compact_context` (dynamic token summarization) + `extract_memories` (persistent project rules) |

---

## 💻 3. User Interface & Integration Surfaces

### JetBrains Junie:
- **Primary Interface**: Junie CLI terminal and JetBrains IDEs (IntelliJ IDEA, PyCharm, WebStorm).
- **Control Mechanism**: In-terminal commands (`/local`, `/model`).
- **Target Audience**: Developers strictly working within the JetBrains IDE ecosystem.

### AlpieCode:
- **VS Code Extension (v0.8.5)**:
  - **Slash Commands Autocomplete (`/`)**: Floating popup for `/plan`, `/explain`, `/doctor`, `/test`, `/diff`, `/clear` with full keyboard arrow navigation.
  - **Reasoning Effort Selector**: `⚖️ 169Pi Med (Default)`, `🧠 High`, `⚡ Low (Fast)` toggle pill.
  - **Change Plan Review Cards**: Visual inline diff with `Accept`, `Reject`, and interactive `Edit Request` textarea.
  - **Live Token Meter**: Real-time generation speed (`⚡ 42 tok/s · 📊 1,240 tokens`).
  - **Inline Ghost Completions**: Tab-to-accept autocomplete as you type in any code editor.
- **Full CLI Suite**: `alpiecode serve`, `alpiecode run`, `alpiecode chat`, `alpiecode plan`, `alpiecode explain`, `alpiecode doctor`, `alpiecode diff`, `alpiecode init`.
- **Jupyter Notebooks, JupyterLab & Google Colab**:
  - `%load_ext alpiecode`
  - `%alpie <task>` and `%%alpie <multiline>`
  - `%alpie_plan`, `%alpie_explain`, `%alpie_doctor`
- **Python SDK**: `import alpiecode; alpiecode.run("...")` for programmatic agent pipelines.

---

## 🐍 4. Dependency & Environment Governance

One of AlpieCode's biggest innovations over Junie Local is **Proactive Environment & Virtual Environment Management**:

```
                                  Generated Python Code
                                            │
                                            ▼
                           Proactive AST Import Scanner
                           (Excludes 100+ Python Stdlib)
                                            │
                             Module missing in workspace?
                                            │
                             ┌──────────────┴──────────────┐
                             ▼ (Yes)                       ▼ (No)
               Check for .venv in workspace          Execute in Sandbox
                             │
              ┌──────────────┴──────────────┐
              ▼ (.venv Exists)              ▼ (No .venv)
       Popup: "Install in .venv?"    Popup: "Create .venv & Install?"
              │                             │
              ▼                             ▼
   .venv/bin/pip install pkg      python3 -m venv .venv && pip install pkg
              │                             │
              └──────────────┬──────────────┘
                             ▼
              Auto Re-run Sandbox with .venv/bin/python3
```

- **Junie Local**: Relies on the user already having an active, configured virtual environment. If a dependency is missing, the command fails.
- **AlpieCode**: Scans imports *before execution*, identifies missing libraries (e.g. `numpy`, `pandas`), presents a 1-click dialog to initialize `.venv` and install the package, and immediately executes the script with the newly created virtual environment interpreter.

---

## 🛡️ 5. Safety, Guardrails & Enterprise Governance

| Security & Governance Feature | JetBrains Junie Local | AlpieCode CodeAgent |
| :--- | :--- | :--- |
| **Command Safety Gate** | IDE execution permission | `guardian.py` regex safety gate (blocks `rm -rf`, disk wipes, unsafe system alterations) |
| **Infinite Loop Protection** | Client timeout | Hard cap (`MAX_AUTO_FIX_RETRIES = 3`) to prevent recursive AI retry loops |
| **Cross-Platform UNC Routing** | macOS only (N/A) | `_wslShellExec` automatically handles Windows UNC paths (`\\wsl.localhost\...`) |
| **System Diagnostics** | `serverctl.sh status/health` | `alpiecode doctor` (checks Python, CUDA/GPU, compilers, network latency, extension status) |

---

## 📊 6. Comprehensive Architectural Matrix

| Metric | JetBrains Junie Local | AlpieCode CodeAgent |
| :--- | :--- | :--- |
| **Inference Framework** | Apple `mlx-vlm` | `llama-cpp-python` (Local) + vLLM / OpenAI API (Remote) |
| **Model Size** | 27 Billion parameters (Qwen3.6-27B) | 169Pi Model Family (Optimized for coding) |
| **Speculative Decoding** | Yes (MTP Draft Model ~250MB) | Planned / GRPO Reinforcement Learning weights |
| **Supported OS** | **macOS only** (Apple Silicon M5+) | **Universal** (Linux, Windows WSL, macOS, Colab) |
| **RAM Requirement** | **64 GB minimum** | **8 GB – 16 GB** (Quantized GGUF) |
| **Extension Support** | JetBrains IDEs only | VS Code, Cursor, VSCodium |
| **Notebook Support** | None | Full Jupyter Notebook, JupyterLab & Google Colab |
| **CLI Capabilities** | Interactive CLI | CLI with 8 subcommands (`run`, `chat`, `plan`, `doctor`, etc.) |
| **Change Review Flow** | Standard git diff | Interactive Change Plan Card with inline edit requests |
| **Auto-Fixing** | Manual re-prompt | Automated sandbox error capture & 3-retry repair loop |
| **Package Management**| Passive | Proactive AST scan + 1-click `.venv` auto-creation |

---

## 🎯 Key Takeaways & Recommendations

### What AlpieCode Does Better:
1. **Universal Accessibility**: AlpieCode is not locked to expensive 64GB Mac hardware; it runs on any developer's existing machine (Linux, Windows, WSL, macOS, Google Colab).
2. **Hybrid Dual-Engine Reliability**: You get the speed and power of cloud VLM models when online, with instant seamless fallback to local GGUF when offline.
3. **Multi-Surface Ecosystem**: Works in VS Code, Terminal CLI, Jupyter Notebooks, Google Colab, and Python scripts.
4. **Developer Control**: The Plan-First Change Card, Slash Commands, and Reasoning Selector give developers complete transparency over AI actions.
5. **Zero-Config Environments**: Proactive virtual environment creation and dependency auto-install remove friction for data science and web development.

### What AlpieCode Can Adopt from Junie Local:
1. **Speculative Decoding on Apple Silicon**: In future releases, we can explore integrating small draft models (MTP) with `llama.cpp` speculative decoding for even faster local GGUF tokens/sec on Mac and CUDA workstations.
