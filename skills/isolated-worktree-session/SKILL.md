---
name: isolated-worktree-session
description: 隔離工作流：從當前 HEAD 切 temp branch、在 repo root 外開 worktree（帶 .env、複製當前對話讓新視窗可 resume）、session 嚴格鎖定只在 worktree 內活動、結束時詢問是否 cherry-pick 回原 branch 再清理。使用者輸入 `/isolated-worktree-session` 必定執行；沒被明確呼叫時，Claude 判斷需要隔離也可以自主啟用——同一個 repo 有平行 session 在動、使用者提到「平行作業／隔離／怕污染／別動到主目錄」、或改動大到會讓共用 checkout 長時間處於中間狀態（大範圍 refactor、schema/migration、跨多檔的實驗性改動）。純問答、看 code 不改檔、一兩行瑣碎修改不要啟用；自主啟用前先用一句話宣告理由。
---

# Isolated Worktree Session（隔離工作流）

## 總覽

**手動輸入 `/isolated-worktree-session` 必定執行；Claude 判斷需要隔離時也可以自主啟用，判準見 Step 0。**

從目前 HEAD 切一條 **temp branch**，並為它開一個 **worktree**，把 git 不會帶過去的 `.env` 補進去，然後把當前這段對話複製一份到 worktree 對應的 session 目錄 —— 使用者用新的 VS Code 開 worktree 時，就能在 resume 清單看到同一段對話並直接接下去。整個 session 只在這個 worktree 裡活動 —— 不讀、不寫、不 grep、不 glob、不 cd 到 worktree 以外的任何地方。做完之後，主動詢問使用者要不要把新 commit cherry-pick 回原 branch，然後刪掉 temp branch 與 worktree。

**核心原則：** 目錄硬隔離，**雙向**。(1) 你不去讀 worktree 外的任何東西 —— 之前有 session 把隔壁目錄（另一個平行 session 改到一半的檔案）讀進來當參考，結果回報了一堆「假 bug」。(2) worktree 本身開在 repo root **外面**（sibling 目錄），別的 session 掃 repo root 也讀不到你。所以一旦啟用，這裡不是建議，是硬規定。

## Step 0：確認觸發方式

兩種進入方式都合法：

**A. 使用者親手輸入 `/isolated-worktree-session`** —— 必定執行，不用再判斷。

**B. Claude 自主啟用** —— 沒被 `/` 呼叫，但符合下列任一情況，就可以自己啟用：

- 同一個 repo 有平行 session 在動（`git worktree list` 看得到別人的作業 worktree、使用者提到「另一個視窗／session 也在跑」）
- 使用者表達隔離意圖：「平行作業」「隔離一下」「怕污染」「別動到主目錄」
- 改動大到會讓共用 checkout 長時間處於中間狀態：大範圍 refactor、schema / migration、跨多檔的實驗性改動

自主啟用前，先用一句話宣告理由（例如「這次要動 schema，我開隔離 worktree 做」）；使用者說不用，就直接在當前目錄做，同一輪任務內不要再提。

**不該啟用的情況**：純問答、只看 code 不改檔、一兩行的瑣碎修改、或使用者已明確說「直接改就好」。

觸發後（不論 A 或 B），宣告：「啟用 isolated-worktree-session：先開 temp branch + worktree 再動 code。」然後進 Step 1。

**例外：已經在 linked worktree 裡。** 就算沒被 `/` 呼叫，Step 1 的偵測若發現當前已在 linked worktree，仍要套用 Step 3 的鎖定規則（不要跑出去讀外面）—— 不要新建 worktree。至於做完要不要跑 cherry-pick 流程，看這個 worktree 裡有沒有 `.worktree-session-meta`：
- **有** → 這個 worktree 是這套流程開的（很可能就是使用者換視窗接手的那份對話）。從裡面讀出 `ORIGINAL_BRANCH` / `ORIGINAL_HEAD` / `TEMP_BRANCH` / `REPO_ROOT`，Step 4 之後照跑，收尾由這邊負責。
- **沒有** → 是別人的 worktree。只鎖定，不要跑 Step 5 之後的流程。

## Step 1：先偵測是不是已經在 worktree 裡

