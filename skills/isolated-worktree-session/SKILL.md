---
name: isolated-worktree-session
description: **只在使用者明確同意後才啟用**。不要自動觸發。當使用者要修改 code 時，先用一句話詢問「要不要用 isolated-worktree-session？（從 HEAD 切 temp branch + worktree + 嚴格隔離 + 結束時詢問是否 cherry-pick）」；只有使用者明確說 Yes / 要 / 啟用 之後，才真正執行此 skill 的步驟。使用者沒同意就直接在當前目錄改。
---

# Isolated Worktree Session（隔離工作流）

## 總覽

從目前 HEAD 切一條 **temp branch**，並為它開一個 **worktree**。整個 session 只在這個 worktree 裡活動 —— 不讀、不寫、不 grep、不 glob、不 cd 到 worktree 以外的任何地方。做完之後，主動詢問使用者要不要把新 commit cherry-pick 回原 branch，然後刪掉 temp branch 與 worktree。

**核心原則：** 目錄硬隔離。之前有 session 把隔壁目錄（另一個平行 session 改到一半的檔案）讀進來當作參考，結果回報了一堆「假 bug」。所以一旦啟用，這裡不是建議，是硬規定。

## Step 0：先取得使用者同意

**這個 skill 不會自動觸發。** 當使用者要求改 code 時，必須先用一句話詢問：

> 要不要用 **isolated-worktree-session** 隔離這次改動？（會從 HEAD 切 temp branch + 開 worktree，結束時問你要不要 cherry-pick 回來）

- 使用者明確同意（Yes / 要 / 啟用 / 好 / 開）→ 繼續 Step 1
- 使用者拒絕 / 沒回應 / 說「直接改就好」→ **不要用這個 skill**，直接在當前目錄改 code，整個 skill 都不用跑
- 使用者沒講要不要，但要求快速的小修正（typo、改 log 等）→ 還是要問一次，不要自己決定

確認啟用後，宣告：「啟用 isolated-worktree-session：先開 temp branch + worktree 再動 code。」

## 什麼時候用

**前提：使用者在 Step 0 已經明確同意。**

適合提議啟用的情境：
- 任何會改 code / schema / migration / config / 文件的任務
- 同一個 repo 有多個 session 在跑時
- 使用者提到「平行作業」「另一個 session」「隔離一下」

**不適合提議的情境（這時連問都不用問，直接做）：**
- 純看 code、純研究、完全不會碰 repo 狀態的調查
- 已經在另一個 linked worktree 裡（Step 1 會偵測；如果已經在裡面，仍然套用 Step 3 的鎖定規則 —— 但仍要先問使用者要不要繼續沿用隔離規則）

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
WORKTREE_DIR="${REPO_ROOT}/.worktrees/${SAFE_ORIG}-${SLUG}-${TIMESTAMP}"

# 確認 .worktrees/ 已加入 .gitignore，沒有就補上並 commit
if ! git -C "$REPO_ROOT" check-ignore -q .worktrees 2>/dev/null; then
  echo ".worktrees/" >> "$REPO_ROOT/.gitignore"
  git -C "$REPO_ROOT" add .gitignore
  git -C "$REPO_ROOT" commit -m "chore: ignore .worktrees"
fi

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

回報給使用者：

```
Worktree 已建立：$WORKTREE_DIR
Temp branch：   $TEMP_BRANCH（從 $ORIGINAL_BRANCH @ ${ORIGINAL_HEAD:0:7} 切出）
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

### 為什麼要這麼嚴

同一個 repo 同時有兩個 session 在跑，代表 parent dir / sibling dir 裡都是「另一個 agent 改到一半」的檔案。讀進來會發生：
- 對「不在你工作分支裡」的 code 回報假 bug
- 對「其實還沒做完」的事誤判已經完成
- 測試莫名失敗，因為混到不相容的狀態

硬隔離是唯一的解法。

## Step 4：正常開發 + commit

在 worktree 裡一切照常：要 install 就 install（`npm install` 等等）、改檔、跑測試、commit。所有 commit 都會落在 `$TEMP_BRANCH` 上。

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
| 1 | 偵測現有 worktree | 不要巢狀 |
| 2 | 從 HEAD 切 `tmp/...` branch + 在 `.worktrees/...` 開 worktree | 工作區隔離 |
| 3 | 把 session 鎖在 `$WORKTREE_DIR` | 防止 session 間互相污染 |
| 4 | 正常改 code + commit | 進度推進 |
| 5 | 整合前先問 | 由使用者把關 |
| 6 | 在原 repo 跑 `git cherry-pick $ORIGINAL_HEAD..$TEMP_BRANCH` | 把工作搬回去 |
| 7 | `git worktree remove` + `git branch -D` | 清乾淨 |

## 常見錯誤

### 為了「看 context」偷讀 parent / sibling dir

❌ `Read /Users/daniel/Heph/ai_family_backend/backend/some-file`（當 WORKTREE_DIR 是 `.worktrees/foo/` 時）
**為什麼錯：** 那個檔案可能正被另一個 session 改到一半。
**怎麼改：** 只讀 `$WORKTREE_DIR` 裡的檔案。需要歷史 context 就用 `git log` / `git show`，**而且要在 worktree 內跑**。

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

### 忘了把 `.worktrees/` 加進 `.gitignore`

❌ Worktree 內容跑進主 checkout 的 `git status`。
**怎麼改：** Step 2 已經內建檢查 + 自動補 .gitignore。

### 「我只是 cd 上去一層看看 monorepo root」

❌ 任何離開 `$WORKTREE_DIR` 的 cd。
**為什麼錯：** 直接違反整個 skill 的前提 —— 這就是使用者反映的那個 bug。
**怎麼改：** 不要做。真的需要外面的東西就**停下來問使用者**。

## Red Flags —— 想到下面這些話就立刻停下

下面任何一個念頭出現，代表你正準備違反規則：

- 「快速看一下 parent 目錄就好」
- 「我 grep 整個 repo 找 reference」
- 「讀另一個 worktree 比對一下」
- 「cd 上去看一眼 monorepo root」
- 「只看一下不會怎樣，read-only 而已」
- 「使用者明顯就想要 cherry-pick，直接做」
- 「先清乾淨再來看 merge 有沒有成功」

**這些念頭全部都代表：違反隔離規則 / 跳過確認 gate。停下，重讀 Step 3 或 Step 5。**

## 偷雞理由 vs 真相

| 偷雞理由 | 真相 |
|---------|------|
| 「Read-only 沒差啦，我又沒改」 | 讀到別的 session 的中間狀態會產生假 bug。**禁止。** |
| 「我要看 parent dir 才能理解」 | 那就問使用者。不要偷看。 |
| 「使用者明顯就想 cherry-pick」 | 他要的是 gate。每次都要問。 |
| 「先清一清比較整齊」 | 在 cherry-pick 前清理 = 工作消失。清理是**最後一步**。 |
| 「同一個 repo 啦有什麼差」 | 平行 session 代表你 worktree 外面的檔案正被別人改。差別就是使用者抱怨的那個 bug。 |
| 「我就 `ls ..` 一下」 | 一個 `ls` 變成一個 `cat`，變成一個錯誤結論。從一開始就不要。 |
