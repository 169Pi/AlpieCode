/**
 * Inline Code Completion Provider for AlpieCode.
 *
 * Registers as a VS Code InlineCompletionItemProvider to show ghost-text
 * suggestions as the user types. Press Tab to accept.
 *
 * Features:
 *  - Debounced requests (300ms pause before triggering)
 *  - Cancellation-aware (cancels in-flight requests on new keystrokes)
 *  - Sends prefix + suffix + language to POST /completion
 *  - Works with both online and offline backends
 */

import * as vscode from "vscode";
import * as http from "http";
import * as https from "https";
import { URL } from "url";

/* ------------------------------------------------------------------ */
/*  Configuration                                                     */
/* ------------------------------------------------------------------ */

const DEBOUNCE_MS = 300;     // Wait 300ms after last keystroke
const MIN_PREFIX_LENGTH = 8; // Don't trigger on very short prefixes
const REQUEST_TIMEOUT = 8000; // 8 second timeout

/* ------------------------------------------------------------------ */
/*  Provider                                                          */
/* ------------------------------------------------------------------ */

export class AlpieCompletionProvider implements vscode.InlineCompletionItemProvider {

  private _timer: ReturnType<typeof setTimeout> | null = null;
  private _abortController: AbortController | null = null;

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionItem[] | null> {

    // Check if autocomplete is enabled in settings
    const enabled = vscode.workspace
      .getConfiguration("alpiecode")
      .get<boolean>("enableAutocomplete", true);
    if (!enabled) { return null; }

    // Cancel any previous in-flight request
    if (this._abortController) {
      this._abortController.abort();
      this._abortController = null;
    }

    // Get prefix (code before cursor) and suffix (code after cursor)
    const prefixRange = new vscode.Range(new vscode.Position(0, 0), position);
    const prefix = document.getText(prefixRange);

    // Don't trigger on very short prefixes
    if (prefix.trim().length < MIN_PREFIX_LENGTH) { return null; }

    const suffixRange = new vscode.Range(
      position,
      document.lineAt(Math.min(position.line + 50, document.lineCount - 1)).range.end
    );
    const suffix = document.getText(suffixRange);

    const language = document.languageId;
    const filePath = vscode.workspace.asRelativePath(document.uri);

    // Debounce: wait for user to pause typing
    await this._debounce(token);
    if (token.isCancellationRequested) { return null; }

    // Fetch completion from server
    const serverUrl = vscode.workspace
      .getConfiguration("alpiecode")
      .get<string>("serverUrl", "http://127.0.0.1:7169");

    try {
      const completion = await this._fetchCompletion(
        serverUrl, prefix, suffix, language, filePath, token
      );

      if (!completion || token.isCancellationRequested) { return null; }

      return [
        new vscode.InlineCompletionItem(
          completion,
          new vscode.Range(position, position)
        ),
      ];
    } catch {
      return null;
    }
  }

  /* ---- Debounce ---- */

  private _debounce(token: vscode.CancellationToken): Promise<void> {
    return new Promise((resolve) => {
      if (this._timer) { clearTimeout(this._timer); }
      this._timer = setTimeout(() => {
        this._timer = null;
        resolve();
      }, DEBOUNCE_MS);

      token.onCancellationRequested(() => {
        if (this._timer) { clearTimeout(this._timer); this._timer = null; }
        resolve();
      });
    });
  }

  /* ---- HTTP request to /completion ---- */

  private _fetchCompletion(
    serverUrl: string,
    prefix: string,
    suffix: string,
    language: string,
    filePath: string,
    token: vscode.CancellationToken
  ): Promise<string | null> {
    return new Promise((resolve) => {
      try {
        const url = new URL("/completion", serverUrl);
        const client = url.protocol === "https:" ? https : http;

        const payload = JSON.stringify({
          prefix,
          suffix,
          language,
          file_path: filePath,
          max_tokens: 128,
        });

        const req = client.request(
          url,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Content-Length": Buffer.byteLength(payload),
            },
            timeout: REQUEST_TIMEOUT,
          },
          (res) => {
            let body = "";
            res.on("data", (chunk: Buffer) => (body += chunk.toString()));
            res.on("end", () => {
              try {
                const data = JSON.parse(body);
                resolve(data.completion || null);
              } catch {
                resolve(null);
              }
            });
          }
        );

        req.on("error", () => resolve(null));
        req.on("timeout", () => { req.destroy(); resolve(null); });

        // Wire up cancellation
        token.onCancellationRequested(() => { req.destroy(); resolve(null); });

        req.write(payload);
        req.end();
      } catch {
        resolve(null);
      }
    });
  }

  dispose() {
    if (this._timer) { clearTimeout(this._timer); }
    if (this._abortController) { this._abortController.abort(); }
  }
}