**還沒建立任何東西前**先跑：

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
SUBMODULE=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
```

判斷：
- `GIT_DIR != GIT_COMMON` 而且 `SUBMODULE` 是空的 → **已經在 linked worktree 裡**。**跳到 Step 3**，不要再巢狀建立新的 worktree。
- 否則 → 進入 Step 2。

## Step 2：開 temp branch + worktree

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
ORIGINAL_BRANCH=$(git -C "$REPO_ROOT" branch --show-current)
ORIGINAL_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 由使用者請求推一個短描述（kebab-case，8~30 字）
SLUG="<task-slug>"

# 處理原 branch 名稱裡的 /
SAFE_ORIG="${ORIGINAL_BRANCH//\//-}"
TEMP_BRANCH="tmp/${SAFE_ORIG}-${SLUG}-${TIMESTAMP}"
# ⚠️ 一定要開在 repo root「外面」的 sibling，不要開在 ${REPO_ROOT}/.worktrees/ 裡
# —— 開在 repo 內，別的 session 掃 repo root 就會讀到你改到一半的檔（見文末「常見錯誤」）
WORKTREE_DIR="${REPO_ROOT}.worktrees/${SAFE_ORIG}-${SLUG}-${TIMESTAMP}"

# 先建好 sibling 父目錄（git worktree add 不會自動建父層）
mkdir -p "${REPO_ROOT}.worktrees"

# 從「當前 HEAD」開 worktree（不是從 main，也不是從 origin/main）
git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" -b "$TEMP_BRANCH" HEAD

cd "$WORKTREE_DIR"
```

把 session 用得到的資訊寫在 worktree 內（用 `.git/info/exclude` 排除，不會進 commit）：

```bash
mkdir -p .git/info
cat > .worktree-session-meta <<EOF
ORIGINAL_BRANCH=$ORIGINAL_BRANCH
ORIGINAL_HEAD=$ORIGINAL_HEAD
TEMP_BRANCH=$TEMP_BRANCH
WORKTREE_DIR=$WORKTREE_DIR
REPO_ROOT=$REPO_ROOT
EOF
grep -qxF '.worktree-session-meta' .git/info/exclude 2>/dev/null \
  || echo '.worktree-session-meta' >> .git/info/exclude
```

### 把 .env 帶過去（git 不會幫你）

`.env` 幾乎都被 gitignore，所以 `git worktree add` 不會帶過去 —— 新的 worktree 少了環境變數，app 跟測試都跑不起來。而且它不一定在 repo 根目錄，monorepo 常常是 `backend/`、`frontend/` 底下各一份，所以要**保留相對路徑**複製：

```bash
git -C "$REPO_ROOT" ls-files -z --others --ignored --exclude-standard \
    -- ':(glob)**/.env' ':(glob)**/.env.*' ':(exclude)**/node_modules/**' |
  while IFS= read -r -d '' f; do
    mkdir -p "$WORKTREE_DIR/$(dirname "$f")"
    cp -p "$REPO_ROOT/$f" "$WORKTREE_DIR/$f"
    echo "已帶入 $f"
  done
```

`--others --ignored` 撈的是「沒被 git 追蹤、而且被 ignore」的檔案 —— 正好就是那些只存在本機的 `.env`。已經被追蹤的（`.env.example`、有些專案的 `.env.test`）本來就跟著 worktree 過去了，不會被重複處理，也不會蓋掉。

這是**一次性快照**：之後改了原 repo 的 `.env`，worktree 那份不會跟著變。

這一步一定要在 Step 3 上鎖**之前**做完 —— 鎖上之後就不能再回原 repo 拿東西了。

## Step 2.5：把當前對話複製到 worktree

worktree 開好了，但這段對話的記錄還躺在**原專案**的 session 目錄底下。使用者用新的 VS Code 開 worktree 時，resume 清單是照當前目錄去找的 —— 看不到這段對話，等於換個視窗就得從頭講一次。

跑這支腳本把對話搬一份過去（`<skill 目錄>` 是這個 skill 載入時告訴你的 Base directory）：

```bash
python3 "<skill 目錄>/scripts/sync-session-to-worktree.py" "$WORKTREE_DIR"
```

它會從 `CLAUDE_CODE_SESSION_ID` 找出當前 transcript，算出 worktree 對應的 session 目錄，複製成一個新的 session id（連 sidecar 與 file-history 一起搬），並砍掉檔尾那個還沒有結果的 tool call —— 不砍的話複製過去的對話接不下去。為什麼要這樣做，腳本裡的 docstring 有寫。

你要記得的只有三件事：

- **複製的是執行當下的快照。** 之後又多講了幾輪，worktree 那份不會自己跟上 —— 使用者說要換視窗之前，把同一行再跑一次。
- **重跑是覆蓋同一份**，不會愈積愈多（新 session id 記在 `.worktree-session-meta` 的 `COPIED_SESSION_ID`）。
- **worktree 那份比來源長時，腳本會擋下來。** 那代表使用者已經在新視窗接續講了，那份才新，蓋下去會弄丟。真的要蓋才加 `--force`。

