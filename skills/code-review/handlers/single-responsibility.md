# 單一職責 Single Responsibility Code Review 規範

> 適用所有檔案（class 與 function 層級）。本規範聚焦「一個 class / function 是否承擔過多職責」的偵測與重構。
> function 內部「抽象層級一致、Extract Method」的細節見 `readability.md`；模組間依賴強度見 `coupling-cohesion.md`，避免重複。
> 下文的「請求入口／商業邏輯／資料存取／共用工具」是**概念角色**，不是特定框架的層名；專案若無對應分層，映射到承擔該職責的最接近位置即可。

## 核心原則

1. **SRP（Single Responsibility Principle）— Robert C. Martin《Clean Code》**
   一個模組應該只有「**一個變更的理由**」(one reason to change)。重點不是「只做一件事」，而是只對「**一個 actor / 一個變更來源**」負責。
   檢視問句：這個 class/function 會因為「誰」的需求而被改？若有多個角色（如行銷改規則、風控改審核、App 團隊改回傳格式），即為多職責。

2. **CQS（Command-Query Separation）— Bertrand Meyer**
   一個 function 要嘛改變狀態（command）、要嘛回傳資料（query），不要既改又查。

3. **SLAP（Single Level of Abstraction Principle）— Robert C. Martin**
   一個 function 裡每一行應在同一抽象高度。高層流程夾雜低層細節（如編排流程中直接組資料庫查詢語句、直接拼 HTTP 請求）即違反。

4. **Tell, Don't Ask**
   若一個 method 一直在「問」其他物件的狀態再做決定，職責可能放錯了位置。

## 偵測訊號（code smells）

> 逐條使用 TodoWrite 工具標記檢查進度。逐項確認目標 class / function 是否出現以下訊號：

- [ ] **方法 / 類別過長**：function 超過一頁、class 數百行，通常塞了多個關注點
- [ ] **命名含糊**：出現 `And` / `Or`（如 `validateAndSave`）或泛用後綴 `Manager` / `Processor` / `Helper`，是職責不清的標誌
- [ ] **難以命名**：取不出精準名字，表示它做的事無法用單一概念概括
- [ ] **依賴 / import 爆炸**：同時引入多個不相關領域（如審核規則 + 資料庫用戶端 + 輸出格式轉換 + 多組列舉），依賴面越廣職責通常越雜
- [ ] **測試難寫**：要 mock 一大堆東西、測試案例組合爆炸，代表它管太多
- [ ] **水平關注點混雜**：同一 method 內同時有「業務決策」+「資料存取」+「格式轉換」（違反 SLAP）
- [ ] **註解分段**：用 `// ---- 驗證 ----`、`// ---- 寫入 ----` 切段落，等於在標示「這裡該拆」
- [ ] **command 與 query 混用**：一個 function 既改狀態又回傳查詢結果（違反 CQS）

## 重構手法（解決方向）

| 訊號 | 對應手法 |
|------|---------|
| 段落式長方法 | **Extract Method / Extract Function**：把段落抽成具意圖名稱的私有方法，主流程讀起來像目錄（細節見 `readability.md`） |
| 一群欄位+方法總是一起變動、自成概念 | **Extract Class**：抽成新 class（如把審核邏輯抽成 `PublishModerationPolicy`） |
| 一個商業邏輯單元編排太多事 | **拆分**：編排者只負責串流程，協作者（審核規則、輸出轉換、資料存取）各自聚焦 |
| 商業邏輯裡直接寫資料庫查詢語句 | **下沉資料存取**：改呼叫資料存取單元，維持「商業邏輯 → 資料存取 → 資料庫」單向依賴 |
| 一個 class 因「多種規則」膨脹 | **Strategy / Policy 物件**：把變動點隔離成策略物件（如多源審核、不同 redeem 類型） |

## 實務拿捏

別走極端。過度拆分會造成 **Shotgun Surgery（散彈式修改）**——改一個需求要動十個檔案，這同樣違反 SRP 的精神（本該一起變的東西被拆散）。

判準：**會一起改變的放一起，會分開改變的拆開**（高內聚、低耦合）。與 `readability.md` 的「過度拆分：一行程式碼包成一個 private method」呼應。

## 建議格式

標籤依違反的原則對應命名：`[單一職責]`(SRP)、`[CQS]`、`[SLAP]`、`[Tell-Don't-Ask]`。

```
- **[單一職責]** {檔案}:{行數範圍}
  - 問題：{描述職責過多的具體現象，引用偵測訊號}
  - 原則：{SRP / CQS / SLAP / Tell-Don't-Ask}
  - 建議：{具體重構方向，如 Extract Class 出哪個職責、下沉到哪個資料存取單元}
```
