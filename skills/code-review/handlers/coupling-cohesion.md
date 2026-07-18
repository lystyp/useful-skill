# 耦合與內聚 Coupling & Cohesion Code Review 規範

> 適用所有語言、所有檔案。本規範聚焦「模組**之間**的依賴強度（低耦合）與模組**內部**的聚焦程度（高內聚）」。
> 文中「請求入口 / 商業邏輯 / 資料存取 / 共用工具」是**概念角色**，不是特定框架的層名；專案若無對應分層，映射到最接近的位置。
> 職責切分（一個模組幾個變更理由）見 `single-responsibility.md`；magic 值 / primitive obsession / data clumps 的「資料形狀」面向見 `types-and-data.md`；本檔管其「造成跨模組耦合」的面向，兩者互引。

## 核心原則

1. **Cohesion（內聚）— Constantine / Yourdon《Structured Design》**
   一個模組 / 型別 / 函式內部各元素為同一目的而聚在一起的程度。由弱到強：Coincidental → Logical → Temporal → Procedural → Communicational → Sequential → **Functional**（最佳）。高內聚＝能用「一句話、無 and/or」描述其職責。

2. **Coupling（耦合）— 同源**
   模組間互相依賴的強度。由壞到好：Content（直接改/跳進對方內部）→ Common（共享全域可變狀態）→ External → Control（傳旗標控制對方走哪條路）→ Stamp（傳整包結構、對方只用一部分）→ Data（只傳所需基本資料）→ Message。**目標：停在 Data / Message；出現 Content / Common / Control 是紅旗。**

3. **Law of Demeter（最少知識原則）— Lieberherr**
   「只跟直接朋友說話」：只呼叫自身、參數、自己建立的物件、直接持有成員的方法；不可 `a.getB().getC().doX()`（train wreck），否則呼叫端依賴遠端物件的內部結構。

4. **Connascence（連生）— Page-Jones / Weirich**
   量化耦合的語彙：一方改、另一方必須跟著改。靜態 Name<Type<Meaning<Position<Algorithm；動態（更強）Execution / Timing / Value / Identity。重構準則：把**強** connascence 轉**弱**（Position→Name）；**跨模組邊界只允許最弱的（Name/Type）**，強的只能留在同檔近距離內。

## 偵測訊號（code smells）

> 逐條使用 TodoWrite 工具標記檢查進度。

**Law of Demeter / Message Chain**
- [ ] train wreck 鏈式存取 `a.getB().getC().doX()`，呼叫端依賴中間物件內部結構
- [ ] 請求入口穿透商業邏輯摸回傳物件的深層欄位（`service.getState().internal.flag`），而非叫對方直接給答案
- [ ] 商業邏輯沿著 `repo.getModel().relation.field` 把資料層的關聯結構洩漏出來

**跨層 / 架構耦合（單向依賴）**
- [ ] 商業邏輯直接呼叫資料庫驅動 / ORM 原生 API（跳過資料存取層）＝ Content coupling、破壞單向依賴
- [ ] 兩個模組共享 module-level 可變單例或全域變數（Common coupling）
- [ ] 下層回傳框架特有的請求 / 回應型別、或下層反過來知道上層（反向耦合）

**Stamp / Control coupling**
- [ ] 跨層傳整個資料模型物件 / 大 DTO，但接收方只用其中 2–3 欄位（Stamp coupling；宜只傳所需欄位降到 Data coupling）
- [ ] 函式簽章吃整包 entity 卻只讀 `entity.id`——應改吃 `id` 本身
- [ ] 布林 / mode 參數決定函式走哪條分支，呼叫端在「遙控」被呼叫端流程（Control coupling；拆函式的手法歸 `functions.md`，本檔標其耦合本質）

**Connascence 紅旗**
- [ ] 多處 hardcode 同一魔術值且語意必須一致（狀態碼、`role: 0/1`）＝ Connascence of Meaning，應集中列舉 / 設定常數
- [ ] 依位置參數順序呼叫 `fn(a,b,c,d)`＝ Connascence of Position，宜改具名參數 / 參數物件（→ Name）
- [ ] 兩處各自實作同一演算法 / 序列化 / 簽章，改一邊不改另一邊就壞（Connascence of Algorithm）
- [ ] 隱性執行順序依賴「必須先 A 再 B 否則壞」但介面沒表達（Connascence of Execution/Timing）

**Feature Envy / Inappropriate Intimacy / Middle Man**
- [ ] 某方法大量存取「別的模組 / 型別」的資料與方法，遠多於自己的（Feature Envy）——邏輯放錯位置
- [ ] 兩個模組互摸對方私有欄位、彼此深知內部（Inappropriate Intimacy）
- [ ] 某模組大半方法只是原封轉呼叫另一物件、無自身邏輯（Middle Man——多餘間接層，反向訊號）

## 重構手法對照

| 訊號 | 解法 |
|------|------|
| Message chain / train wreck | **Hide Delegate**（中間物件加委派方法隱藏導航） |
| Feature Envy | **Move Method/Field** 把邏輯搬到資料所在處；**Tell-Don't-Ask** |
| Inappropriate Intimacy | Move Method/Field、Extract Class、斷一向依賴 |
| Stamp coupling | 只傳所需欄位；跨層加 mapper 收斂 DTO |
| Control-flag 參數 | 拆成 `preview()` / `commit()` 具名方法（見 `functions.md`） |
| Connascence of Meaning | 集中列舉 / 設定常數 → 降成 Name |
| Connascence of Position | 改具名參數 / 參數物件 → 降成 Name |
| 商業邏輯直接摸 ORM / 驅動 | 補回資料存取層、恢復單向依賴 |
| Common coupling | 改依賴注入 / 參數傳入，狀態內聚到擁有者 |
| Middle Man | **Remove Middle Man** / Inline，讓呼叫端直接跟真正物件講 |

**降 connascence 通則**：① 強轉弱（dynamic/Algorithm/Position → Name/Type）；② 縮跨度（強耦合只留同檔）；③ 減程度（同一約定別散多處）。

## 實務拿捏（與 SRP 邊界、別過度拆）

- **低耦合與高內聚互相拉扯**：一味追求「小模組 / 小函式」會把本該同居的行為與資料拆散，反製造 Feature Envy、Message Chains 與 **Shotgun Surgery**（改一件事要掃十幾檔）。若「改一件事要動很多分散處」，那是**內聚不足、該合併**，非再拆。
- **近距離的強耦合可接受**：耦合非零和，重構優先給「強度高 × 跨度遠 × 程度大」者；就近的小耦合別為純潔硬拆（Rule of Three）。
- **Hide Delegate ⇄ Remove Middle Man 是一組對偶**：委派要適量，過度就 Remove Middle Man。
- 專案既有的分層紅線（單向依賴、型別集中於共用型別模組、常數集中於設定模組）同時服務低耦合與降 connascence，違反屬明確 finding。

## 建議格式

標籤依違反面向命名：`[耦合]`、`[內聚]`、`[Demeter]`、`[Connascence]`。

```
- **[耦合]** {檔案}:{行數範圍}
  - 問題：{哪兩個模組耦合、哪一級（Content/Common/Control/Stamp…）、引用訊號}
  - 原則：{Coupling 級別 / Law of Demeter / Connascence 種類}
  - 建議：{Hide Delegate / Move Method / 降 connascence 強度等具體手法}
```
