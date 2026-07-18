# 擴充性 Extensibility Code Review 規範

> 適用所有檔案（class 與 function 層級）。本規範聚焦「加一個新種類 / 新行為時，要不要回頭改既有程式碼」的偵測與重構。
> 職責切分見 `single-responsibility.md`；function 內部抽象層級見 `readability.md`，避免重複。
> 下文的「請求入口／商業邏輯／資料存取／共用工具」是**概念角色**，不是特定框架的層名；專案若無對應分層，映射到承擔該職責的最接近位置即可。

## 核心原則

1. **OCP（Open-Closed Principle）— Robert C. Martin《Clean Code》**
   軟體實體應**對擴充開放、對修改封閉**：加新功能用「新增程式碼」達成，而非「回頭改既有程式碼」。
   檢視問句：**每次需求多一個「種類」（多一個審核通道、多一種內容產製類型、多一種付款方式），要動幾個既有檔案？** 答案越多、越分散，擴充性越差。

2. **DIP（Dependency Inversion Principle）**
   高層模組依賴抽象（interface），不依賴具體實作。抽象穩定 → 換 / 加實作不動高層，也利於測試注入 double。

3. **LSP（Liskov Substitution Principle）**
   子型別必須能無痛替換父型別。違反時多型擴充會逼出 `if (x instanceof Y)` 特例分支。

## 偵測訊號（extensibility code smells）

> 逐條使用 TodoWrite 工具標記檢查進度。逐項確認目標是否出現以下訊號：

- [ ] **重複的 switch / if-else 鏈**：同一組型別判斷散落多處，加一種就要全部改
- [ ] **型別判斷 + 行為綁死**：`if (type === 'X') doX() else if ...` 把「分類」與「行為」寫在呼叫端，而非交給多型物件
- [ ] **Shotgun Surgery（散彈式修改）**：加一個小種類要同時改商業邏輯 + 設定檔 + 測試替身 + 測試多個檔案
- [ ] **`instanceof` / 向下轉型**：呼叫端在猜具體型別，代表多型沒做好（違反 LSP）
- [ ] **布林 / flag 參數爆炸**：`build(x, true, false)` 用旗標切行為，新情境再加旗標
- [ ] **enum 對照散落**：同一個 enum 的行為差異在多個檔案各自維護 hardcoded 對照，未集中
- [ ] **加功能得改既有測試**：加新種類卻要改舊測試斷言，代表耦合到實作細節而非抽象
- [ ] **匯總邏輯寫死 N 個分支**：處理一組同類物件卻寫死三個 if，而非迭代集合
- [ ] **狀態轉移直接賦值、無守門（State）**：`entity.status = NEXT` 這類直接指派散落多個商業邏輯單元，沒有單一「合法轉移表 / guard」把關非法轉移（如已 `PUBLISHED` 又被轉回 `GENERATING`）；判斷「能不能上架 / 能不能重生」的合法後繼在多處各自 hardcode，加一個新狀態要全部改。（此為 transition validity，與下方「集中對照表」的 behavior dispatch 是不同軸）
- [ ] **外部 SDK 型別洩漏進 domain（Adapter/ACL）**：商業邏輯 / 資料存取單元的參數或回傳型別直接是第三方 SDK 的型別（RPC 訊息物件、雲端語音服務回應、影像辨識結果），或同一個 vendor 套件被請求入口 / 商業邏輯 / 背景工作各自直接引用呼叫，而非收斂到單一 adapter/client 模組——SDK 換版會波及業務層
- [ ] **重造標準庫 / 框架既有功能（YAGNI）**：手刻語言標準庫、內建語法或所用框架／函式庫已提供的東西（自寫深拷貝、自刻日期格式化、手組查詢語句組裝器、自寫參數驗證）
- [ ] **為小事引入依賴（YAGNI）**：為一兩行就能解決的邏輯裝一個套件，徒增供應鏈與維護面
- [ ] **沒人用的彈性 / dead flexibility（YAGNI）**：預留的 option / 泛型參數 / 擴充 hook 只有單一 caller、從未被第二種情境用到（與上面「flag 參數爆炸」呼應，但聚焦「預留卻沒人用」的投機抽象）
- [ ] **這 feature 根本不需要存在（YAGNI）**：需求未確認就先寫的「之後可能用到」的 endpoint / 欄位 / 分支；YAGNI 用在 feature 層級，不只抽象層級

> 實用快篩：grep 同一個 enum 值（如 `PREMIUM_VIDEO`）。若散落十處各自判斷，即為擴充熱點。

