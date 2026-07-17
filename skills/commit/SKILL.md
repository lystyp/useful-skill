---
name: commit
description: 根據 git staged/unstaged changes 撰寫 commit 訊息並提交
user-invocable: true
disable-model-invocation: true
---

# Commit Skill

## 步驟

1. **先問使用者**：要根據哪種變更來撰寫 commit 訊息？
   - **staged**（只看已 `git add` 的變更）→ 執行 `git diff --staged`
   - **both**（staged + unstaged 都看）→ 執行 `git diff --staged` 和 `git diff`

2. 同時執行 `git log --oneline -10` 查看最近的 commit 風格作為參考。

3. 根據 diff 內容分析變更，並參考 `git log` 中的歷史 commit 格式（前綴、語言、風格）來撰寫 commit 訊息：
   - 第一行簡潔描述，格式需與歷史 commit 保持一致
   - 如果變更較複雜，加上詳細說明
   - **訊息要寫成對其他 code reviewer 也能看得懂的版本**：避免只有作者自己才懂的術語縮寫；涉及非顯而易見的設計決策時，簡短說明動機與取捨，讓 reviewer 不用翻聊天紀錄也能理解 why

4. **將草擬的 commit 訊息展示給使用者確認**，詢問是否需要修改。

5. 使用者確認後：
   - 如果使用者選的是 **both**，先列出未 staged 的檔案，詢問是否要 `git add` 相關檔案
   - 執行 `git commit`

## 注意事項

- **訊息中不得出現任何 AI attribution**：不加 `Co-Authored-By: Claude ...`，也不加 `🤖 Generated with Claude Code` 之類的標記。這條必須明寫——預設行為會自動補上 trailer，沒有明令禁止就會被加進去。
- 不要自動 push，除非使用者明確要求
- commit 訊息使用 HEREDOC 格式傳遞，確保格式正確
- 不要使用 `git add -A` 或 `git add .`，應列出具體檔案讓使用者確認
