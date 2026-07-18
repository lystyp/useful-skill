---
name: pr-inline-comment
description: 在 GitHub PR 或 GitLab MR 的指定程式碼行上發、改、刪 inline review comment。處理 commit SHA 取得、行號錨定（新增／刪除／未變動行各有規則）、以及「行號必須以整數送出」這個會讓留言被靜默降級成一般留言的踩雷點。
user-invocable: true
argument-hint: "<PR/MR URL>（其餘細節用對話描述：哪個檔案哪一行、要發什麼）"
---

# PR / MR Inline Comment

把 review 出來的問題掛到對應的程式碼行上。通常接在 `code-review` 之後使用。

支援 **GitHub**（`gh`）與 **GitLab**（`glab`）。兩邊的概念一樣、欄位名不同，下面分開寫；**共通的踩雷點集中在最後一節，動手前務必看**。

留言內文格式見 `review-finding-format` skill 的「精簡格式」：問題 / 🗣️ 白話情境 / 解法三段。因為留言已錨定在程式碼行上，內文不需要再重述檔案與行號脈絡。

---

## GitHub

### 前置

`gh` 已安裝並登入（`gh auth status` 可確認）。在 repo 目錄內執行時不必指定 repo；否則帶 `--repo <owner>/<name>`。

### Step 1：取得 head commit SHA

inline comment 要錨定在某個 commit 上：

```bash
gh pr view <n> --json headRefOid,baseRefName,files
```

取 `headRefOid` 當 `commit_id`。

### Step 2：確認檔案路徑與行號

- **路徑**：用 PR diff 裡的路徑（注意 monorepo 前綴，例如 `backend/src/...`，不是你的 workspace 相對路徑）
- **行號**：`line` 指**該行在檔案中的行號**（不是 diff 的位移），搭配 `side`：
  - 新增行、未變動的 context 行 → `side: "RIGHT"`
  - 被刪除的行 → `side: "LEFT"`
  - 多行留言 → 另帶 `start_line` 與 `start_side`

**務必先驗證行號**（從 diff hunk 推算容易差一）：

```bash
gh api "repos/<owner>/<repo>/contents/<path>?ref=<head_sha>" \
  --jq '.content' | base64 -d | sed -n '<起>,<迄>p' | cat -n
```

### Step 3：發布

```bash
python3 - <<'PY'
import json
body = open('/tmp/comment.md', encoding='utf-8').read()
json.dump({
    "body": body,
    "commit_id": "<head_sha>",
    "path": "<diff 檔案路徑>",
    "line": 93,            # 整數
    "side": "RIGHT",
}, open('/tmp/payload.json','w',encoding='utf-8'), ensure_ascii=False)
PY

gh api --method POST \
  -H "Accept: application/vnd.github+json" \
  --input /tmp/payload.json \
  "repos/<owner>/<repo>/pulls/<n>/comments"
```

> 若改用 `-f` / `-F` 而非 `--input`：`-f` 一律送字串、`-F` 才會解析成數字。`line` 用 `-f` 送會是字串（見最後一節）。

### 修改 / 刪除

comment id 從 `gh api "repos/<owner>/<repo>/pulls/<n>/comments" --jq '.[].id'` 取得。

```bash
# 改內文（不動位置）
gh api --method PATCH --input /tmp/update.json \
  "repos/<owner>/<repo>/pulls/comments/<comment_id>"

# 刪除（成功回 204）
gh api --method DELETE "repos/<owner>/<repo>/pulls/comments/<comment_id>"
```

---

## GitLab

### 前置

`glab` 已安裝並登入。**所有指令都要以 `GITLAB_HOST=<host>` 前綴執行**——git remote 的 ssh port 與 API port 常常不同，不帶會 `404` / `None of the git remotes...`。

從 MR URL 拆出：
- **host**：`scheme://` 後到第一個 `/` 前，含 port
- **project path**：host 後到 `/-/merge_requests/` 前
- **MR iid**：`/-/merge_requests/` 後的數字
- API 用的 project id 需 URL-encode（`/` → `%2F`）

### Step 1：取得 diff 版本 SHA

GitLab 的 `position` 需要**三個** SHA：

```bash
GITLAB_HOST=<host> glab api "projects/<encoded-id>/merge_requests/<iid>/versions"
```

