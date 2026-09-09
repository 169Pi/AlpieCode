# Walkthrough: Phase 1 Codebase Stability & Crash Fixes

Phase 1 of the stability roadmap addresses critical crash vectors, cross-session leaks, thread safety hazards, and dead code accumulation across the AlpieCode runtime.

---

## Changes Made

### 1. BUG-04 & BUG-06: Orchestrator Thread Safety & State Isolation
**File**: [`src/codeagent/orchestrator.py`](file:///home/singh/Projects/codeagent-poc/src/codeagent/orchestrator.py)
* **Local Verification Gate**: Converted `_verification_nudge` from an instance attribute (`self._verification_nudge`) to a task-local variable (`verification_nudged = False`). In the server, sharing an orchestrator across requests previously meant that after one task triggered the nudge, all subsequent tasks across all sessions had verification permanently suppressed.
* **Task-Local Backend & Fallback**: Replaced mutating `self.backend` during dynamic reachability checks and local fallback with a local `task_backend` reference. When online inference fails, `task_backend = LocalBackend(cfg)` handles fallback locally within that task without mutating the shared orchestrator instance, preventing data races in concurrent multi-user server environments.
* **Stream Exception Guard**: Added a defensive guard `if resp is None: yield AgentEvent("error", ...) return` before accessing `resp.reasoning` to prevent uncaught `AttributeError` if a stream terminates unexpectedly without emitting a `done` event.

### 2. BUG-01: Removed Dead Sequential Code in Executor
**File**: [`src/codeagent/executor.py`](file:///home/singh/Projects/codeagent-poc/src/codeagent/executor.py)
* Removed ~80 lines of unreachable sequential fallback code that was left behind after the staged DAG parallel execution engine was introduced.
* The method now cleanly terminates with `return [results_map[tc.id] for tc in tool_calls if tc.id in results_map]`.

### 3. BUG-02: Eliminated Duplicate Handlers in CLI
**File**: [`src/codeagent/cli.py`](file:///home/singh/Projects/codeagent-poc/src/codeagent/cli.py)
* Removed the duplicate `doctor` handler block (previously duplicated at lines 142 and 222).
* Removed the duplicate, dead `diff` handler block (previously duplicated at lines 212 and 257). The CLI now exclusively dispatches to the modernized `git_ops.show_diff()` implementation.

### 4. BUG-09: Aligned Bash Timeout Error Message
**File**: [`src/codeagent/tools.py`](file:///home/singh/Projects/codeagent-poc/src/codeagent/tools.py)
* Changed the `subprocess.TimeoutExpired` error message in `_bash` from `"Command timed out after 300s"` to `"Command timed out after 120s"`, accurately matching the actual `timeout=120` passed to `subprocess.run`.

### 5. BUG-11: Added Tool-Call Pairing Guard in Compaction
**File**: [`src/codeagent/compaction.py`](file:///home/singh/Projects/codeagent-poc/src/codeagent/compaction.py)
* Added a pairing integrity check in `compact_messages()`:
  ```python
  min_cutoff = 1 if system else 0
  while cutoff > min_cutoff and messages[cutoff].get("role") == "tool":
      cutoff -= 1
  ```
  If `cutoff = len(messages) - KEEP_RECENT_TURNS` lands on a `tool` message, it now steps backwards so that `recent_messages` never begins with an orphan `tool` message severed from its parent `assistant` message, preventing OpenAI API `400 Invalid parameter` errors.

---

## Verification & Test Results

### Automated Unit Test Suite (`test/test_phase1.py`)

Created a comprehensive test suite in [`test/test_phase1.py`](file:///home/singh/Projects/codeagent-poc/test/test_phase1.py) covering each bug fix:

```bash
PYTHONPATH=src .venv/bin/pytest -v test/test_phase1.py
```

```
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/singh/Projects/codeagent-poc
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 8 items

test/test_phase1.py::test_bug01_executor_dead_code_removed PASSED        [ 12%]
test/test_phase1.py::test_bug01_executor_execution PASSED                [ 25%]
test/test_phase1.py::test_bug02_cli_no_duplicate_handlers PASSED         [ 37%]
test/test_phase1.py::test_bug04_and_06_orchestrator_state_isolation PASSED [ 50%]
test/test_phase1.py::test_bug06_fallback_preserves_orchestrator_backend PASSED [ 62%]
test/test_phase1.py::test_orchestrator_streaming PASSED                  [ 75%]
test/test_phase1.py::test_bug09_bash_timeout_message PASSED              [ 87%]
test/test_phase1.py::test_bug11_compaction_tool_pairing_guard PASSED     [100%]

============================== 8 passed in 0.70s ===============================
```

### CLI Command Verification

1. **CLI Help & Subcommands**:
   ```bash
   alpiecode --help
   ```
   Validated clean argument parser assembly with no duplicate command collisions.

2. **System Health Diagnostic (`doctor`)**:
   ```bash
   alpiecode doctor
   ```
   Executed properly from the single consolidated handler at line 142.

3. **Diff Inspection (`diff`)**:
   ```bash
   alpiecode diff
   ```
   Correctly executed `git_ops.show_diff()` with rich terminal syntax formatting.
