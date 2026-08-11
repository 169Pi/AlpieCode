/**
 * Code Action provider for AlpieCode.
 *
 * Registers right-click context menu commands that send selected code
 * and diagnostic information to the AlpieCode chat panel.
 */

import * as vscode from "vscode";
import { ChatViewProvider } from "./chatViewProvider";

/**
 * Register all code action commands.
 */
export function registerCodeActions(
  context: vscode.ExtensionContext,
  chatProvider: ChatViewProvider
) {
  // Fix This Error — uses diagnostics + selection
  context.subscriptions.push(
    vscode.commands.registerCommand("alpiecode.fixError", () => {
      const { fileInfo, selection } = getEditorContext();
      if (!fileInfo) { return; }

      const diagnostics = vscode.languages.getDiagnostics(fileInfo.uri);
      const relevantDiags = diagnostics
        .filter(
          (d) =>
            d.severity === vscode.DiagnosticSeverity.Error ||
            d.severity === vscode.DiagnosticSeverity.Warning
        )
        .slice(0, 5)
        .map(
          (d) =>
            `Line ${d.range.start.line + 1}: [${severityLabel(d.severity)}] ${d.message}`
        );

      const diagText =
        relevantDiags.length > 0
          ? `\n\nDiagnostics:\n${relevantDiags.join("\n")}`
          : "";

      const task = `Fix the errors in ${fileInfo.relativePath} (${fileInfo.language}).${diagText}\n\nCode:\n\`\`\`${fileInfo.language}\n${selection}\n\`\`\``;
      chatProvider.sendTask(task);
    })
  );

  // Generate Tests
  context.subscriptions.push(
    vscode.commands.registerCommand("alpiecode.generateTests", () => {
      const { fileInfo, selection } = getEditorContext();
      if (!fileInfo) { return; }

      const task = `Generate comprehensive unit tests for the following code in ${fileInfo.relativePath} (${fileInfo.language}).\n\nCode:\n\`\`\`${fileInfo.language}\n${selection}\n\`\`\``;
      chatProvider.sendTask(task);
    })
  );

  // Explain Code
  context.subscriptions.push(
    vscode.commands.registerCommand("alpiecode.explainCode", () => {
      const { fileInfo, selection } = getEditorContext();
      if (!fileInfo) { return; }

      const task = `Explain the following code in ${fileInfo.relativePath} (${fileInfo.language}). Be thorough but concise.\n\nCode:\n\`\`\`${fileInfo.language}\n${selection}\n\`\`\``;
      chatProvider.sendTask(task);
    })
  );

  // Refactor / Optimize
  context.subscriptions.push(
    vscode.commands.registerCommand("alpiecode.refactorCode", () => {
      const { fileInfo, selection } = getEditorContext();
      if (!fileInfo) { return; }

      const task = `Refactor and optimize the following code in ${fileInfo.relativePath} (${fileInfo.language}). Improve readability, performance, and maintainability.\n\nCode:\n\`\`\`${fileInfo.language}\n${selection}\n\`\`\``;
      chatProvider.sendTask(task);
    })
  );

  // Ask About Selection — opens input box for custom question
  context.subscriptions.push(
    vscode.commands.registerCommand("alpiecode.askAboutCode", async () => {
      const { fileInfo, selection } = getEditorContext();
      if (!fileInfo) { return; }

      const question = await vscode.window.showInputBox({
        prompt: "What would you like to ask about this code?",
        placeHolder: "e.g., How can I make this async?",
      });

      if (!question) { return; }

      const task = `${question}\n\nFile: ${fileInfo.relativePath} (${fileInfo.language})\n\nCode:\n\`\`\`${fileInfo.language}\n${selection}\n\`\`\``;
      chatProvider.sendTask(task);
    })
  );
}

interface EditorContext {
  fileInfo: { uri: vscode.Uri; relativePath: string; language: string } | null;
  selection: string;
}

function getEditorContext(): EditorContext {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor. Open a file first.");
    return { fileInfo: null, selection: "" };
  }

  const document = editor.document;
  const sel = editor.selection;
  const selectedText = sel.isEmpty
    ? document.getText() // Use entire file if no selection
    : document.getText(sel);

  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || "";
  const relativePath = workspaceFolder
    ? document.uri.fsPath.replace(workspaceFolder, "").replace(/^[\\/]/, "")
    : document.uri.fsPath;

  return {
    fileInfo: {
      uri: document.uri,
      relativePath,
      language: document.languageId,
    },
    selection: selectedText,
  };
}

function severityLabel(severity: vscode.DiagnosticSeverity): string {
  switch (severity) {
    case vscode.DiagnosticSeverity.Error:
      return "ERROR";
    case vscode.DiagnosticSeverity.Warning:
      return "WARNING";
    case vscode.DiagnosticSeverity.Information:
      return "INFO";
    case vscode.DiagnosticSeverity.Hint:
      return "HINT";
    default:
      return "UNKNOWN";
  }
}