## 重構手法 / Design Patterns（解決方向）

| 訊號 | 對應手法 |
|------|---------|
| 依型別分支的行為散落 | **Strategy / Polymorphism**：收斂成實作同一介面的策略物件，用 map / 集合查找與迭代；加種類 = 新增 class + 註冊一筆 |
| 散落的 `new` 與型別判斷 | **Factory / Registry**：`Map<Enum, Impl>` 集中建立邏輯，新增種類只註冊一筆 |
| 流程骨架固定、步驟因種類而異 | **Template Method**：骨架放父層，變動點開 hook / 抽象方法 |
| 高層綁死具體實作、難測試 | **DIP + DI**：依賴 interface，正式注入真實實作、測試注入 double |
| enum 行為差異散落 | **集中對照表**：以 enum 值為 key 的單一設定對照（如「產製中狀態 → 對應失敗狀態」的對照表），避免散在各處各自 hardcode |
| 狀態轉移散落、無守門 | **轉移表 + guard**：集中的 `From → Set<To>` 對照 + 一個 guard 函式擋非法轉移；一般資料導向後端在 KISS 取向下**不需 full GoF State（每狀態一個 class）**，那是 over-engineering。與上一列「集中對照表」交叉引用（transition validity ≠ behavior dispatch） |
| 外部 SDK 型別穿透到業務邏輯 / domain | **Adapter / Anti-Corruption Layer**：SDK 只在單一 translation point 出現，vendor 型別不得成為業務函式的參數/回傳型別；換供應商 / 升 SDK 時業務邏輯不動 |
| 重造標準庫 / 框架功能、多餘依賴、沒人用的彈性 | **刪掉、別重構（YAGNI）**：優先語言標準庫 → 所用框架／函式庫既有能力 → 已安裝的依賴；移除為小事引入的套件；預留卻無第二個 caller 的擴充點直接拔掉，等真的第三次重複再抽象（Rule of Three） |
| 多個同類處理者，要選 Strategy/Registry 還是 Chain of Responsibility | **依執行形狀選型**：扇出並行 + 匯總全部結果（scatter-gather）用 **Strategy + Registry**（迭代集合、平行執行後匯總含失敗在內的全部結果）；循序傳遞且**第一個能處理就短路**才用 **Chain of Responsibility**。別把扇出匯總硬塞進 CoR——會失去並行與「全部結果」，淪為多餘的「傳給下一棒」包裝 |

## 實務拿捏（別過度抽象）

OCP 有成本（抽象、interface、registry 都增加間接層）。準則：

- **Rule of Three**：第一次寫具體；第二次重複先忍；**第三次**才抽象。過早抽象常猜錯擴充軸（YAGNI）。
- **只在「真的會變的軸」上開放擴充**。已知會長的軸（如審核通道、內容產製類型）值得投資抽象；不會變的地方保持簡單。
- 抽象選錯軸比不抽象更糟——會逼後人沿錯誤接縫硬塞。與 `single-responsibility.md` 的「過度拆分 / Shotgun Surgery」呼應。
- **反向偵測（over-engineering / Golden Hammer）**——「已經套了 pattern 卻只有一個變體」也是 finding，別只抓「該抽沒抽」。訊號：
  - [ ] **單一實作的 Strategy / interface**：抽了介面或策略物件，但實作只有一個、無第二個變體在望
  - [ ] **一筆 entry 的 registry / 一個型別的 factory**：`Map` 只註冊一項、factory 只 `new` 一種，間接層沒換來多型收益
  - [ ] **只有一個 caller 的間接層**：為「以後可能」開的 hook / 泛型參數 / 抽象方法，全 repo grep 只有單一使用點（與上方「dead flexibility」呼應，但聚焦「已套 pattern 卻只有一個變體」）
  這幾條的解法都是**拔掉間接層、inline 回去**，等第三次重複再抽（Rule of Three）。

## 建議格式

標籤依違反的原則對應命名：`[擴充性]`（OCP）、`[DIP]`、`[LSP]`、`[YAGNI]`（重造 stdlib / 多餘依賴 / 投機抽象 / 沒人用的彈性）。

```
- **[擴充性]** {檔案}:{行數範圍}
  - 問題：{描述加新種類時要改哪些既有程式碼，引用偵測訊號}
  - 原則：{OCP / DIP / LSP}
  - 建議：{具體手法，如 Strategy 收斂哪段 switch、改用哪個 registry}
```
