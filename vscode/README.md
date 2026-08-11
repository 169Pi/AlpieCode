# AlpieCode — VS Code Extension

AI coding agent powered by **169Pi**. Chat with your codebase, fix bugs, generate tests, and refactor code — all from your editor.

## Features

- 💬 **Chat Sidebar** — Real-time streaming chat with your AI coding agent
- 🔧 **Code Actions** — Right-click to fix errors, generate tests, explain, or refactor code
- 📝 **Diff Preview** — Review AI-suggested file changes before applying
- 🎨 **Theme Integration** — Seamlessly matches your VS Code dark/light theme

## Quick Start

1. Start the AlpieCode server:
   ```bash
   alpiecode serve
   ```
2. Open the AlpieCode sidebar (click the icon in the activity bar)
3. Type a task and press **Ctrl+Enter** to send

## Right-Click Code Actions

Select code in your editor, then right-click to access:
- **Fix This Error** — Automatically fix diagnostics
- **Generate Tests** — Create unit tests for selected code
- **Explain Code** — Get a detailed explanation
- **Refactor / Optimize** — Improve code quality
- **Ask About Selection** — Ask any custom question

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `alpiecode.serverUrl` | `http://127.0.0.1:7169` | Backend server URL |
| `alpiecode.enableThinking` | `true` | Show reasoning traces |

## Requirements

- AlpieCode backend (`pip install alpiecode`)
- Running server (`alpiecode serve`)
