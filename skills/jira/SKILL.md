---
name: jira
description: 用 Jira Cloud REST API v3 查詢與操作 issue。當使用者提到 Jira、要建立 / 更新 / 查詢 issue、跑 JQL、加 comment、轉狀態（transition / 移到 Done / In Progress）、貼一個 Jira issue 連結或 issue key（如 ABC-123）要你去讀內容、或要把某件事「開成 Jira 票」時務必觸發——即使他只說「開個票」「更新一下那張卡」「Jira 上那個 XXX 現在什麼狀態」而沒明講 API。透過內建的 jira.py wrapper 操作，已處理好 Basic Auth、ADF 格式與 v3 的 cursor 分頁。寫入類操作（建立 / 更新 / comment / 轉狀態）會動到真的 Jira，執行前先跟使用者確認。
user-invocable: true
argument-hint: "[要對 Jira 做的事，如「查 ABC 專案未完成的票」「把 ABC-12 轉到 Done」]"
---

# Jira Cloud

用 `scripts/jira.py`（純 Python stdlib，無外部依賴）操作 Jira Cloud v3 API。
它把三個最容易踩雷的地方包起來了，所以照著下面用就好，不用自己拼 curl：

- **Auth**：Basic auth（`email:api_token` base64），從環境變數讀。
- **ADF**：v3 的 `description` / comment 不吃純字串，要 Atlassian Document Format
  （一包 JSON）。wrapper 會自動把純文字轉成 ADF。
- **搜尋**：舊的 `/rest/api/3/search` 已被移除（回 `410 Gone`），改用
  `/search/jql`，而且是 cursor 分頁（`nextPageToken`、沒有 `total`）。wrapper 處理好了。

需要 wrapper 沒包到的操作（找 custom field id、查 create metadata、手刻 ADF 清單/程式碼區塊、`update` 的 verb 語法等），讀 [references/api.md](references/api.md) 的 raw curl 範例。

## One-time setup

wrapper 從三個環境變數讀憑證，**不要**把 token 寫進任何檔案：

```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"   # 站台根，結尾不要帶 /rest
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="…"   # 於 https://id.atlassian.com/manage-profile/security/api-tokens 產生
```

token 只在產生當下顯示一次，且可單獨撤銷。設完先驗證連得上：

```bash
python3 scripts/jira.py myself
# -> Connected as <name> <email> / accountId: …
```

若使用者還沒設好，先引導他做這步，不要試圖繞過認證。

## 寫入前先確認

`create` / `update` / `comment` / `transition` 會改動到真正的 Jira，別人會看到、可能觸發通知與自動化。動手前：

1. 先把「要開哪個專案、什麼 type、summary/內容」或「要改哪張票的哪個欄位」講清楚給使用者確認。
2. 不確定 project key、issue type 名稱、custom field id、或有哪些 transition 時，
   **先查再寫**（見下方「查 ID / metadata」與 references/api.md），不要猜。
3. 確認後再執行；執行完把回傳的 issue key / 連結貼給使用者。

讀取類（`myself` / `search` / `get` / `transitions`）沒有副作用，可以放心跑。

## 常用操作

```bash
# 查詢（JQL）：預設回 summary,status 兩欄，表格輸出
python3 scripts/jira.py search "project = ABC AND statusCategory != Done ORDER BY updated DESC"
python3 scripts/jira.py search "assignee = currentUser() AND sprint in openSprints()" \
        --fields summary,status,assignee --all        # --all 會跟著 nextPageToken 抓完所有頁

# 看單一 issue（--fields 省略則回全部欄位，JSON）
python3 scripts/jira.py get ABC-123 --fields summary,status,description,assignee

# 建立 issue（--desc 是純文字，會自動轉 ADF）
python3 scripts/jira.py create --project ABC --type Task \
        --summary "修正登入頁 race condition" \
        --desc "重現步驟：\n1. …\n2. …"
# 額外欄位用 --field key=value（value 可以是 JSON），可重複：
python3 scripts/jira.py create --project ABC --type Bug --summary "…" \
        --field 'priority={"name":"High"}' --field 'labels=["backend"]' \
        --field 'customfield_10011=5'

# 更新欄位（回 204，wrapper 印 "updated"）
python3 scripts/jira.py update ABC-123 --summary "新標題"
python3 scripts/jira.py update ABC-123 --field 'assignee={"accountId":"5b…"}'

# 加 comment
python3 scripts/jira.py comment ABC-123 "已在 staging 驗過，可以 merge。"

# 轉狀態：先列出目前可用的 transition，再轉（--to 收 id 或名稱，大小寫不拘）
python3 scripts/jira.py transitions ABC-123
python3 scripts/jira.py transition ABC-123 --to "Done"
python3 scripts/jira.py transition ABC-123 --to 31 --comment "驗收通過"
```

## 查 ID / metadata

Project key、issue type 名稱、custom field id 都是每個站台不一樣的，要查不要猜。
`transitions` 子命令會列出某張票當下能走的 transition；其餘（專案清單、某專案的
issue types、create metadata 的必填欄位、所有 field 對照 custom field id）用
[references/api.md](references/api.md) 的 raw curl。找到 custom field id 後就能用
`--field 'customfield_xxxxx=…'` 帶進 create/update。

## 錯誤處理

wrapper 會把 Jira 原始的錯誤 body 印出來——它通常會直接點名哪個欄位有問題
（例：`customfield_10011 is required`）。看到就照它說的補欄位或改值，不要盲試。
認證錯（401/403）先回頭檢查三個環境變數；`410` 幾乎都是還在用舊 search 端點。
