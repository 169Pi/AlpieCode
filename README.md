# codeagent

Minimal installable coding-agent CLI backed by an OpenAI-compatible endpoint
(vLLM, or anything that speaks the `/v1/chat/completions` tool-calling protocol).

## Quick Start

```bash
git clone <repo-url>
cd codeagent-poc
pip install .
```

That's it — the defaults point to the team's VLM endpoint, so you can start
using it immediately:

```bash
cd your-repo
codeagent run "fix the failing test in tests/test_foo.py"
```

## Install

```bash
# Option 1: pip install (recommended)
pip install .

# Option 2: just install dependencies
pip install -r requirements.txt

# Option 3: isolated environment
pipx install .
```

This registers a `codeagent` command on your PATH.

## Configure (Optional)

The defaults work out of the box with the team's VLM endpoint. If you need
to point to a different server:

```bash
codeagent init
```

Prompts for:
- **base_url** — your vLLM server's OpenAI-compatible URL
- **model** — the served model name
- **api_key** — leave blank if your endpoint doesn't require auth

This writes `~/.codeagent/config.json`. You can also set environment variables:

```bash
export CODEAGENT_BASE_URL=http://your-host:8000/v1
export CODEAGENT_MODEL=your-model
export CODEAGENT_API_KEY=  # optional
```

## Usage

### One-Shot Task

```bash
cd your-repo
codeagent run "add logging to the main function"
```

### Interactive Chat

```bash
cd your-repo
codeagent chat
```

Type your requests interactively. The agent maintains context across messages.
Type `exit` or `quit` to stop.

### Options

```bash
codeagent run "task" --workdir /path/to/repo  # operate on a different directory
codeagent run "task" --max-turns 50           # increase max turns
codeagent run "task" --quiet                  # suppress per-turn output
```

## How It Works

The agent will:
1. `git init` the working directory if it isn't already a repo
2. Read/edit files and run shell commands via tool calls
3. Commit a checkpoint after every turn (`git log` to see the trail —
   `git reset --hard <sha>` to rollback)
4. Stop when the model returns a message starting with `DONE:`

### Available Tools

| Tool | Description |
|------|-------------|
| `bash` | Run any shell command |
| `read_file` | Read a file (with optional line range) |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace an exact string in a file |
| `list_files` | List files in the repo tree |

## Project Structure

```
codeagent-poc/
├── pyproject.toml          # Package metadata & dependencies
├── requirements.txt        # For pip install -r
├── README.md
└── src/
    └── codeagent/
        ├── __init__.py
        ├── config.py       # Config loading (file/env/defaults)
        ├── tools.py        # Tool definitions & implementations
        ├── agent.py        # Core agent loop & chat mode
        └── cli.py          # CLI entry point
```

## Requirements on the Model-Serving Side

Your vLLM server needs tool-calling enabled:

```bash
vllm serve <your-model> \
  --tool-call-parser hermes \
  --enable-auto-tool-choice
```

## Known Limitations

- `bash` runs unsandboxed shell commands — fine for a personal repo, not safe
  for untrusted tasks. Wrap in a container for multi-tenant use.
- No context compaction — long sessions will eventually hit the model's
  context window.
- Checkpoints are commits but there's no built-in `codeagent rollback`
  command yet — use `git log --oneline` and `git reset --hard` manually.