回報給使用者：

```
Worktree 已建立：$WORKTREE_DIR
Temp branch：   $TEMP_BRANCH（從 $ORIGINAL_BRANCH @ ${ORIGINAL_HEAD:0:7} 切出）
已帶入 .env：    <實際複製的檔案清單，例如 backend/.env>
對話已複製：     <腳本印出的 to: 路徑>
                用新的 VS Code 開 $WORKTREE_DIR，就能 resume 這段對話接著做。
從現在開始，這個 session 只能在上面那個 worktree 裡活動。
```

## Step 3：嚴格鎖定 worktree（硬規定）

Step 2 之後，session 必須當作 **`$WORKTREE_DIR` 以外的世界不存在**。

### 絕對禁止 —— 連「快速看一下」都不行

- 用 `Read`、`Edit`、`Write` 去碰路徑會解析到 `$WORKTREE_DIR` 以外的檔案
- `Glob`、`Grep` 的路徑或 pattern 跑出 `$WORKTREE_DIR`（不准用 `../`、不准用其他絕對路徑）
- `cd ..`、`cd /`、`cd ~`、`cd <別的 worktree>`、`pushd <外部>` —— 任何離開 worktree 的 cd
- `cat ../foo`、`ls ..`、`find /Users/... -name`、`head ../something` —— 任何往上層或同層其他目錄看的動作
- `git -C <別的 path>`、`git --git-dir=<別的>`、`git --work-tree=<別的>`
- 開啟其他 worktree、主 checkout、或檔案系統其他地方的檔案
- 「我只是快速看一下」「比對一下」「看看他們那邊長怎樣」—— **即使是 read-only 也禁止**

### 每個 Bash 指令有路徑參數時要做的檢查

```bash
# $target 是 Bash 指令即將碰到的路徑
RESOLVED=$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$target")
case "$RESOLVED" in
  "$WORKTREE_DIR"|"$WORKTREE_DIR"/*) ;;  # ok
  *) echo "BLOCKED：$target 跑出 worktree（$WORKTREE_DIR）" >&2; exit 1 ;;
esac
```

對 `Read` / `Edit` / `Write` / `Glob` / `Grep`：
- 路徑要嘛是 `$WORKTREE_DIR` 底下的相對路徑，要嘛是以 `$WORKTREE_DIR` 開頭的絕對路徑
- 路徑裡**不准出現 `..`**
- 如果想碰的路徑不在 `$WORKTREE_DIR` 底下 → **停下來**。告訴使用者你想做什麼、為什麼，讓使用者決定。

### 唯一的例外：Step 2.5 那支同步腳本

`scripts/sync-session-to-worktree.py` 本身放在 skill 目錄、寫入的是 `~/.claude/projects/`，兩個都在 worktree 外面。要同步對話就照 Step 2.5 原樣再跑一次那一行，**不受上面的路徑檢查限制**。

這不算破例偷看：它碰的是對話記錄，不是任何 repo 的工作檔，讀不到別的 session 改到一半的 code。反過來說，**例外就只有這一支** —— 不要因為「腳本可以出去」就自己延伸成「那我也去 `~/.claude` 翻一下別的東西」。

### 為什麼要這麼嚴

「同一個 repo 而已，有什麼差」—— 差別是：平行 session 代表 worktree 外面那些檔案正被別人改到一半。讀進來就會對不在你分支裡的 code 回報假 bug、把還沒做完的事誤判成完成、讓測試莫名其妙紅掉。硬隔離是唯一的解法。

## Step 4：正常開發 + commit

在 worktree 裡一切照常：要 install 就 install（`npm install` 等等）、改檔、跑測試、commit。所有 commit 都會落在 `$TEMP_BRANCH` 上。

使用者只要說要換到 worktree 的視窗去做（「我開新的 VS Code 了」「你把對話同步一下」之類），就把 Step 2.5 那一行再跑一次，讓那邊拿到的是最新的對話而不是剛開 worktree 時的快照。

## Step 5：完成時 —— 先問再 cherry-pick

任務做完時，**不要**自動整合。先列出新 commit：

```bash
git log --oneline "$ORIGINAL_HEAD..HEAD"
```

然後**逐字**問使用者：

