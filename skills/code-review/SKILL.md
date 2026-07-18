---
name: code-review
description: 逐項 review 一份改動——本地 branch diff、GitHub PR、GitLab MR、或指定路徑皆可。先讀懂改動目的，再把 12 個面向（可讀性 / 註解 / DRY / 單一職責 / 耦合內聚 / 擴充性 / 函式控制流 / 型別與資料形狀 / 錯誤處理 / API 健壯性 / 安全性(OWASP)）各派一個 subagent 逐項對 checklist 檢查、critic 覆核、禁空證據 PASS。當使用者要 code review、審 PR / MR / diff、檢查設計 / 重複 / 安全 / clean code 時使用。
user-invocable: true
argument-hint: "[PR/MR URL、branch 名、或路徑；留空＝當前 branch diff]"
---

# Code Review

把「review 一次改動」拆成 12 個獨立面向，每個面向一份 checklist（`handlers/*.md`），**各派一個 subagent 逐項檢查**，再各派一個 critic 覆核。與語言、框架、平台無關。

> **為什麼要 fan-out 而不是自己一次讀完**：逐項覆蓋率若靠單一 agent 自律去記住 12 份 checklist 的每一條，會踩「指令越多、整批遵守率越低」（curse of instructions，整批遵守率 ≈ 單條^N），結果就是「檢查幾項就 pass」。一個 handler 一個 subagent、每個 subagent 只扛一份 checklist，覆蓋率才守得住。

## Handlers

| Handler | 面向 | 類別 |
|---------|------|------|
| `readability.md` | 命名、Composed Method、認知負荷 | readability |
| `comments.md` | 註解只講「為什麼」、過時／複述／死碼 | readability |
| `functions.md` | 函式長度、參數、控制流、巢狀深度 | readability |
| `dry.md` | 重複的邏輯／知識，以及**錯誤的** DRY | maintainability |
| `single-responsibility.md` | 單一職責、變更理由 | maintainability |
| `extensibility.md` | YAGNI、過度抽象、預留無人用的擴充點 | maintainability |
| `coupling-cohesion.md` | 模組邊界、依賴方向、內聚度 | architecture |
| `types-and-data.md` | 型別安全、資料形狀、非法狀態可表達性 | correctness-perf |
| `error-handling.md` | 錯誤傳播、吞例外、失敗路徑 | correctness-perf |
| `review-lessons.md` | 跨模組設計／正確性的累積教訓 | correctness-perf |
| `api-robustness.md` | 效能 / Bug / 併發（**逐入口端到端追鏈**） | correctness-perf |
| `security.md` | 授權 / injection / 資料外洩（**逐入口端到端追鏈**，OWASP） | correctness-perf |

前 10 支是**跨切面**：對每個受審檔案都適用。

`api-robustness` 與 `security` 是**逐入口**：以單一對外入口為單位，沿整條資料流追到底，不是「一個檔一條」。所謂入口指任何外部輸入的進入點——HTTP endpoint、RPC method、CLI 子命令、訊息佇列 consumer、排程任務、webhook 皆是。

> 類別存在的目的：讓可讀性 / 寫法類問題成為**可數的獨立一桶**，不被 logic/perf 淹沒而在 triage 被無聲丟掉（見 Step 6）。

## 執行流程

### Step 1：取得 diff

依使用者給的參數判斷來源。四種都支援：

**A. 沒給參數 / 給 branch 名 → 本地 diff**

```bash
git rev-parse --abbrev-ref @{upstream}          # 先查基準，不要假設叫 main/dev
git diff <base>...HEAD                          # 三個點：只看這條分支加了什麼
git diff HEAD                                   # 若有未提交改動，一併納入
```

> range diff 是空的、或工作區有未提交改動時，**務必**把 `git diff HEAD` 納入範圍——review 常常在 commit 之前跑。

**B. GitHub PR URL / PR 編號**

```bash
gh pr view <n> --json title,body,state,baseRefName,headRefName
gh pr diff <n>
```

**C. GitLab MR URL**

從 URL 拆出三個欄位：**host**（`scheme://` 後到第一個 `/` 前，含 port）、**project path**（host 後到 `/-/merge_requests/` 前）、**MR iid**（最後的數字）。

```bash
GITLAB_HOST=<host> glab mr view <iid> --repo <project path>
GITLAB_HOST=<host> glab mr diff <iid> --repo <project path>    # 不要加 --raw，會 404
```

> `glab` 必須帶 `GITLAB_HOST=` 前綴——git remote 的 port 與 API 的 port 常常不同，不帶會失敗。若回 `Unauthenticated` / `404`，先用 `glab auth status` 確認登入的 host。

**D. 給了檔案或目錄路徑 → 只審那些路徑**，範圍限縮但流程相同。

另外決定兩件事：

- **方向**：使用者若說「這次只看效能 / 只看可讀性」→ 只跑對應類別的 handler；沒指定＝全跑。
- **位置**：受審分支在別的 worktree 時，所有 git 指令走 `git -C <worktree>`（`git worktree list` 可查）。

### Step 2：先讀懂改動目的

**進行任何 review 之前**，先弄清楚這次改動「想達成什麼」：

- PR / MR：讀 title 與 description
- 本地 diff：讀 `git log <base>..HEAD` 的 commit 訊息
- 都沒有：直接問使用者

