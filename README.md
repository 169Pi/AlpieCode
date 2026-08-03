# AlpieCode

Autonomous AI Coding Agent CLI backed by 169Pi Alpie VLM / OpenAI-compatible endpoint
(speaks the `/v1/chat/completions` tool-calling protocol).

```
    _    _     _      ____            _      
   / \  | |_ _| | ___ / ___|___   __| | ___ 
  / _ \ | | '_ \ |/ _ \ |   / _ \ / _` |/ _ \
 / ___ \| | |_) | |  __/ |__| (_) | (_| |  __/
/_/   \_\_|_.__/|_|\___|\____\___/ \__,_|\___|
```

## Quick Start

```bash
git clone <repo-url>
cd codeagent-poc
uv venv && source .venv/bin/activate
uv pip install -e .
```

The defaults point directly to the team's Alpie VLM endpoint (`http://20.245.200.125:8000/v1` with model `169Pi/grpo_phase_2_merged`), so you can start using it immediately:

```bash
cd your-repo
alpiecode "explain what this project does"
# or
alpiecode run "fix the failing test in tests/test_foo.py"
```

## Usage

### 1. Direct Task Execution
```bash
alpiecode "create a python script to calculate fibonacci numbers and add unit tests"
```

### 2. Explicit Run Subcommand
```bash
alpiecode run "refactor database connection in main.py" --max-turns 30
```

### 3. Interactive Chat Mode
```bash
alpiecode chat
```
Maintains context across multiple prompts in an interactive REPL session. Type `exit` or `quit` to stop.

### 4. Configuration (Optional)
```bash
alpiecode init
```
Configures custom endpoint settings saved to `~/.alpiecode/config.json`. Or set env vars:
```bash
export ALPIECODE_BASE_URL=http://your-host:8000/v1
export ALPIECODE_MODEL=169Pi/grpo_phase_2_merged
```

## Built-in Tool Support
AlpieCode comes equipped with native tool calling:
- **`list_files`**: Inspect repository directory structure.
- **`read_file`**: Read file contents with line range filtering.
- **`write_file`**: Create new files or overwrite existing ones.
- **`edit_file`**: Make exact, targeted line string replacements.
- **`bash`**: Execute shell commands/tests in the repository directory.

## Automatic Checkpoints
AlpieCode automatically initializes `git` if not already present and creates a commit checkpoint after every turn.
If you ever need to rollback:
```bash
git log --oneline
git reset --hard <checkpoint-sha>
```
