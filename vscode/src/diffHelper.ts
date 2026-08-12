/**
 * Diff preview helper for AlpieCode file operations.
 *
 * When the agent emits write_file or edit_file tool calls,
 * this module shows a native VS Code diff view side-by-side so the user can
 * review changes and Accept or Reject them.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

/**
 * Show a native side-by-side diff preview for a file write/edit operation with Accept/Reject buttons.
 *
 * @param workdir - The workspace root directory
 * @param filePath - Relative path to the file being modified
 * @param newContent - The proposed new content
 * @param toolName - "write_file" | "edit_file"
 */
export async function showDiffPreview(
  workdir: string,
  filePath: string,
  newContent: string,
  toolName: string
): Promise<void> {
  const absPath = path.isAbsolute(filePath)
    ? filePath
    : path.join(workdir, filePath);

  const fileUri = vscode.Uri.file(absPath);
  const fileName = path.basename(filePath);

  // Read existing content (empty if new file)
  let fileExists = false;
  let existingContent = "";
  try {
    existingContent = fs.readFileSync(absPath, "utf-8");
    fileExists = true;
  } catch {
    // File doesn't exist yet — new file creation
  }

  // Create virtual documents for diff
  const originalScheme = `alpiecode-original-${Date.now()}`;
  const modifiedScheme = `alpiecode-modified-${Date.now()}`;

  const originalUri = vscode.Uri.parse(
    `${originalScheme}:${fileName}?${encodeURIComponent(existingContent)}`
  );
  const modifiedUri = vscode.Uri.parse(
    `${modifiedScheme}:${fileName}?${encodeURIComponent(newContent)}`
  );

  // Register content providers
  const originalProvider = vscode.workspace.registerTextDocumentContentProvider(
    originalScheme,
    {
      provideTextDocumentContent(uri: vscode.Uri): string {
        return decodeURIComponent(uri.query);
      },
    }
  );

  const modifiedProvider = vscode.workspace.registerTextDocumentContentProvider(
    modifiedScheme,
    {
      provideTextDocumentContent(uri: vscode.Uri): string {
        return decodeURIComponent(uri.query);
      },
    }
  );

  const label =
    toolName === "write_file"
      ? `✨ ${fileName} (AlpieCode: Proposed File Creation)`
      : `✏️ ${fileName} (AlpieCode: Proposed Edit)`;

  // Show native side-by-side diff view
  try {
    await vscode.commands.executeCommand("vscode.diff", originalUri, modifiedUri, label);
  } catch (err) {
    console.error("Failed to open VS Code diff editor:", err);
  }

  // Show Accept/Reject notification popup
  const actionText = fileExists ? "edit" : "create";
  const choice = await vscode.window.showInformationMessage(
    `AlpieCode wants to ${actionText} '${filePath}'. Accept proposed changes?`,
    { modal: false },
    "✅ Accept",
    "❌ Reject"
  );

  if (choice === "✅ Accept") {
    // Ensure parent directory exists
    const dir = path.dirname(absPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(absPath, newContent, "utf-8");
    vscode.window.showInformationMessage(`✅ Accepted & applied changes to '${filePath}'`);

    // Open the target file in active editor
    try {
      const doc = await vscode.workspace.openTextDocument(fileUri);
      await vscode.window.showTextDocument(doc);
    } catch {
      // ignore
    }
  } else {
    // Revert changes on Reject
    if (fileExists) {
      fs.writeFileSync(absPath, existingContent, "utf-8");
    } else if (fs.existsSync(absPath)) {
      try { fs.unlinkSync(absPath); } catch {}
    }
    vscode.window.showInformationMessage(`❌ Rejected changes to '${filePath}'`);
  }

  // Cleanup virtual document providers
  originalProvider.dispose();
  modifiedProvider.dispose();
}
