"""
Client SDK for AlpieCode API server.

Provides a clean, typed interface for connecting to an AlpieCode server (`alpiecode serve`),
streaming SSE events, managing sessions, and canceling tasks.
Used by the CLI client mode and future IDE/remote Python integrations.
"""

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .orchestrator import AgentEvent


class AlpieCodeClient:
    """Client for interacting with a running AlpieCode API server."""

    def __init__(self, base_url: str = "http://127.0.0.1:7169", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> Dict[str, Any]:
        """Check server health and backend status."""
        req = urllib.request.Request(f"{self.base_url}/health")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def metrics(self) -> Dict[str, Any]:
        """Get server observability metrics."""
        req = urllib.request.Request(f"{self.base_url}/metrics")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def list_sessions(self) -> list:
        """List active server sessions."""
        req = urllib.request.Request(f"{self.base_url}/sessions")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("sessions", [])
        except Exception:
            return []

    def cancel_task(self, session_id: str) -> bool:
        """Request cancellation of an in-progress task session."""
        req = urllib.request.Request(
            f"{self.base_url}/cancel/{session_id}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def stream_chat(
        self,
        task: str,
        workdir: str = ".",
        session_id: Optional[str] = None,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        url: Optional[str] = None,
        github_repo: Optional[str] = None,
    ) -> Iterator[AgentEvent]:
        """
        Stream agent events from POST /chat using Server-Sent Events (SSE).
        Yields AgentEvent instances.
        """
        endpoint = f"{self.base_url}/chat"
        payload = json.dumps({
            "task": task,
            "workdir": str(workdir),
            "session_id": session_id,
            "image": image_path,
            "video": video_path,
            "url": url,
            "github": github_repo,
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                current_event_type = "message"
                current_data_str = ""

                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        if current_data_str:
                            try:
                                event_data = json.loads(current_data_str)
                            except Exception:
                                event_data = {"content": current_data_str}
                            yield AgentEvent(type=current_event_type, data=event_data)
                            current_event_type = "message"
                            current_data_str = ""
                        continue

                    if line.startswith("event:"):
                        current_event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        current_data_str = line[5:].strip()

                if current_data_str:
                    try:
                        event_data = json.loads(current_data_str)
                    except Exception:
                        event_data = {"content": current_data_str}
                    yield AgentEvent(type=current_event_type, data=event_data)
        except Exception as e:
            yield AgentEvent(type="error", data={"error": f"Server connection failed: {e}"})
