---
name: readability-review
description: |
  從「人類讀者第一次閱讀」的視角檢查程式碼可讀性，產出帶位置、卡點類型、觸發 heuristic 與重寫建議的 finding 報告。理論基礎是 Ousterhout《A Philosophy of Software Design》的 cognitive load 與 information locality，明確反對 Clean Code「function 越短越好、註解是失敗」的教條。

  當使用者說「readability review」「可讀性 review」「冷讀一遍」「這段好不好讀」「從讀者視角看」「以讀者角度檢查」「human readability」「人類可讀性」「新人看得懂嗎」「接手的人讀起來如何」「這段好不好懂」「幫我用人的角度讀」時必須觸發。即使使用者沒明確說「可讀性」三個字，只要意圖是「這段別人讀起來順不順」就用此 skill。

  跟一般 code review 的關鍵差異：一般 code review 找 bug / 架構 / 安全 / 效能問題，本 skill **只**找「讀者腦中的摩擦力」（停頓、跳轉、意外），並用 SonarQube cognitive complexity 與 seeinglogic 的視覺 pattern 作為可觀察訊號。若使用者要的是 bug / 架構 / 安全 / 效能檢查，不要觸發本 skill。

  輸出語言：繁體中文。
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Read Code As Human

從「人類讀者第一次閱讀」的視角檢查 code，找出讀者腦中的摩擦力。

## 何時用 / 何時不用

**用本 skill 的情境**
- 想知道一段 code 是否好讀、新人接手會不會卡
- 想列出「讀這段時會在哪裡停頓、跳去哪裡、會誤解什麼」
- PR review 時想專門看可讀性向度

**不用本 skill 的情境**
- 找 bug、邊界條件、race condition → 用 `code-review-excellence`
- 檢查分層架構 / 依賴方向 / API 規範 → 用專案的 `code-review`
- 找重複 code、效能問題、直接動手修 → 用 `simplify`
- 安全審查 → 用 `security-review`

## 理論立場：Ousterhout 派

本 skill 採 John Ousterhout《A Philosophy of Software Design》立場，明確反對 Robert Martin《Clean Code》的部分教條。Why：Martin 自己的 prime generator 範例在拆細後效能掉 3-4 倍，後來又自己合回去，實證證實 Ousterhout 的「information locality」優先於「function 越短越好」。

| 議題 | Clean Code (Martin) | A Philosophy of Software Design (Ousterhout) | 本 skill 採用 |
|---|---|---|---|
| function 長度 | 2-4 行最好 | 看「讀懂要跳幾處」，太碎反而 entanglement | Ousterhout：行數是參考，跳轉次數才是主訊號 |
| 註解 | 是 expressiveness 失敗 | 解釋 WHY 不可取代 | Ousterhout：缺 WHY 算 finding；只描述 WHAT 的註解才是 noise |
| 過度抽象 | 切越細越好 | "shallow methods" 增加負擔 | Ousterhout：只被叫一次又跟原處糾纏的抽出 = 反模式 |

**核心定義**：可讀性 = cognitive load（讀者腦中要同時 hold 的資訊量）+ information locality（相關邏輯是否放在一起，讀者不用跳）。

## 強制流程：兩遍掃描

### Pass 1 — Cold Read

從上到下逐段讀目標 code，假裝你是第一次看這個 codebase 的新人。每段問自己「我有看懂嗎？卡在哪？」，記錄三類事件：

1. **停頓**：需要回頭重讀的行（讀完一次不懂，要再讀一次才接得起來）
2. **跳轉**：為理解某個 identifier 必須跳去別檔/別方法看（例如不知道 `process()` 有沒有 side effect）
3. **意外**：行為跟名字 / 結構 / 周圍 code 暗示的不一致（surprise）

每個事件記下：發生在哪一行、為什麼卡、要看到什麼資訊才能解開。

### Pass 2 — Heuristic Check

用下表的可觀察訊號交叉比對 Pass 1 的事件。**只有同時滿足「Pass 1 有事件」且「Pass 2 有訊號」才寫成 finding**——單純命中 heuristic 但讀起來其實沒卡，就不要報。

| 維度 | 可觀察訊號 |
|---|---|
| 命名 | 識別字 < 3 字元（i, j 等迴圈變數除外）、shadowing、視覺易混（i/l/1, O/0） |
| 巢狀 | 縮排深度 > 2 |
| function 形狀 | 行數 > 50 **或** 要跳到 ≥ 3 個其他方法才懂 |
| 條件 | 單一條件 > 2 行 **或** 同一條件內混用 `&&` 和 `\|\|` |
| chain | function chain > 3 步且無中間命名變數 |
| 變數生命週期 | 跨度 > 20 行；宣告離首次使用太遠 |
| 註解 | 只解釋 WHAT 而非 WHY；或缺了讀者無法自行推出的 WHY |
| 新奇性 | 用了 codebase 罕見的 idiom / syntax（讀者沒看過要查） |
| 一致性 | 跟周圍 code 風格斷裂（命名、結構、錯誤處理方式） |

「新奇性」與「一致性」要先用 Grep 抽樣 codebase 周圍幾個檔，確認真的是這個 codebase 的少數案例，才算 finding。

