---
name: debug-patches
description: 把「只在本機／測試環境才要有」的 debug 改動（例如印出 req/res body）套進當前 repo，並單獨包成一個 temp commit，測完可以整包丟掉。也負責維護這份 debug 改動清單：使用者說「再加一個測試用改動」「記下這個 debug patch」時，把新的一筆寫進 catalog。觸發：套 debug 改動、加測試用的 log、temp commit、debug patch、把 debug commit 拿掉。
user-invocable: true
disable-model-invocation: true
argument-hint: "[留空＝套用全部；或 patch ID；或 remove；或「新增：<描述>」]"
---

# Debug Patches

一組「平常不該進 codebase、但 debug 時很想要」的改動。呼叫本 skill 會把它們套進當前 repo
並**單獨包成一個 temp commit**——跟正在做的功能改動分開，測完 drop 掉即可，不會混進 MR。

**這些改動一律不得 merge 進 stage / main。** 多數會把 request body、response body 這類含
密碼 / token / PII 的東西寫進 log，只能活在本機或自己的 debug 分支。

---

## 模式判斷

| 使用者輸入 | 模式 |
|---|---|
| 無參數、或指定 patch ID | **A. 套用**（預設） |
| `remove` / 「拿掉」/「還原」/「要 push 了」 | **B. 移除** |
| 「新增：…」/「再加一個…」/ 描述一個新的 debug 改動 | **C. 加進 catalog** |

---

## 模式 A：套用並包成 temp commit

1. **選 patch**：讀下方 Catalog。無參數 → 取所有「適用專案」符合當前 repo 的 patch；有指定 ID → 只取該筆。
   不符合當前 repo 的直接略過，並在最後回報時說明略過了哪些、為什麼。
2. **檢查衝突**（不可略過）：
   - `git log --oneline -20` 找有沒有既存的 `temp:` commit。有 → 先問使用者要疊上去還是先移除舊的。
   - `git status --short` 看 patch 會動到的檔案有沒有**未 commit 的既有改動**。有 → **停下來問**，不要硬套：
     混在一起之後 temp commit 就無法乾淨 drop。
3. **套用**：照 patch 檔的「套用方式」改。**以現行檔案為準做局部改動，不要整檔覆蓋**——patch 檔裡的
   參考實作是寫下當時的樣子，目標檔案可能已經演進。所有新增的行都要帶 `[temp-debug]` 標記註解，
   移除時才 grep 得到。
4. **驗證**：跑專案自己的型別檢查 / lint（例如 `bunx tsc --noEmit`）確認沒把 build 弄壞。跑不動就說明原因，別默默跳過。
5. **commit**：`git add` **逐一列出**改到的檔案（不用 `git add -A` / `git add .`），然後：

   ```
   temp: debug patches — <patch ID 清單>（勿 merge）
   ```

   commit 訊息**不得**含任何 AI attribution（不加 `Co-Authored-By`、不加 `🤖 Generated with`）。
6. **回報**：commit SHA、套了哪幾筆、略過哪幾筆與原因，並提醒 push 前用 `remove` 模式清掉。

## 模式 B：移除 temp commit

先 `git log --oneline -20` 找到那個 `temp:` commit，再依它的位置選做法：

- **它就是 HEAD**：`git reset --mixed HEAD~1`，接著只對 patch 動到的那幾個檔案 `git checkout -- <檔案>`。
  不要用 `git reset --hard`——會一併吃掉其他未 commit 的工作。
- **它後面還有 commit**：`git rebase --onto <temp-sha>^ <temp-sha> HEAD` 把它抽掉。
  後續 commit 有動到同一個檔案時會衝突，解法一律是留「沒有 `[temp-debug]` 標記」的那一版。

收尾：`git grep -n "\[temp-debug\]"` 確認沒有殘留。

## 模式 C：把新的 debug 改動加進 catalog

1. 問清楚（不確定才問，答案顯然就別問）：要 debug 什麼、動哪些檔案、適用哪個專案。
2. **先實際套一次並驗證**（型別檢查 / 實跑），確定寫進 catalog 的參考實作是真的能動的，不是憑印象寫的。
3. 在 `patches/` 新增一個檔，格式照 [patches/http-req-res-body.md](patches/http-req-res-body.md)。
4. 把新的一筆補進下方 Catalog 表格。
5. 驗證用的改動記得還原（除非使用者要直接留著走模式 A 的 commit 流程）。

---

## Catalog

| ID | 內容 | 適用專案 |
|---|---|---|
| [http-req-res-body](patches/http-req-res-body.md) | 每筆 HTTP request 完成時，把 request body 與 response body 一起印進 access log | `ai_family_backend` / `backend`（Express + pino-http） |
