# 程式碼可讀性 Code Review 規範

## 核心原則

本規範基於三個 Clean Code 原則：

1. **Extract Method**（Martin Fowler《Refactoring》）— 將具有獨立意圖的程式碼抽取為方法，用名稱表達意圖
2. **One Level of Abstraction per Function**（Robert C. Martin《Clean Code》）— 一個函式內的步驟應在同一抽象層級
3. **Composed Method Pattern**（Kent Beck《Smalltalk Best Practice Patterns》）— 主方法由命名清晰的小步驟組成，讀起來像流程敘述

## 檢查清單

> 逐條使用 TodoWrite 工具標記檢查進度。

逐項確認每個公開方法是否有以下問題：

- [ ] 方法超過 20 行且包含 3 個以上不同層次的操作（如 HTTP 呼叫 + 資料解析 + 錯誤判斷混在同一方法）
- [ ] 方法內混合流程編排（呼叫其他方法、決定下一步）與實作細節（字串操作、位元組／編碼轉換、序列化/反序列化）
- [ ] 有程式碼區塊需要靠註解才能理解意圖（應抽取為以意圖命名的 private method）
- [ ] 方法內有多個連續的 if 判斷各自處理不同情境，但全部攤平在同一層
- [ ] Private method 名稱描述「怎麼做」而非「做什麼」（如 `checkStatusCode` 應改為 `assertResourceExists`）
- [ ] 判斷型方法缺少 `is`/`has` 前綴、驗證型缺少 `assert`/`validate` 前綴、轉換型缺少 `to`/`parse`/`from` 前綴
- [ ] 過度拆分：一行程式碼包成一個 private method（增加跳轉成本卻沒有提高可讀性）
- [ ] 名不符實 / noise words：名稱暗示錯誤型別或語意（`accountList` 其實是 `Map`），或用 `xxxData` / `xxxInfo` / `xxxObject` 這類無資訊量的後綴（`Manager` 類職責含糊的後綴歸 `single-responsibility.md`）

## 建議格式

```
- **[可讀性]** {檔案}:{行數範圍}
  - 問題：{描述具體的可讀性問題}
  - 原則：{Extract Method / One Level of Abstraction / Composed Method}
  - 建議：{具體的重構方向，如提取為哪些 private method}
```
