---
name: explain-mr
description: 白話具體詳細說明一份改動（本地 branch、GitLab MR、GitHub PR）在幹嘛、為什麼要做。使用者問「這隻 branch 在幹嘛」「這個 MR 在做什麼」「說明一下這個 PR」時使用。
user-invocable: true
argument-hint: "[MR/PR URL、branch 名；留空＝當前 branch]"
---

白話具體詳細說明這份改動在幹嘛、為什麼要做。

- 讀 commit 訊息／MR 描述抓動機，再回 code 驗證（呼叫端、頻率、diff 外的 helper 實作）。
- 講出原本的問題機制、怎麼改、行為有沒有變；驗證過的跟作者說的分開寫。
- 說明完問 user 要不要 `git reset` 到這個 MR 第一筆 commit 的上一筆（改動留在工作區方便看 diff），他同意才做。