要抓出三件事：目標 / 動機是什麼？宣稱的 scope 與「不在 scope」為何？有沒有列出 breaking changes、資料遷移、預期數值、測試計畫等驗收線索？

接著用「這個目的」當審查主軸：

- **目的對齊**：每段 diff 是否真的服務於宣稱的目的？有無無關的夾帶改動、或目的要求卻漏改的地方？
- **目的完整性**：要達成這個目的，diff 是否涵蓋所有必要的檔案 / 邊界情況（對照 description 的 breaking changes、遷移、數值逐項核對）？
- **目的副作用**：是否在達成目的的同時破壞既有行為或引入新風險？**即使宣稱某段「不在 scope」，若改動讓既有問題更容易被觸發，仍要點出。**

這層「目的導向」判斷與 handler checklist **並列輸出**，不是二選一。

### Step 3：估成本 + 確認（成本閘，必做）

- 跨切面：**檔數 × 10 個 handler** 個 review pair（review + critic）。
- 逐入口：先枚舉這次**實際改到 / 新增的對外入口**，每個入口 **+2 條**追鏈 pair（api-robustness 一條、security 一條）。
- 一個 pair 約數萬 token 量級。

**一律先把「將審的檔清單 + handler 數 + 入口鏈數 + 估計」報給使用者並取得確認，再 fan-out**——不要默默啟動。估計偏高時建議縮範圍（限類別、限路徑、限入口數），並**明講被砍掉的是什麼**，不要無聲截斷。

### Step 4：Fan-out

每個 (檔案 × handler) 派一個 subagent，要求它：

1. 讀 `handlers/<name>.md` 的完整 checklist
2. **逐條**輸出 verdict：`PASS` / `FAIL` / `UNSURE`
3. 每條都要帶 `file:line` 證據——**舉不出行號的 PASS 一律改判 `UNSURE`，禁空證據 PASS**
4. 只針對「這次 diff 改動到的內容」評斷，不要 review 未變動的既有程式碼（除非變動破壞了它）

每個 review subagent 完成後，再派一個 **critic** subagent 覆核兩件事：checklist 是否逐條都有 verdict（覆蓋率）、`PASS` 的證據是否真的成立（防止空過）。

> diff 的 hunk 標頭 `@@ -a,b +c,d @@` 提供新檔的起始行號，據此推算每個問題在新檔的實際行號範圍。行號以**新檔（`+` 側）**為準；若問題在被刪除的行，註明是舊檔行號。

> 若專案自己有 deterministic workflow 引擎（用 pipeline + schema 強制每個 handler 回傳 N 列 verdict），優先用它——把覆蓋率變成**程式強制**比靠模型自律可靠得多。本 skill 的 subagent fan-out 是不依賴專案設施的通用版，覆蓋率靠 critic 把關。

### Step 5：輸出

問題的寫法**不在本檔重複**，以 `review-finding-format` skill 為唯一出處：**輸出前先讀取它**並照辦（位置 / 問題 / 🗣️ 白話情境 / 建議解法）。這樣 review 輸出與後續用 `pr-inline-comment` 發出的留言格式天然一致，發留言時內文可直接沿用。

問題清單**先依類別分節**（readability / maintainability 各自成獨立小節，不與 correctness-perf 混列），節內再依檔分組。最後給簡短小結：共幾個問題、類別分布、是否建議合併。

改動規模大時另外落檔：用 `date +%Y-%m-%d-%H-%M-%S` 取時間戳寫入 `docs/code-review/<timestamp>.review.md`（目錄不存在就建，並確認它有被 gitignore——這是本機產物），內容另含**覆蓋率表**（每列 file / handler / 應檢查條數 vs 實際涵蓋 / 缺漏數）與**入口清單**。

CLI 摘要要**逐類別報數**，不要只報總數或只挑 correctness-perf 講。

### Step 6：逐一確認

**預設只出清單、不直接改 code**——修不修由作者決定。使用者明確要求修正時，才對每個 `FAIL` / `UNSURE` 逐項確認修改方向後動手；`PASS` 不需逐項回報。

**可讀性 / 寫法類與 correctness-perf 同等浮出（硬性）**：`readability` / `maintainability` 類的 `FAIL` / `UNSURE` **不得因「嚴重度低、不影響行為」就在 triage 階段被自行過濾或壓成一句帶過**。

- 逐類別各成獨立小節呈現，每條都帶 `file:line` 與具體改法，讓作者自己決定取捨——**篩選權在作者、不在 triage**。
- 可讀性條目多時可**批次**呈現（一個小節列完）而非逐則洗版，但**不可略過**；要略過（例如純主觀偏好）必須明講「哪幾條、為什麼判定不值得」，不能無聲消失。
- 對外發布留言時比照：logic/perf 與可讀性都發，可讀性用同一輪批次發，不因類別而跳過。

## 注意事項

- 不確定一律標 `UNSURE`（「待確認」），不直接判違規。
- Handler checklist 是**唯一出處**，不要在對話裡憑記憶重述規則——每個 subagent 都必須實際讀取自己那份 handler 檔。
- 若 diff 過大，分批處理，但最終彙整成單一份完整清單。**分批時要講清楚哪些檔還沒審**，不要讓截斷看起來像「全部審完了」。
- 專案若自己有 `.claude/skills/code-review/handlers/`，**優先用專案的**（更貼合該專案的架構慣例與分層命名），本 skill 的通用 handler 作為補充。
