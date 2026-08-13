/**
 * AlpieCode VS Code Extension — Main Entry Point.
 *
 * Registers the chat sidebar webview, code action commands,
 * and handles extension lifecycle.
 */

import * as vscode from "vscode";
import { ChatViewProvider } from "./chatViewProvider";
import { registerCodeActions } from "./codeActions";
import { AlpieCompletionProvider } from "./completionProvider";

export function activate(context: vscode.ExtensionContext) {
  console.log("AlpieCode extension activating...");

  // Register the chat sidebar webview provider (pass context for globalState)
  const chatProvider = new ChatViewProvider(context.extensionUri, context);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      ChatViewProvider.viewType,
      chatProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  // Register code action commands (right-click menu)
  registerCodeActions(context, chatProvider);

  // Status bar item
  const statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.text = "$(robot) AlpieCode";
  statusBarItem.tooltip = "AlpieCode AI Agent";
  statusBarItem.command = "alpiecode.chatView.focus";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Register inline code completion provider (ghost-text autocomplete)
  const completionProvider = new AlpieCompletionProvider();
  context.subscriptions.push(
    vscode.languages.registerInlineCompletionItemProvider(
      { pattern: "**" },
      completionProvider
    )
  );

  console.log("AlpieCode extension activated ✅");
}

export function deactivate() {
  console.log("AlpieCode extension deactivated.");
}