> 完成。在 temp branch `$TEMP_BRANCH` 上有 N 個新 commit：
>
> - `abc1234` ...
> - `def5678` ...
>
> 要 cherry-pick 回 `$ORIGINAL_BRANCH` 嗎？
> - **Yes** → cherry-pick + 砍掉 temp branch + 砍掉 worktree
> - **No**  → 全部丟掉（commits 會消失）
> - **Keep** → 保留 worktree 跟 branch，什麼都不動

**等使用者明確回答**之後再做事。

## Step 6：Cherry-Pick（只有 Yes 才執行）

從**原本的 repo checkout** 跑，不是從 worktree 裡跑：

```bash
cd "$REPO_ROOT"

# 確認原 branch 是乾淨的
if [ -n "$(git status --porcelain)" ]; then
  echo "原 repo 有未提交的改動 —— 停下。請先處理再 cherry-pick。" >&2
  exit 1
fi
git checkout "$ORIGINAL_BRANCH"

git cherry-pick "$ORIGINAL_HEAD..$TEMP_BRANCH"
```

如果 cherry-pick 衝突：
- **停下**。回報衝突。
- **不要**清掉 worktree 或 temp branch —— 它們是復原的依據。
- 讓使用者決定處理（手動解 / `git cherry-pick --abort`）。

cherry-pick 成功 → 進入 Step 7。

## Step 7：清理

只有在以下兩種情況才做清理：
- (a) cherry-pick 成功 ✅
- (b) 使用者選 **No** 並明確確認要丟掉這些 commit

```bash
cd "$REPO_ROOT"
git worktree remove "$WORKTREE_DIR"
git branch -D "$TEMP_BRANCH"
```

複製過去的那份對話**留著不要動**。它躺在 `~/.claude/projects/` 底下，跟著 worktree 路徑命名；worktree 砍掉之後那個目錄會變成孤兒，但裡面是對話本身 —— 如果使用者中途換到新視窗接手，後半段的討論只存在那一份。要不要清掉是使用者的事，不要順手刪。

驗證：

```bash
git worktree list                 # 不該再看到 $WORKTREE_DIR
git branch --list "$TEMP_BRANCH"  # 應該是空
git log --oneline -5              # 有 cherry-pick 的話可以看到新 commit
```

回報：

```
清理完成。
- Worktree 已移除：$WORKTREE_DIR
- Branch 已刪除：  $TEMP_BRANCH
- 目前位於：       $(git branch --show-current)
```

## 快速對照表

| Step | 做什麼 | 為什麼 |
|------|-------|-------|
| 0 | 確認觸發方式：手動呼叫必跑；自主啟用要符合判準並宣告理由 | 隔離有成本，瑣事不開 worktree |
| 1 | 偵測現有 worktree | 不要巢狀 |
| 2 | 從 HEAD 切 `tmp/...` branch + 在 repo root **外**（`<repo>.worktrees/...` sibling）開 worktree，並把 gitignore 掉的 `.env` 依相對路徑帶過去 | 工作區隔離（雙向：別人也讀不到你）；沒有 `.env` 的 worktree 跑不起來 |
| 2.5 | 跑 `scripts/sync-session-to-worktree.py "$WORKTREE_DIR"` | 用新視窗開 worktree 時看得到、接得上這段對話 |
| 3 | 把 session 鎖在 `$WORKTREE_DIR`（只有 2.5 那支腳本例外） | 防止 session 間互相污染 |
| 4 | 正常改 code + commit；要換視窗前重跑 2.5 | 進度推進，對話不停在舊快照 |
| 5 | 整合前先問 | 由使用者把關 |
| 6 | 在原 repo 跑 `git cherry-pick $ORIGINAL_HEAD..$TEMP_BRANCH` | 把工作搬回去 |
| 7 | `git worktree remove` + `git branch -D`（複製的對話留著） | 清乾淨，但不清掉對話記錄 |

## 常見錯誤

### 為瑣碎改動自主啟用（或被拒絕後還一直問）

❌ 使用者只是要改一兩行、或純看 code，你就開 worktree；或使用者這輪已經說過「直接改就好」，你又問一次要不要隔離。
**為什麼錯：** temp branch + 上鎖 + cherry-pick gate 對瑣事是純開銷；被拒絕後重複問是把選擇成本丟回去給使用者。
**怎麼改：** 瑣事直接在當前目錄改。自主啟用只用在 Step 0 的判準（平行 session／使用者表達隔離意圖／大改動），啟用前宣告一句理由，被拒絕後同一輪不再提。

### 任何離開 `$WORKTREE_DIR` 的動作（這是最常犯的一條）

