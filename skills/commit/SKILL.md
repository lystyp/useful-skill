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

3. 根據 diff 內容分析變更，撰寫 commit 訊息：
   - 第一行簡潔描述（中文或英文，依照 git log 中的既有風格）
   - 如果變更較複雜，加上詳細說明
   - 結尾加上 `Co-Authored-By: Claude <noreply@anthropic.com>`

4. **將草擬的 commit 訊息展示給使用者確認**，詢問是否需要修改。

5. 使用者確認後：
   - 如果使用者選的是 **both**，先列出未 staged 的檔案，詢問是否要 `git add` 相關檔案
   - 執行 `git commit`

## 注意事項

- 不要自動 push，除非使用者明確要求
- commit 訊息使用 HEREDOC 格式傳遞，確保格式正確
- 不要使用 `git add -A` 或 `git add .`，應列出具體檔案讓使用者確認
