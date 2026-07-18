# DRY / 重複 Code Review 規範

> 適用所有語言、所有檔案。本規範聚焦「同一則**知識**是否被表述了兩次以上」的偵測與收斂。
> 文中「請求入口 / 商業邏輯 / 資料存取 / 共用工具」是**概念角色**，不是特定框架的層名；專案若無對應分層，映射到最接近的位置。
> 「重複 switch/if 收斂成 Strategy」的擴充軸見 `extensibility.md`；magic number 該不該具名、列舉字面值見 `types-and-data.md`（本檔管「同一值散落多處」的重複面向，兩者互引）。

## 核心原則

1. **DRY 管的是「知識」不是「文字」— Andy Hunt & Dave Thomas《The Pragmatic Programmer》**
   「Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.」重複的不是字面相同的字元，而是同一則業務規則 / 意圖被寫了兩次以上。

2. **字面相同 ≠ 重複。** 兩段長得一樣的 code，若代表**會各自獨立演化的兩則知識**，強行合併反而製造錯誤耦合（coincidental duplication）。判準：一個需求變動會不會**同時**逼你改這兩處？會＝真重複；不會＝巧合。

3. **平行結構（parallel modification）是重複的稅。**（Martin Fowler《Refactoring》: Duplicated Code）一個改動要在多處同步改，就是知識被複製的信號；漏改一處就是 bug。

4. **DRY 有上限：wrong abstraction 比 duplication 貴。**（Sandi Metz; Kent C. Dodds — AHA）抽象要等 use case 清楚、共通性自己浮現才做（Rule of Three）。

## 偵測訊號（code smells）

> 逐條使用 TodoWrite 工具標記檢查進度。

**字面 / 結構重複**
- [ ] 兩個以上函式 / 方法主體幾乎相同（差幾個變數名或欄位），同一則業務規則被複製
- [ ] copy-paste 後只改中間一兩行（頭尾相同）——應 Extract Function 後參數化差異
- [ ] 相似的資料查詢（相同過濾條件 / 關聯載入 / 欄位選取組合）散落多個資料存取函式
- [ ] 多個請求入口重複同一段請求解析、分頁計算、回應包裝邏輯

**單一真相源（最高風險區）**
- [ ] 同一數值常數（費用、門檻、上限、重試次數、TTL）以字面值散寫多處，而非引用單一設定 / 常數模組
- [ ] 同一 error code / message 字串在拋錯處與測試斷言處各寫一份
- [ ] 輸入驗證的欄位清單與資料模型定義各手寫一份、會 drift
- [ ] API 文件的 request/response 形狀與輸入驗證各寫一份欄位清單，未由單一來源導出（docs 應指向 source of truth、勿手抄欄位）
- [ ] 資料結構 / 型別在各處 inline 定義，而共用型別模組已有等義定義（含由它衍生的子集型別）
- [ ] 同一 entity 在多個端點各自手寫 map 成回應，欄位對映重複

**平行結構 / test 重複**
- [ ] 新增一個列舉值 / 狀態 / 欄位時，可預見要「順手同步改」API 文件、驗證、對映、種子資料、測試多處——知識分散
- [ ] production 的業務規則（門檻、計費公式）在測試裡硬寫一份數字，規則一改測試抓不到
- [ ] 多個 test 重複建置相同前置狀態，未走共用 fixture / 前置輔助

## 重構手法對照

| 訊號 | 解法 |
|------|------|
| 函式主體雷同 | **Extract Function**，差異處參數化（傳值 / callback / strategy） |
| 資料查詢片段重複 | 收斂到單一資料存取函式，或共用查詢條件 / 欄位集合常數 |
| 入口解析/分頁/包裝重複 | 抽共用驗證 schema + 回應建構工具（共用工具 / 中介層） |
| 常數散落 | **Extract Constant** 至設定 / 常數模組，引用而非複寫 |
| 驗證 ↔ 資料模型欄位 drift | 單一真相源：由模型型別導出驗證，或由驗證推導型別，或用生成工具 |
| API 文件 ↔ 驗證各一份 | 文件由驗證 / 型別導出；docs 指向 source of truth |
| inline 型別重複 | 移到共用型別模組具名定義，各處引用 |
| 同 entity 多處手動 map | 抽單一 mapper（純函式，放共用工具，補單元測試） |
| test 硬寫 production 規則 | test 引用同一常數 / 導出值，別複製數字 |

## 實務拿捏（DRY 過頭的護欄）

- **先問「同一則知識，還是巧合相同？」** 未來會因**不同理由**各自改變的兩段，別合併。
- **Rule of Three**：第一、二次先容忍複製，第三次才抽象（Fowler）。
- **wrong abstraction 的解法是往回走**：若共用函式被越加越多 boolean / mode 參數與 conditional 來遷就各種「幾乎相同」的 caller，正解是**把抽象 inline 回各 caller**、刪去用不到的分支再視情況重抽（Sandi Metz），而非再包一層。看到「一個共用函式被塞滿 flag 參數」時，提示的是「這是 wrong abstraction，考慮拆回」——與 `extensibility.md` 的過度抽象呼應。
- **護欄不在精簡範圍**：trust-boundary 驗證、安全、資料遺失處理即使看似重複也不可為 DRY 而省。

## 建議格式

```
- **[DRY]** {檔案}:{行數範圍}
  - 問題：{哪則知識被複製到哪幾處，引用偵測訊號}
  - 判定：{真重複（會同時變動） / 需確認是否巧合相同}
  - 建議：{Extract 到哪、單一真相源設在哪、連動要改哪些檔}
```
