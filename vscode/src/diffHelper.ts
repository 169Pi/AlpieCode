/**
 * Diff preview helper for AlpieCode file operations.
 *
 * When the agent emits write_file or edit_file tool calls,
 * this module shows a VS Code diff view so the user can
 * review changes before accepting them.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

/**
 * Show a diff preview for a file write/edit operation.
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
  let existingContent = "";
  try {
    existingContent = fs.readFileSync(absPath, "utf-8");
  } catch {
    // File doesn't exist yet — this is a new file creation
  }

  // Create virtual documents for diff
  const originalScheme = "alpiecode-original";
  const modifiedScheme = "alpiecode-modified";

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
      ? `✨ ${fileName} (AlpieCode: Create/Overwrite)`
      : `✏️ ${fileName} (AlpieCode: Edit)`;

  // Show diff view
  await vscode.commands.executeCommand("vscode.diff", originalUri, modifiedUri, label);

  // Show accept/reject dialog
  const choice = await vscode.window.showInformationMessage(
    `AlpieCode wants to ${toolName === "write_file" ? "write" : "edit"} ${filePath}`,
    { modal: false },
    "✅ Accept",
    "❌ Reject"
  );

  if (choice === "✅ Accept") {
    // Ensure directory exists
    const dir = path.dirname(absPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(absPath, newContent, "utf-8");
    vscode.window.showInformationMessage(`✅ Applied changes to ${filePath}`);

    // Open the file after applying
    const doc = await vscode.workspace.openTextDocument(fileUri);
    await vscode.window.showTextDocument(doc);
  } else {
    vscode.window.showInformationMessage(`❌ Rejected changes to ${filePath}`);
  }

  // Cleanup providers
  originalProvider.dispose();
  modifiedProvider.dispose();
}
