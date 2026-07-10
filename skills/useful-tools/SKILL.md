---
name: useful-tools
description: Daniel 的實用工具設定集——每個工具一份 reference 文件，內含完整設定步驟、原理解說與踩雷排查。當使用者想「設定／重建／排查」以下工具時觸發：claude-code-stop-notification（Claude Code 回覆完成時發 macOS 通知，內容自動帶出該輪提問、點通知跳回對應專案的 VSCode 視窗；以 Stop hook + terminal-notifier 實作，含勿擾模式踩雷指南）。設定前務必先讀 references/ 內對應文件再動手。
---

# Useful Tools

這是一個「工具設定集」skill。每個工具對應 `references/` 下的一份文件，
文件內含：最終行為、前置需求、完整設定步驟、逐段原理解說、已知限制與排查 SOP。

## 收錄的工具

| 工具 | Reference | 用途 |
| --- | --- | --- |
| claude-code-stop-notification | [references/claude-code-stop-notification.md](references/claude-code-stop-notification.md) | Claude Code 回覆完成時發 macOS 通知：內容帶當輪提問前 60 字、點擊跳回該 session 專案的 VSCode 視窗 |

## 使用方式

當使用者提到要設定上述工具、或工具行為異常（例如「沒收到通知」）時：

1. **先讀對應的 reference 文件**，不要憑記憶重新發明設定。
2. 依文件內的步驟設定；排查時依文件內的「排查 SOP」逐層檢查。
3. 文件內記錄了已知限制與取捨（例如 icon 與精準跳轉不可兼得），
   使用者要求超出限制時，直接引用文件說明取捨，不要空承諾。

## 新增工具到這個 skill

之後要收錄新工具時：

1. 在 `references/` 新增 `<tool-name>.md`，結構比照既有文件
   （最終行為 → 前置需求 → 設定步驟 → 原理解說 → 已知限制 → 排查 SOP）。
2. 在本檔「收錄的工具」表格加一列。
3. 更新 frontmatter 的 `description`，讓觸發條件涵蓋新工具。
