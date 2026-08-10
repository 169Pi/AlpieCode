"""
FastAPI HTTP server for AlpieCode.

Exposes REST and SSE streaming endpoints for web UIs, IDE plugins (VS Code, JetBrains, Neovim),
and remote API clients.
"""

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException, Request, Response
    from fastapi.responses import JSONResponse, StreamingResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from .config import load_config
from .orchestrator import AgentEvent, AgentOrchestrator, resolve_backend
from .prompt import PromptBuilder
from .session import SessionManager


if HAS_FASTAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """FastAPI lifespan startup & shutdown resource management."""
        cfg = load_config()
        app.state.cfg = cfg
        app.state.backend = resolve_backend(cfg)
        app.state.prompt_builder = PromptBuilder()
        app.state.session_mgr = SessionManager()
        app.state.orchestrator = AgentOrchestrator(
            backend=app.state.backend,
            prompt_builder=app.state.prompt_builder,
        )
        app.state.start_time = time.time()

        yield

        # Shutdown resources cleanly
        if hasattr(app.state, "backend") and app.state.backend:
            app.state.backend.shutdown()

    app = FastAPI(
        title="AlpieCode Agent API",
        description="Scalable backend API powering AlpieCode CLI and IDE plugins",
        version="0.7.2",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check():
        """Health check and engine status."""
        backend_name = app.state.backend.name if hasattr(app.state, "backend") else "unknown"
        is_avail = app.state.backend.is_available if hasattr(app.state, "backend") else False
        uptime = time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0.0
        return {
            "status": "online",
            "backend": backend_name,
            "available": is_avail,
            "uptime_seconds": round(uptime, 2),
            "version": "0.7.2",
        }

    @app.get("/sessions")
    async def list_sessions():
        """List active sessions."""
        return {"sessions": app.state.session_mgr.list_sessions()}

    @app.delete("/sessions/{session_id}")
    async def delete_session(session_id: str):
        """Delete an active session."""
        success = app.state.session_mgr.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": session_id}

    @app.post("/cancel/{session_id}")
    async def cancel_session(session_id: str):
        """Cancel an in-progress session task."""
        session = app.state.session_mgr.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.cancelled = True
        return {"status": "cancellation_requested", "session_id": session_id}

    @app.post("/chat")
    async def chat_endpoint(request: Request):
        """
        Execute agent task and stream response as Server-Sent Events (SSE).
        """
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        task = body.get("task")
        if not task:
            raise HTTPException(status_code=400, detail="Missing required 'task' parameter")

        workdir_str = body.get("workdir", ".")
        workdir = Path(workdir_str).resolve()
        session_id = body.get("session_id")

        session = app.state.session_mgr.get_session(session_id) if session_id else None
        if not session:
            session = app.state.session_mgr.create_session(
                workdir=workdir,
                max_tokens=app.state.cfg.n_ctx,
                session_id=session_id,
            )

        import asyncio
        import queue
        import threading

        event_queue = queue.Queue()

        def producer():
            try:
                orchestrator: AgentOrchestrator = app.state.orchestrator
                for event in orchestrator.run_task(
                    session=session,
                    task=task,
                    cfg=app.state.cfg,
                    image_path=body.get("image"),
                    video_path=body.get("video"),
                    url=body.get("url"),
                    github_repo=body.get("github"),
                ):
                    event_queue.put(event)
            finally:
                event_queue.put(None)  # Sentinel to signal completion

        threading.Thread(target=producer, daemon=True).start()

        async def event_generator():
            while True:
                # Poll queue asynchronously without blocking event loop
                event = await asyncio.to_thread(event_queue.get)
                if event is None:
                    break
                data_json = json.dumps(event.data)
                yield f"event: {event.type}\ndata: {data_json}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-ID": session.id,
            },
        )

    @app.get("/metrics")
    async def get_metrics():
        """Observability metrics."""
        sessions = app.state.session_mgr.list_sessions()
        return {
            "active_sessions": len(sessions),
            "backend": app.state.backend.name if hasattr(app.state, "backend") else "unknown",
            "uptime_seconds": round(time.time() - app.state.start_time, 2) if hasattr(app.state, "start_time") else 0.0,
        }

else:
    app = None


def run_server(host: str = "127.0.0.1", port: int = 7169) -> None:
    """Start the uvicorn ASGI server."""
    if not HAS_FASTAPI:
        print("❌ FastAPI/Uvicorn is not installed. Install with: pip install 'alpiecode[server]' or pip install fastapi uvicorn")
        return

    import uvicorn
    print(f"🚀 Starting AlpieCode Server on http://{host}:{port}")
    uvicorn.run("codeagent.server:app", host=host, port=port, reload=False)
