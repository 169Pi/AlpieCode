/**
 * SSE Streaming Client for AlpieCode backend.
 *
 * Cross-platform (Windows, Linux, macOS). Zero dependencies beyond Node.js builtins.
 * Handles POST /chat SSE streams, health checks, and cancellation.
 */

import * as http from "http";
import * as https from "https";
import { URL } from "url";

export interface AgentEvent {
  type: string;
  data: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  backend: string;
  available: boolean;
  uptime_seconds: number;
  version: string;
}

/* ------------------------------------------------------------------ */
/*  Health check                                                      */
/* ------------------------------------------------------------------ */

export function checkHealth(serverUrl: string): Promise<HealthResponse | null> {
  return new Promise((resolve) => {
    try {
      const url = new URL("/health", serverUrl);
      const client = url.protocol === "https:" ? https : http;

      const req = client.get(url, { timeout: 4000 }, (res) => {
        let body = "";
        res.on("data", (c: Buffer) => (body += c.toString()));
        res.on("end", () => {
          try { resolve(JSON.parse(body)); }
          catch { resolve(null); }
        });
      });
      req.on("error", () => resolve(null));
      req.on("timeout", () => { req.destroy(); resolve(null); });
    } catch { resolve(null); }
  });
}

/* ------------------------------------------------------------------ */
/*  Cancel a running task                                             */
/* ------------------------------------------------------------------ */

export function cancelTask(serverUrl: string, sessionId: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const url = new URL(`/cancel/${sessionId}`, serverUrl);
      const client = url.protocol === "https:" ? https : http;
      const req = client.request(url, { method: "POST", timeout: 5000 }, (res) => {
        resolve(res.statusCode === 200);
      });
      req.on("error", () => resolve(false));
      req.end();
    } catch { resolve(false); }
  });
}

/* ------------------------------------------------------------------ */
/*  SSE streaming                                                     */
/* ------------------------------------------------------------------ */

export interface StreamOptions {
  task: string;
  workdir: string;
  sessionId?: string;
  image?: string;
}

/**
 * Stream agent events from POST /chat via SSE.
 *
 * Returns an abort function. Handles:
 * - Multi-line `data:` fields
 * - Proper event boundary detection
 * - Double-fire guard on done callback
 * - Informative error messages
 */
export function streamChat(
  serverUrl: string,
  options: StreamOptions,
  onEvent: (event: AgentEvent) => void,
  onError: (error: Error) => void,
  onDone: () => void
): () => void {
  let finished = false;
  const done = () => { if (!finished) { finished = true; onDone(); } };

  try {
    const chatUrl = new URL("/chat", serverUrl);
    const client = chatUrl.protocol === "https:" ? https : http;

    const body: Record<string, any> = {
      task: options.task,
      workdir: options.workdir,
    };
    if (options.sessionId) { body.session_id = options.sessionId; }
    if (options.image) { body.image = options.image; }

    const payload = JSON.stringify(body);

    const req = client.request(
      chatUrl,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "Content-Length": Buffer.byteLength(payload),
        },
      },
      (res) => {
        if (res.statusCode !== 200) {
          let errBody = "";
          res.on("data", (c: Buffer) => (errBody += c.toString()));
          res.on("end", () => {
            onError(new Error(`Server returned ${res.statusCode}: ${errBody}`));
            done();
          });
          return;
        }

        // SSE parser state
        let buf = "";
        let evtType = "message";
        let dataLines: string[] = [];

        res.on("data", (chunk: Buffer) => {
          buf += chunk.toString();
          const lines = buf.split("\n");
          buf = lines.pop() || "";

          for (const line of lines) {
            if (line === "" || line === "\r") {
              // Blank line → dispatch event
              if (dataLines.length > 0) {
                const raw = dataLines.join("\n");
                let parsed: any;
                try { parsed = JSON.parse(raw); }
                catch { parsed = { content: raw }; }
                onEvent({ type: evtType, data: parsed });
              }
              evtType = "message";
              dataLines = [];
            } else if (line.startsWith("event:")) {
              evtType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trimStart());
            }
            // Ignore comments (':') and other SSE fields
          }
        });

        res.on("end", () => {
          if (dataLines.length > 0) {
            const raw = dataLines.join("\n");
            try { onEvent({ type: evtType, data: JSON.parse(raw) }); }
            catch { /* ignore trailing garbage */ }
          }
          done();
        });

        res.on("error", (e) => { onError(e); done(); });
      }
    );

    req.on("error", (e) => {
      onError(new Error(`Cannot reach server: ${e.message}. Is 'alpiecode serve' running?`));
      done();
    });

    req.write(payload);
    req.end();

    return () => { req.destroy(); done(); };
  } catch (e: any) {
    onError(new Error(`Connection failed: ${e.message}`));
    done();
    return () => {};
  }
}