## Finding 輸出格式

每個 finding 必須有以下 5 欄，缺一不可：

```
- 位置：file.ts:42-58
- 卡點類型：停頓 / 跳轉 / 意外
- 第一次讀會發生什麼：[具體描述讀者腦內狀態，要寫得像旁白]
- 觸發的 heuristic：[Pass 2 表格中的哪一條，加上具體訊號值]
- 重寫建議：[具體的 code 或結構改法，不要只說「應該重構」]
```

報告開頭給總結：「本次冷讀共記錄 N 個事件，其中 M 個觸發 heuristic 成為 finding；K 個只是停頓但沒命中訊號，標為 fyi」。

## 自我節制規則（防退化關鍵）

這四條是 skill 的紅線。每寫一個 finding 前先過一遍。

### 1. 每個 finding 必須綁到可觀察訊號

禁止停在「這名字不好」「這段有點亂」這種品味話。Why：可讀性主觀，不綁訊號就會退化成審美。每個 finding 都要能講出「讀者要跳 N 次」「行數 X > 50」「跨度 Y > 20 行」「縮排 Z > 2」這種可數的東西。

**範例**
- ❌ 「`process` 這名字太籠統」
- ✅ 「`process` 是 47:5；要理解它有沒有 side effect 需跳去 `service.ts:120`、`event-emitter.ts:88`、`db.ts:34` 三處——觸發『function 形狀』的『跳轉 ≥ 3 個方法』訊號」

### 2. 禁止以「應該更短」為唯一理由建議拆 function

Why：Ousterhout 警告，拆出來只被叫一次又跟原處 entangled 的 shallow method，反而增加讀者負擔（要在多處之間跳）。

要建議拆 function，**必須證明拆完後 Pass 1 的跳轉次數會減少**，例如「拆出 `validatePayload` 後，原 function 從 80 行降到 30 行，且新 function 有清楚的單一輸入/輸出，讀主流程的人不用再讀 validation 細節」。

不能只說「這 function 太長」就要求拆。

### 3. 禁止建議刪掉解釋 WHY 的註解

Why：Clean Code 教派最大的歷史錯誤是把所有註解視為失敗，導致大量「為什麼用這個 magic number / 這個 workaround / 這個非直覺順序」的知識永久遺失。

可以建議刪掉的註解：純粹覆述 code 在做什麼的（例如 `// increment i` 前面就是 `i++`）。
**不可以**建議刪掉的註解：解釋為什麼這樣做、為什麼不用看似更簡單的方法、外部約束（API 限制、相容性要求、bug workaround）的。

不確定一條註解是 WHAT 還是 WHY 時，預設保留。

### 4. 語境優先

若該段 code 跟周圍 code 的風格 / 命名 / 結構是一致的，即使違反某條 heuristic，也降級為 "fyi" 而非 finding。Why：在已建立慣例的 codebase 裡，一致性對讀者來說比「絕對更好」更重要——讀者已經建立的 mental model 比 skill 的 heuristic 更值錢。

例如：整個 codebase 都用 2 字元縮寫的 model 變數（`u` for user, `o` for order），新檔案也這樣寫時，「識別字 < 3 字元」降為 fyi。

## 範例：好的 finding vs 壞的 finding

### 好的 finding

```
- 位置：order-service.ts:88-145
- 卡點類型：跳轉
- 第一次讀會發生什麼：讀到第 102 行的 `applyDiscount(order, ctx)`，無法
  判斷 ctx 裡哪些欄位會被讀到，得跳去 discount-engine.ts:34 看
  applyDiscount 的實作，再跳回原處才能繼續理解後面的邏輯。
- 觸發的 heuristic：function 形狀（要跳 ≥ 3 個方法才懂）+ 命名
  （ctx 過於籠統，第二字元就是泛詞 context）
- 重寫建議：在 88 行的 function signature 上方加一行註解說明
  ctx 中 applyDiscount 會用到的欄位（campaignId, userTier），或把
  applyDiscount 的 signature 改成顯式接收這兩個欄位。
```

### 壞的 finding（會被自我節制規則擋下）

```
- 位置：order-service.ts:88
- 卡點類型：停頓
- 第一次讀會發生什麼：function 太長，讀起來很累
- 觸發的 heuristic：function 形狀
- 重寫建議：應該拆成幾個 private method
```

被擋下的理由：
- 「太長很累」不是可觀察訊號（違反規則 1）
- 「應該拆成幾個 private method」沒證明拆完後跳轉次數會減少（違反規則 2）
- 沒指出具體要拆出哪些單元、拆完讀主流程的人少看了什麼

## 報告結構

最終回覆給使用者的格式：

```markdown
## Readability Review: [檔案/範圍]

**摘要**：冷讀記錄 N 個事件 → M 個 finding + K 個 fyi。

### Findings（按嚴重度排序）
1. [finding 5 欄格式]
2. ...

### FYI（命中 heuristic 但讀起來其實順暢，或被「語境優先」規則降級）
- [簡述位置與情況]

### 整體印象（選填）
一段話描述讀完整段 code 的腦內負擔感受，例如「主流程清晰但
errorhandling 散落在三處導致每讀一段都要回頭」。
```
