# 🤖 AlpieCode — Complete Documentation & User Manual

> **Autonomous AI Software Engineering Agent** powered by 169Pi. Operates locally on your device (CPU/GPU) with zero internet, or connects to high-speed cloud VLM endpoints. Integrates seamlessly into **CLI**, **REST/SSE API**, and **VS Code IDE**.

---

## 📑 Table of Contents

1. [Overview & Core Architecture](#1-overview--core-architecture)
2. [Installation & Requirements](#2-installation--requirements)
3. [Online Mode vs. Offline Mode](#3-online-mode-vs-offline-mode)
4. [Thinking Mode vs. Non-Thinking Mode](#4-thinking-mode-vs-non-thinking-mode)
5. [Multimodal & Vision Capabilities (Online)](#5-multimodal--vision-capabilities-online)
6. [CLI Reference — Every Command & Flag in Order](#6-cli-reference--every-command--flag-in-order)
7. [VS Code Extension Full Guide](#7-vs-code-extension-full-guide)
8. [Backend Server & REST/SSE API Reference](#8-backend-server--restsse-api-reference)
9. [Autonomous Toolset & Safety System](#9-autonomous-toolset--safety-system)
10. [Configuration & Environment Variables](#10-configuration--environment-variables)
11. [Troubleshooting & FAQ](#11-troubleshooting--faq)

---

## 1. Overview & Core Architecture

AlpieCode is an autonomous software engineering assistant that acts as a **staff engineer** on your machine. It doesn't just suggest snippets; it:
- Reads and explores your entire workspace (`list_files`, `file_search`, `read_file`).
- Plans multi-file architecture before writing code (`update_plan`).
- Executes shell commands to compile, run tests, and debug in an isolated environment (`bash`).
- Interactively previews diffs before committing (`diffHelper`).
- Provides real-time inline ghost-text autocompletions (`Tab` key).

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│   CLI (`alpiecode run`)    VS Code Extension    REST API    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / SSE / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                  Agent Orchestrator & Server                │
│   • Session Manager        • Context Compaction (32k ctx)   │
│   • Guardian Safety Gate   • Cross-Session Memory Store     │
│   • Smart Loop Detector    • Inline Autocomplete Provider   │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│      ONLINE BACKEND          │    │      OFFLINE BACKEND         │
│  Remote High-Speed Server    │    │  Local GGUF Model (169Pi)    │
│  (80–120 tok/s, Multimodal)  │    │  (CPU/GPU, 0% Internet req.) │
└──────────────────────────────┘    └──────────────────────────────┘
```

---

## 2. Installation & Requirements

### System Requirements
- **OS**: Linux, macOS, or Windows (WSL2 / Native Windows)
- **Python**: `3.9` or higher
- **Package Manager**: Works with `pip`, `uv`, or `pipx`

### Standard Installation
```bash
pip install --upgrade alpiecode
```

### Development Installation (from Source)
```bash
git clone https://github.com/169pi/codeagent-poc.git
cd codeagent-poc
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## 3. Online Mode vs. Offline Mode

AlpieCode operates in two distinct operational modes:

| Feature | 🌐 Online Mode | ✈️ Offline Mode |
|:---|:---|:---|
| **Primary Model** | `169Pi/grpo_phase_2_merged` | `169Pi/Alpie_learn_prototype_GGUF_NEW` |
| **Backend Engine** | Remote OpenAI-compatible VLM Server | Local `llama-cpp-python` (Vulkan/CUDA/Metal/CPU) |
| **Speed** | ⚡ 80–120 tokens/sec | 🐢 5–25 tokens/sec (hardware dependent) |
| **Internet Required** | Yes | **No (0% Internet required)** |
| **Data Privacy** | Encrypted transit to cloud endpoint | **100% On-Device (0 bytes leave machine)** |
| **RAM Footprint** | ~50 MB client memory | ~4–6 GB (Model weights in RAM/VRAM) |
| **Multimodal / Vision**| Full (Images, UI mockups, Videos, YouTube) | Text / GGUF code focus |
| **Fallback Behavior** | Auto-falls back to Offline if unreachable | Runs standalone without pinging network |

### How Routing Works:
1. When you trigger any task, AlpieCode performs a **sub-second connectivity probe** to the configured `base_url`.
2. If online and reachable, it routes requests through the **high-speed remote VLM server**.
3. If unreachable or offline, it routes requests directly through the **embedded local GGUF engine**.

---

## 4. Thinking Mode vs. Non-Thinking Mode

AlpieCode features an advanced dual-mode reasoning engine:

### 💭 Thinking Mode (Default: ON)
- **What it does**: The model executes deep chain-of-thought (CoT) reasoning before emitting tool calls or code. It breaks down architectural requirements, analyses edge cases, checks type invariants, and self-corrects potential bugs before editing disk.
- **When to use**: Multi-file projects, game development, debugging complex errors, algorithm design, refactoring, and large feature builds.
- **Display**:
  - In **CLI**: Displayed in styled reasoning blocks.
  - In **VS Code**: Expandable `💭 Thinking Process` disclosure box that streams live.

### ⚡ Non-Thinking Mode (`--no-thinking`)
- **What it does**: Bypasses chain-of-thought reasoning to directly emit tool calls and completions with zero initial latency.
- **When to use**: Quick edits, documentation lookups, typo fixes, code autocompletions, or resource-constrained environments.
- **How to toggle**:
  - **CLI**: Pass the `--no-thinking` or `--non-thinking` flag.
  - **VS Code**: Uncheck the `💭 Thinking` checkbox in the chat header, or set `"alpiecode.enableThinking": false` in Settings.

---

## 5. Multimodal & Vision Capabilities (Online)

In Online Mode, AlpieCode features native multimodal perception, allowing you to feed images, video files, YouTube walkthroughs, or remote GitHub repositories directly into the agent.

### 🖼️ 1. Image & UI Mockup Analysis (`--image`)
Feed mockups, architecture diagrams, screenshots of UI bugs, or sketches:
```bash
# Build frontend matching a screenshot
alpiecode run "Recreate this dashboard landing page using HTML and Vanilla CSS" --image ./mockup.png

# Debug an error from a screenshot
alpiecode run "Fix the visual glitch shown in this screenshot" --image ./bug_screenshot.jpg
```
*Supported image formats*: `.png`, `.jpg`, `.jpeg`, `.webp`, `.svg`, `.gif`.

### 🎬 2. Video Analysis (`--video`)
Feed screen recordings or video demonstrations of bugs or user workflows. AlpieCode automatically extracts keyframes using `ffmpeg`:
```bash
alpiecode run "Identify the UI reproduction steps in this recording and write a test case" --video ./repro_bug.mp4
```

### 📺 3. YouTube Video Analysis (`--url`)
Pass a YouTube URL directly. AlpieCode downloads the stream, extracts representative frames, and analyzes the video:
```bash
alpiecode run "Implement the game loop explained in this tutorial video" --url "https://www.youtube.com/watch?v=..."
```

### 🐙 4. GitHub Repository Ingestion (`--github`)
Analyze open-source repositories directly without manual cloning:
```bash
alpiecode run "Analyze issue #42 in this repo and suggest a fix" --github "facebook/react"
```

---

## 6. CLI Reference — Every Command & Flag in Order

### Syntax
```bash
alpiecode [GLOBAL_FLAGS] <COMMAND> [COMMAND_FLAGS] [ARGUMENTS]
```

### Global Commands

#### 1. `alpiecode run "<task>"`
Executes an autonomous software engineering task from natural language.
```bash
alpiecode run "Build a terminal-based Snake game in Python with curses"
```

#### 2. `alpiecode chat`
Starts an interactive terminal chat session with multi-turn conversational context.
```bash
alpiecode chat --workdir ./my-project
```

#### 3. `alpiecode plan "<task>"`
**Read-only dry-run mode.** Inspects the workspace, analyzes dependencies, and outputs a structured execution plan without making any modifications to files.
```bash
alpiecode plan "Refactor authentication system to JWT tokens"
```

#### 4. `alpiecode diff`
Shows all code changes AlpieCode has made since the start checkpoint using syntax-highlighted diffs.
```bash
alpiecode diff
```

#### 5. `alpiecode serve`
Launches the background FastAPI / SSE server powering the VS Code extension and external IDE integrations.
```bash
alpiecode serve --host 127.0.0.1 --port 7169
```
*Note*: If the VS Code extension is not installed, `alpiecode serve` automatically detects your VS Code installation and installs the extension.

#### 6. `alpiecode init`
Interactive onboarding wizard. Allows downloading the offline GGUF model in advance, configuring HuggingFace tokens, or customizing server endpoints.
```bash
alpiecode init
```

---

### Command Flags Reference

| Flag | Applicable To | Description | Default |
|:---|:---|:---|:---|
| `--workdir <PATH>` | `run`, `chat`, `plan`, `diff` | Target directory for the workspace | `.` (current dir) |
| `--image <PATH>` | `run`, `plan` | Path to an image file for vision analysis | `None` |
| `--video <PATH>` | `run`, `plan` | Path to a video file for frame extraction | `None` |
| `--url <URL>` | `run`, `plan` | YouTube URL for multimodal analysis | `None` |
| `--github <REPO>` | `run`, `plan` | GitHub repo shorthand (`owner/repo`) or URL | `None` |
| `--max-turns <INT>`| `run`, `chat` | Maximum autonomous turns before terminating | `50` |
| `--no-thinking` | `run`, `chat`, `plan` | Disable chain-of-thought reasoning tokens | `False` |
| `--host <IP>` | `serve` | IP address for the backend server | `127.0.0.1` |
| `--port <INT>` | `serve` | Port for the backend server | `7169` |
| `--no-update` | All commands | Disable automatic background update check | `False` |
| `--quiet` | All commands | Suppress turn-by-turn detailed terminal logs | `False` |

---

## 7. VS Code Extension Full Guide

The AlpieCode extension integrates the agent directly into your VS Code workflow.

### 1. Activating the Sidebar
1. Start the server in a terminal:
   ```bash
   alpiecode serve
   ```
2. Click the **AlpieCode icon** in the left Activity Bar sidebar.
3. The chat window will display connection status:
   - `🟢 Connected · Online API` (Cloud mode)
   - `🟢 Connected · Local GGUF` (Offline mode)

### 2. Ghost-Text Inline Autocomplete (Tab to Accept)
- As you write code in any file, AlpieCode provides sub-second inline suggestions.
- **Debounced at 300ms** to prevent typing interruption.
- **Cancellation-aware**: Instantly aborts pending generation when new keystrokes occur.
- Press **`Tab`** to accept the suggestion, or keep typing to dismiss.

### 3. Native Side-by-Side Diff Previews (Accept / Reject)
- Whenever AlpieCode modifies or writes a file, it opens a **Native VS Code Diff Tab** (`Original ↔ Modified`).
- A prompt banner appears in the bottom-right corner:
  ```
  AlpieCode wants to modify 'engine.cpp'. Accept proposed changes?
  [ ✅ Accept ]    [ ❌ Reject ]
  ```
- Clicking **`✅ Accept`** writes changes to disk.
- Clicking **`❌ Reject`** immediately discards the edit.

### 4. Right-Click Context Menu Actions
Highlight any snippet in your editor → Right-click:
- 🛠️ **AlpieCode: Fix This Error**: Resolves syntax/runtime bugs.
- 🧪 **AlpieCode: Generate Tests**: Creates unit tests for the selected code.
- 📖 **AlpieCode: Explain Code**: Breaks down complexity line-by-line.
- ⚡ **AlpieCode: Refactor / Optimize**: Cleans structure, improves time complexity.
- 💬 **AlpieCode: Ask About Selection**: Sends snippet directly to the chat sidebar.

---

## 8. Backend Server & REST/SSE API Reference

The server exposes an asynchronous FastAPI engine on `http://127.0.0.1:7169`.

### Endpoints

#### `POST /chat` — Stream Agent Task via SSE
Sends a task to the orchestrator and streams real-time Server-Sent Events.
```json
// Request Body
{
  "task": "Create a python CLI tool for weather",
  "workdir": "/path/to/project",
  "session_id": "optional-session-id",
  "image": "/path/to/mockup.png"
}
```
**SSE Event Stream**:
- `event: status` — Status messages (planning, executing tools).
- `event: thinking` — Streamed reasoning tokens.
- `event: content` — Streamed text output.
- `event: tool_start` — Tool execution started (`name`, `arguments`).
- `event: tool_end` — Tool execution completed (`name`, `result`).
- `event: done` — Task completed.

#### `POST /completion` — Fast FIM Autocomplete
High-speed Fill-In-Middle endpoint designed for editor ghost text.
```json
// Request Body
{
  "prefix": "def calculate_area(radius):\n    ",
  "suffix": "\n\nprint(calculate_area(5))",
  "language": "python",
  "file_path": "math_utils.py",
  "max_tokens": 128
}

// Response Body
{
  "completion": "import math\n    return math.pi * (radius ** 2)"
}
```

#### `GET /health` — Health Status & Diagnostics
```json
{
  "status": "online",
  "backend": "Online API (https://test.169pi.ai/v1)",
  "available": true,
  "uptime_seconds": 1240.5,
  "version": "0.9.8"
}
```

#### `GET /sessions` & `DELETE /sessions/{session_id}`
Manages active conversation sessions.

#### `POST /cancel/{session_id}`
Gracefully cancels an in-flight background task.

---

## 9. Autonomous Toolset & Safety System

AlpieCode has access to an isolated suite of 14 tools:

### File Management Tools
- `read_file(path, start_line, end_line)`: Reads files with numbered lines.
- `write_file(path, content)`: Creates or overwrites files.
- `edit_file(path, old_str, new_str)`: Performs precise substring replacements.
- `list_files(path, max_depth)`: Recursive directory tree listing.
- `file_search(pattern, path, include)`: Fast regex / text search across files.
- `apply_patch(path, patch)`: Applies unified diff patches.
- `view_image(path)`: Inspects local image metadata & dimensions.

### Execution & Shell Tools
- `bash(command)`: Executes shell commands in the project virtualenv.
  - **Smart Truncation**: Preserves both head (compiler errors) and tail (test summaries).
  - **Silent Success Guard**: Detects if a script ran with `exit_code=0` but produced no output.
  - **Loop Prevention**: Stops commands repeating identical executions >3 times.

### Safety Guardian Gate
All shell commands are automatically audited by the Guardian before execution:
- 🟢 **SAFE**: Read-only operations (`ls`, `cat`, `git status`, `pytest`, `cargo test`) → Executed automatically.
- 🟡 **WARNING**: Modifying commands (`rm`, `git commit`, `chmod`, `mv`) → Logged with warning.
- 🔴 **DANGEROUS**: Destructive commands (`rm -rf /`, `mkfs`, `sudo`, `dd`, `shutdown`) → **Hard-blocked** immediately.

### Web & Research Tools
- `web_search(query)`: Live web search for documentation and error codes.
- `fetch_url(url)`: Fetches raw text content from documentation URLs.
- `github_browse(owner, repo, path)`: Browses open-source trees without cloning.
- `github_issues(owner, repo, issue_number)`: Reads issues and PR conversations.
- `clone_repo(repo_url, branch)`: Shallow clones repositories for local analysis.

---

## 10. Configuration & Environment Variables

### Configuration File (`~/.alpiecode/config.json`)
```json
{
  "base_url": "https://test.169pi.ai/v1",
  "model": "169Pi/grpo_phase_2_merged",
  "model_repo": "169Pi/Alpie_learn_prototype_GGUF_NEW",
  "api_key": "not-needed",
  "hf_token": null,
  "max_turns": 50,
  "temperature": 0.2,
  "max_tokens": 32768,
  "enable_thinking": true,
  "n_ctx": 32768,
  "n_gpu_layers": null
}
```

### Environment Variables

| Variable | Description |
|:---|:---|
| `ALPIECODE_BASE_URL` | Override remote API endpoint URL |
| `ALPIECODE_MODEL` | Override remote model name |
| `ALPIECODE_MODEL_REPO` | Override HuggingFace repo for local GGUF model |
| `ALPIECODE_API_KEY` | Set API key if using authenticated endpoints |
| `HF_TOKEN` | HuggingFace user token for downloading models |
| `ALPIECODE_CPU=1` | Force CPU-only execution (disables GPU offload) |
| `ALPIECODE_GPU_LAYERS`| Specify exact number of layers to offload to GPU |

---

## 11. Troubleshooting & FAQ

### Q: Does AlpieCode send my code to third-party services like OpenAI?
**No.** AlpieCode only connects to your configured 169Pi endpoint or runs **100% locally on your own machine** in offline mode. No data is sent to external proprietary APIs.

### Q: How do I force AlpieCode to run offline even when I have Wi-Fi?
Run with the `--offline` flag or set the environment variable:
```bash
alpiecode run "Build a calculator" --offline
# or
export ALPIECODE_OFFLINE=1
```

### Q: Why did a command stop with "REPEATED TOOL CALL LOOP DETECTED"?
AlpieCode includes loop guards. If a command runs 3 times with identical parameters without making progress, the agent is forced to stop and report its findings rather than wasting compute.

### Q: How do I update AlpieCode to the latest version?
```bash
pip install --upgrade alpiecode
```

---

*AlpieCode is engineered with passion by the 169Pi AI Research Team.*
