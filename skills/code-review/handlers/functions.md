# 函式與控制流 Functions & Control Flow Code Review 規範

> 適用所有檔案，聚焦「單一 function 的簽章形狀與內部控制流」。
> 「function 內抽象層級一致 / Extract Method / 命名前綴」見 `readability.md`；「command 與 query 混用」的判定與重構歸 `single-responsibility.md` 的 CQS；「依 type 分派散落多檔要不要收斂 Strategy」的擴充軸歸 `extensibility.md`。本檔管「單一 function 內」的控制流臃腫，三者互引避免重複。

## 核心原則

1. **Small functions, few arguments — Robert C. Martin《Clean Code》ch.3**
   參數越少越好（0–3）；三個以上通常代表缺一個聚合概念或該拆。

2. **Guard Clause / Decompose Conditional — Martin Fowler《Refactoring》**
   先用 early return 擋掉錯誤與邊界，讓 happy path 留在最外層、不被層層 if 埋住；複雜布林條件抽成有意圖名稱的 predicate。

3. **No flag arguments — Clean Code**
   用布林參數切兩條執行路徑，等於一個 function 做兩件事；拆成兩個具名 function。

## 偵測訊號（code smells）

> 逐條使用 TodoWrite 工具標記檢查進度。

- [ ] **參數過多（>3）**：function 帶 4 個以上位置參數（尤其一串同型的字串／布林），呼叫端要數順序——收斂成參數物件（Parameter Object）或 value type
- [ ] **Flag argument**：`publish(id, isDraft)`、`build(payload, dryRun)` 用布林切兩條路徑——拆成兩個具名 function（其「控制耦合」本質見 `coupling-cohesion.md`）
- [ ] **Output argument**：傳入物件被函式內部 mutate 當回傳管道，而非 return 新值（隱藏 side effect）
- [ ] **深層巢狀 / 缺 guard clause**：`if{ if{ if{} } }` 超過 2–3 層、happy path 埋在最內層——用 early return 攤平
- [ ] **複雜條件未抽 named predicate**：`if (u.status == ACTIVE && !u.muted && slots > 0)`——抽成 `isEligibleForPublish(u)`（Decompose Conditional）
- [ ] **單一 function 內的長 switch / if-else 階梯依 type 分派**：對 enum/kind 值在**同一 function**內攤開多分支且臃腫——考慮 map 分派或下沉（跨多檔重複同組分派則歸 `extensibility.md` 的 Strategy）
- [ ] **負向條件繞路**：`if (!isNotReady)` 雙重否定、或用否定條件當主分支——改正向命名
- [ ] **query function 藏 side effect**：命名像讀取（`getX`/`findX`）卻順手寫 DB / 改狀態——判定與重構歸 `single-responsibility.md` 的 CQS，本檔僅作為偵測入口

## 重構手法對照

| 訊號 | 解法 |
|------|------|
| 參數過多 | Introduce Parameter Object（參數物件 / value type）；或該拆 function |
| Flag argument | Replace Parameter with Explicit Methods（`publishDraft` / `publishLive`） |
| Output argument | 改 return 新值，別 mutate 傳入物件 |
| 深巢狀 | Replace Nested Conditional with Guard Clauses（early return 攤平） |
| 複雜條件 | Decompose Conditional，抽 `is/has` 前綴 predicate（命名規範見 `readability.md`） |
| 單一 function 內長 switch | map 分派 / 下沉到對應物件；跨檔重複才升 Strategy（`extensibility.md`） |
| 負向條件 | 反轉成正向命名的 predicate |

## 實務拿捏

- **別為攤平而過度拆**：guard clause 是攤平巢狀，不是把每個 if 抽成 private method（過度拆分見 `readability.md`）。
- 參數物件不是萬靈丹：2–3 個語意清楚的位置參數比硬包一個參數物件更好讀；參數多到要數順序、或同型連續才收斂。

## 建議格式

```
- **[Functions]** {檔案}:{行數範圍}
  - 問題：{參數過多 / flag / 深巢狀 / 複雜條件…，引用訊號}
  - 原則：{Small Functions / Guard Clause / Decompose Conditional / No Flag Argument}
  - 建議：{具體重構，如抽哪個 predicate、拆成哪兩個 method}
```
