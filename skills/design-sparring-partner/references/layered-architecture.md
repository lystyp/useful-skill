# 分層架構的形狀、命名與呈現

> 本檔是 `design-sparring-partner` 的參考檔。當協作產出是一支**分層後端 / service / Lambda / CLI** 時，用這裡的慣例決定「分哪些層、code 放哪、各部件怎麼命名、主流程寫在哪、怎麼把架構描述給使用者」。
>
> **一條軸「該不該」抽象 → 看 SKILL.md §4**（≥2 實作或被點名才抽、變化軸訊號、DIP）。本檔只管「確定要分層 / 抽象**之後**，形狀長怎樣、名字怎麼取、主流程怎麼躺」。

## 目錄
- 這在治什麼病
- 預設分層（進入點 → service → repository）
- 四條形狀原則
- 反模式 ↔ 改法（通用例子）
- 怎麼把架構「描述」出來
- 與專案慣例的關係

---

## 這在治什麼病

請 AI 設計架構，產出的可讀性常偏低，而使用者**說不出差在哪**——只覺得「我自己分的比較好讀」。差別有具體來源，是 LLM 的四個預設傾向同時砸在可讀性上：

1. **自創詞彙**：`sink` / `job` / `runPull` / `orchestrator` 這種 repo 私有字典，每個讀者都得先讀過才懂。
2. **多一層 indirection**：為只有一個實作的東西加 `interface + factory`，追一條資料流要多跳兩個檔。
3. **把主流程打散**：步驟散在 orchestrator → interface → factory → impl，要回答「跑這支會發生什麼」得開五個檔。
4. **用設計模式命名而非用途命名**：`Sink` / `Adapter` / `Manager` / `Processor`——講的是 GoF pattern，不是「這東西幹嘛的」。

---

## 預設分層

除非專案另有慣例，新功能照這三層擺（就是常見的 Controller → Service → Repository，這裡寫成資料夾）：

```
<進入點層>/     ← 視框架而定：API 後端 controller、Lambda handler、CLI command、排程 job entry
service/
  <用途>-service/
repository/
```

- **進入點層**：薄殼。不管框架叫它 controller 還是 handler，角色都一樣——「解析/驗證輸入 → 載設定/算參數 → 委派給 service」。**主流程的故事寫在這層**，由上而下讀得完。
- **service/**：一個資料夾對一個外部系統或一塊內聚能力，名字講**它是幹嘛的**：`payment-service`、`s3-service`、`email-service`。不是 `sink`、不是 `data-manager`。
- **repository/**：把 DB 操作封在這裡，上層只呼叫語意方法（`findActiveByEmail` / `recordStart`），不直接碰 ORM 查詢。

**跨 repo 用同一套分層詞彙本身就是可讀性資產**：團隊看任何一個 repo 都用同一張地圖。設計前先看團隊其他專案用什麼分層詞，跟它一致，而不是自創一套更「乾淨」的。

---

## 四條形狀原則（附 why）

### 1. 主流程要在進入點層讀成一條線
讀者應該在**一個地方**順著 step 1 → 2 → 3 → 4 讀完「這支在做什麼」，不必在 orchestrator / interface / factory / impl 之間跳。流程是線性的故事，就讓它線性地躺著。

### 2. 命名表達「用途」，不是「模式」
`s3-service`（它為了什麼）勝過 `sink`（它是哪個 pattern）。看到名字就知道它的責任，不用打開檔案。避免 `manager` / `helper` / `util` / `processor` / `handler` 當雜物櫃。（呼應 SKILL.md §2：掛業界術語幫使用者判斷、但對外命名要表意。）

### 3. 跟團隊既有分層一致 > 局部的小聰明
若團隊其他 repo 是 Controller → Service → Repository，就照抄這套詞，即使你想到一個「更貼切」的分法。一致性帶來的肌肉記憶，比單一 repo 的巧思值錢。（呼應 §1 locate-then-build、§3 對齊既有同類。）

### 4. 真有變化軸時，seam 的「形狀」用問答決定，不要預設
**軸該不該抽象看 §4；確定要抽之後**，要用哪種**形狀**——建構子參數 / 一個分支 / 設定值，還是 `interface + 多 impl + factory`——**沒有預設答案，取決於當下情境與未來擴充性**。不要憑直覺選邊，不確定就**回問使用者**：

- 現在有幾個**真實**實作？（只有一個 → 多半先具體）
- 未來**明確**會加嗎？大概多久之後、誰來加？
- 換/加實作時要不要不動到呼叫端？
- 團隊其他地方這類 seam 慣例怎麼接？

擴充性是真需求 → 值得 interface/factory，把呼叫端跟實作隔開；只是「可能哪天」→ 先具體、把「之後好改」留在內聚的位置就好。共通底線：**seam 不該把主流程打散**。

---

## 反模式 ↔ 改法（通用例子）

以一支「使用者下單」的 API 為例（換成「同步報表」「寄帳單」「處理 webhook」都一樣）。

**反模式**（agent 預設容易長成這樣）：入口 `OrderProcessor`（丟在 `job/` 或散在各處）呼叫 `IPaymentGateway` + `PaymentGatewayFactory`（其實只接一家金流）、`INotifier` + `NotifierFactory`（其實只寄 email）；下單的步驟散在 processor 與各 strategy 裡。
→ 要回答「下單到底會發生什麼」得跳 controller → processor → IPaymentGateway → factory → impl 好幾個檔；`processor`/`gateway-strategy` 是私有詞彙；兩個 factory 各只有一個實作，純多一層。

**改法**：`controller/orderController` 的 action 讀成一條線——

```ts
const input  = validate(req.body);                 // 1. 驗證輸入
const charge = await paymentService.charge(input); // 2. 收款
const order  = await orderRepository.create(...);  // 3. 建單
await emailService.sendConfirmation(order);        // 4. 寄確認信
```

金流、通知各是一個**用途命名的具體 service**。只有一家金流就先別抽 factory；未來真要多家，依原則 4 問清楚「幾家、多久、誰加」再決定 seam 形狀。讀者在一個 action 裡就看完整條流程，名字都自我說明。

---

## 怎麼把架構「描述」出來

痛點是「agent 描述架構時可讀性低」。提出設計時照這個結構講，讓使用者一眼能比對：

1. **資料夾樹**：進入點層 / service / repository 攤出來。
2. **每個 service 一行**：用「用途」講它的**單一責任**（`payment-service ← 只負責呼叫金流收款`）。
3. **進入點層的主流程當編號步驟列出**（step 1→2→3→4），不要只說「會呼叫 service 處理」。
4. **點出有沒有真的會變的軸**：若有，依原則 4 把該問的問清楚、說明 seam 形狀怎麼定；若無，講明為什麼先具體。
5. **標出任何偏離團隊既有分層的地方**並說明理由——預設要一致，偏離要有交代。

實作前先把這份描述拿給使用者確認分層，確認後才動手寫 code。

---

## 與專案慣例的關係

若專案 / 團隊已有自己的分層慣例（資料夾命名、要不要分 route 與 controller、用不用某種 factory），**以專案既有的為準**；本檔是「沒有現成慣例時」的預設。設計前先掃一眼專案現有結構，跟它一致，再套本檔的原則。