❌ 為了「看 context」讀 parent / sibling dir：`Read /Users/daniel/Heph/ai_family_backend/backend/some-file`（當 worktree 是 repo 外的 `ai_family_backend.worktrees/foo/` 時）
❌ 「cd 上去看一眼 monorepo root」「我就 `ls ..` 一下」
❌ 上鎖之後才發現少了某個沒被 git 追蹤的檔案（憑證、`.env.local`、本機設定），於是 `cp $REPO_ROOT/...` 撈過來
**為什麼錯：** 那些檔案很可能正被另一個 session 改到一半 —— **read-only 也一樣**，讀到中間狀態就會生出假 bug。而且一個 `ls` 會變成一個 `cat`，再變成一個錯誤結論。
**怎麼改：** 需要歷史 context 就用 `git log` / `git show`，**而且要在 worktree 內跑**。該帶的檔案 Step 2 一次帶完；真的漏了就**停下來告訴使用者少了什麼**，讓他決定要不要補。

### 用 `origin/main` 或 `main` 開 worktree 而不是 HEAD

❌ `git worktree add ... -b tmp/foo origin/main`
**為什麼錯：** 使用者明確要求從 HEAD 切，這樣會丟掉當前分支上已 commit 的工作。
**怎麼改：** 一定要寫 `... HEAD`。

### 沒問就自動 cherry-pick

❌ 做完直接跑 `git cherry-pick`。
**為什麼錯：** 「先問再整合」是這個流程的核心。
**怎麼改：** 每次都列 commit + 等使用者選 Yes / No / Keep。

### Cherry-pick 還沒成功就清掉 worktree

❌ 先 `git worktree remove`，然後才發現 cherry-pick 有衝突。
**為什麼錯：** 復原依據沒了，工作直接消失。
**怎麼改：** 清理是**最後一步**，只在 cherry-pick 成功或使用者明確選擇丟掉之後才做。

### 把 worktree 開在 repo root 裡面（`${REPO_ROOT}/.worktrees/...`）

❌ 開在 repo 內。別的 session 從 repo root 掃描（find / cat / 絕對路徑 Read / 非 gitignore-aware grep）會走進來讀到你改到一半的檔 —— 隔離只擋了「你讀別人」，沒擋「別人讀你」；`.gitignore` 也救不了（擋不了那些工具）。
**怎麼改：** Step 2 把 worktree 開在 repo root **外面**的 sibling（`${REPO_ROOT}.worktrees/...`）。任何掃 repo root 的 session 都到不了。

### 只複製 repo root 的 `.env`

❌ `cp "$REPO_ROOT/.env" "$WORKTREE_DIR/"`
**為什麼錯：** monorepo 的 `.env` 常常根本不在根目錄，而是在 `backend/`、`frontend/` 底下各一份。只抓根目錄的結果就是複製了零個檔案，然後 worktree 裡的 app 照樣起不來。
**怎麼改：** 用 Step 2 那段 `git ls-files --others --ignored`，它會把每一份都依相對路徑放到對的位置。

### 自己手動 `cp` transcript 過去，而不是跑那支腳本

❌ `cp ~/.claude/projects/<原專案>/<sid>.jsonl ~/.claude/projects/<worktree>/`
**為什麼錯：** 手動複製會漏掉三件事（懸空的 tool call、session id 互踩、sidecar 沒跟著走），結果就是那份對話 resume 不起來。
**怎麼改：** 跑 Step 2.5 的 `scripts/sync-session-to-worktree.py`。

### 複製完就當作兩邊會自動同步

❌ Step 2.5 跑完，之後又聊了十輪，直接叫使用者去開新視窗。
**為什麼錯：** 複製的是那一刻的快照，後面十輪不在裡面 —— 使用者換過去只會看到半截。
**怎麼改：** 使用者要換視窗之前，把 Step 2.5 那一行再跑一次。

## Red Flags —— 想到下面這些話就立刻停下

下面任何一個念頭出現，代表你正準備違反規則：

- 「改一行也開個 worktree 好了，反正比較安全」
- 「他剛說不用隔離，我再確認一次好了」
- 「快速看一下 parent 目錄就好」
- 「我 grep 整個 repo 找 reference」
- 「讀另一個 worktree 比對一下」
- 「cd 上去看一眼 monorepo root」
- 「只看一下不會怎樣，read-only 而已」
- 「worktree 裡起不來，我回原 repo 拿一下 `.env` 就好」
- 「使用者明顯就想要 cherry-pick，直接做」
- 「先清乾淨再來看 merge 有沒有成功」

**這些念頭全部都代表：違反隔離規則 / 跳過確認 gate。停下，重讀 Step 3 或 Step 5，不要自己找理由繞過去。**
