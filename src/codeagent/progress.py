"""
Progress Monitor for AlpieCode.

Tracks per-turn agent progress by observing tool calls and results.
Detects stalls (zero net progress) and thrashing (delete-after-create loops).
Does NOT kill the agent — only signals the orchestrator to inject corrective prompts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from pathlib import Path


@dataclass
class TurnSnapshot:
    """Captures what happened in a single turn."""
    turn: int
    tools_called: List[str] = field(default_factory=list)
    files_created: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)
    files_deleted: Set[str] = field(default_factory=set)
    bash_exit_codes: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    had_progress: bool = False


class ProgressMonitor:
    """Tracks agent progress across turns.

    Progress = files created, files modified, successful bash runs,
    or errors changing (not repeating the same error).

    Stall = 3+ consecutive turns with zero net progress.
    Thrashing = deleting files the agent itself created.
    """

    def __init__(self):
        self.history: List[TurnSnapshot] = []
        self.all_files_created: Set[str] = set()
        self.consecutive_stalls: int = 0
        self.stall_interventions: int = 0

    def record_turn(self, turn: int, tool_calls: list, tool_results: list) -> TurnSnapshot:
        """Record what happened in a turn and determine if progress was made."""
        snap = TurnSnapshot(turn=turn)

        for tc in tool_calls:
            name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            args = tc.get("arguments", {}) if isinstance(tc, dict) else getattr(tc, "arguments", {})
            if not isinstance(args, dict):
                args = {}
            snap.tools_called.append(name)

            if name == "write_file":
                path = args.get("path", "")
                snap.files_created.add(path)
                self.all_files_created.add(path)

            elif name == "edit_file":
                path = args.get("path", "")
                snap.files_modified.add(path)

            elif name == "bash":
                cmd = args.get("command", "")
                cmd_parts = cmd.strip().split()
                if cmd_parts and cmd_parts[0] in ("rm", "del", "Remove-Item"):
                    for part in cmd_parts[1:]:
                        if not part.startswith("-"):
                            clean = Path(part.strip("\'\"")).name
                            snap.files_deleted.add(clean)

        # Parse tool results for exit codes and errors
        for res in tool_results:
            content = res.get("content", "") if isinstance(res, dict) else getattr(res, "content", "")
            if '"exit_code": 0' in content or '"exit_code":0' in content:
                snap.bash_exit_codes.append(0)
            elif '"exit_code":' in content:
                snap.bash_exit_codes.append(1)
                snap.errors.append(f"command failed: {content[:100]}")
            if content.lower().startswith("error:") or "error:" in content[:80].lower():
                snap.errors.append(content[:100])

        # Determine progress
        snap.had_progress = bool(
            snap.files_created
            or snap.files_modified
            or (snap.bash_exit_codes and 0 in snap.bash_exit_codes)
        )

        # No tools called at all = not progress (empty turn)
        if not snap.tools_called:
            snap.had_progress = True  # text-only response = model is finishing

        # Detect thrashing: deleting a file that was created recently
        created_names = {Path(f).name for f in self.all_files_created}
        thrashing = snap.files_deleted & created_names
        if thrashing:
            snap.had_progress = False

        # Detect identical consecutive errors (stall)
        if len(self.history) >= 2 and snap.errors:
            prev_errors = set(e[:60] for e in self.history[-1].errors)
            curr_errors = set(e[:60] for e in snap.errors)
            if curr_errors and curr_errors == prev_errors:
                snap.had_progress = False

        # Detect pure read-only turns with errors as non-progress
        if snap.errors and not snap.files_created and not snap.files_modified:
            if not (snap.bash_exit_codes and 0 in snap.bash_exit_codes):
                snap.had_progress = False

        # Update stall counter
        if snap.had_progress:
            self.consecutive_stalls = 0
        else:
            self.consecutive_stalls += 1

        self.history.append(snap)
        return snap

    def is_stalled(self, threshold: int = 3) -> bool:
        """Returns True if the agent has made zero net progress for N consecutive turns."""
        return self.consecutive_stalls >= threshold

    def get_stall_advice(self) -> str:
        """Generate a corrective prompt for the model when stalled."""
        self.stall_interventions += 1

        recent = self.history[-3:] if len(self.history) >= 3 else self.history
        deleted = set()
        for snap in recent:
            deleted.update(snap.files_deleted)

        created_names = {Path(f).name for f in self.all_files_created}
        thrashing = deleted & created_names

        if thrashing:
            return (
                f"[SYSTEM - PROGRESS MONITOR] You have been deleting files you previously "
                f"created ({', '.join(thrashing)}). STOP deleting and rewriting from scratch. "
                f"Use edit_file to modify specific sections, or overwrite directly with write_file. "
                f"Take a step back: what is the simplest path to a working solution?"
            )

        if all(snap.errors or (snap.bash_exit_codes and 0 not in snap.bash_exit_codes) for snap in recent):
            return (
                "[SYSTEM - PROGRESS MONITOR] You have encountered errors for 3 consecutive turns. "
                "STOP retrying the same approach. Instead:\n"
                "1. Use read_file to examine the FULL current state of the file(s) you\'re editing\n"
                "2. Identify the root cause of the error (not the symptom)\n"
                "3. Make ONE comprehensive fix that addresses all issues\n"
                "If the task approach is fundamentally wrong, start with a simpler design."
            )

        return (
            "[SYSTEM - PROGRESS MONITOR] No measurable progress detected for 3 turns. "
            "You may be stuck in a loop. Either:\n"
            "1. Complete your current work and output DONE: <summary>\n"
            "2. Try a completely different approach to the problem\n"
            "3. If the code is written and working, verify with bash and finish."
        )

    def get_status_summary(self) -> dict:
        """Return a summary of overall progress for logging."""
        total_files = len(self.all_files_created)
        total_turns = len(self.history)
        success_turns = sum(1 for s in self.history if s.had_progress)
        return {
            "total_turns": total_turns,
            "progress_turns": success_turns,
            "stall_turns": total_turns - success_turns,
            "files_created": total_files,
            "stall_interventions": self.stall_interventions,
            "consecutive_stalls": self.consecutive_stalls,
        }