取陣列**第一筆（最新版本）**的 `base_commit_sha`、`start_commit_sha`、`head_commit_sha`。

### Step 2：確認檔案路徑與行號

- **路徑**：用 MR diff 裡的路徑（注意 monorepo 前綴）
- **行號錨定規則**（依該行在 diff 的性質）：
  - 新增行（`+`）：只給 `new_line`
  - 刪除行（`-`）：只給 `old_line`
  - 未變動的 context 行：`old_line` 與 `new_line` **都要給**（缺一會被拒）

**務必先驗證行號**：

```bash
GITLAB_HOST=<host> glab api \
  "projects/<encoded-id>/repository/files/<url-encoded-path>/raw?ref=<head_sha>" \
  | sed -n '<起>,<迄>p' | cat -n
```

> 檔案路徑也要 URL-encode（`/` → `%2F`）。

### Step 3：發布

```bash
python3 - <<'PY'
import json
body = open('/tmp/comment.md', encoding='utf-8').read()
json.dump({
    "body": body,
    "position": {
        "position_type": "text",
        "base_sha":  "<base_commit_sha>",
        "start_sha": "<start_commit_sha>",
        "head_sha":  "<head_commit_sha>",
        "new_path":  "<diff 檔案路徑>",
        "old_path":  "<diff 檔案路徑>",
        "new_line":  93,    # 整數；context 行再加 "old_line": <int>
    },
}, open('/tmp/payload.json','w',encoding='utf-8'), ensure_ascii=False)
PY

GITLAB_HOST=<host> glab api --method POST \
  -H "Content-Type: application/json" \
  --input /tmp/payload.json \
  "projects/<encoded-id>/merge_requests/<iid>/discussions"
```

### 修改 / 刪除

```bash
# 改內文（不動位置）
GITLAB_HOST=<host> glab api --method PUT \
  -H "Content-Type: application/json" --input /tmp/update.json \
  "projects/<encoded-id>/merge_requests/<iid>/notes/<note_id>"

# 刪除（需 discussion id，成功回 204）
GITLAB_HOST=<host> glab api --method DELETE \
  "projects/<encoded-id>/merge_requests/<iid>/discussions/<discussion_id>/notes/<note_id>"
```

---

## 共通踩雷點

### ⚠️ 行號必須是整數，否則留言會被靜默降級

**這是最容易踩、也最難發現的一個。** 兩邊的 CLI 都有「raw string field」旗標（`-f`），用它送行號會變成字串：

- GitLab：整個 `position` 會被**靜默丟棄**，留言變成不掛在任何行上的一般 MR comment
- GitHub：請求會被拒或落到非預期位置

**一律用 JSON body（`--input` + `Content-Type: application/json`）**，讓行號保持整數型別。

順帶：先把留言內文寫到檔案再用程式組 JSON，可以避免 backtick、換行、引號被 shell 吃掉。

### 一定要驗證「確實是 inline」

POST 回應裡的位置欄位應**非 null**（GitHub 看 `line`/`path`，GitLab 看 `notes[0].position`）。保險起見再列一次確認：

```bash
# GitHub
gh api "repos/<owner>/<repo>/pulls/<n>/comments" \
  --jq '.[] | "\(.id) \(.path) \(.line)"'

# GitLab
GITLAB_HOST=<host> glab api "projects/<encoded-id>/merge_requests/<iid>/discussions" \
  | python3 -c "import sys,json; [print(n['id'], (n.get('position') or {}).get('new_path'), (n.get('position') or {}).get('new_line')) for d in json.load(sys.stdin) for n in d['notes']]"
```

位置是 `null` → 它是一般留言，**刪掉重發**（多半是行號被當字串送了）。

### 行號一定要先核對過再發

從 diff hunk 標頭算出來的行號很容易差一。發之前用 head SHA 的**實際檔案內容**對一次（上面兩邊都有指令）。

## 注意事項

- 發布 / 修改 / 刪除留言都是**對外動作**，會出現在別人的 PR / MR 上。動手前確認內容與目標行無誤，批量發之前先讓使用者過目清單。
- 若另有「需請 PM／設計確認」的延伸點（非純程式問題），放在解法**之後**、用 `---` 分隔並標 `📋`，與開發者要動手的部分區隔開。
