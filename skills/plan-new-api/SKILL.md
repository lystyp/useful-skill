---
name: plan-new-api
description: 在 backend/ 新增一支 API 時，從規格釐清到實作到測試的完整開發流程指引。規劃階段強制「一次一題」釐清設計決策（HTTP/URL、輸入驗證、權限處理、回應結構、排序、測試範圍），接著依層序實作 validator→repository→service→controller→route→swagger，並寫 service integration test + validator unit test。當使用者說「規劃一支新 API」、「幫我開一支 XX 查詢/建立 API」、「新建 endpoint」、「我要加一個 API 讓 client 可以 XX」時觸發。也涵蓋共用 mapper 模式、靜默過濾（silent filter）策略、測試寫作風格、commit 慣例。
user-invocable: true
---

# Plan New API

在 backend/ 新增一支 API 的完整流程 skill。**自足獨立，不依賴其他 skill**。從規格釐清 → 分層實作 → 寫測試 → commit，全部在這份指引內完成。

---

## 核心原則

1. **規劃階段一次一題** — 絕對不要把所有問題列成清單一次全發。每題附建議理由，使用者「選推薦或說 yes」即可。詳見下方「互動規則」。
2. **先規劃、再動工** — 所有設計決策釐清完後，**先把完整規劃（路由、檔案清單、schema 設計、測試情境）呈現給使用者確認**，確認後才開始寫 code。
3. **業界做法有疑慮時用 WebSearch 查一次再答** — 不要只憑直覺回答「業界通常怎麼做」。
4. **測試和程式碼等重要** — 每支 API 至少寫 validator unit test + service integration test（跑 testcontainer 的真 DB）。

---

## 階段總覽

```
1. 釐清規格（一次一題）
   ↓
2. 呈現完整規劃給使用者確認
   ↓
3. 依序實作（mapper → validator → repo → service → controller → route → swagger）
   ↓
4. 寫測試（validator unit test + service integration test）
   ↓
5. 驗證（tsc --noEmit + 跑測試）
   ↓
6. Commit
```

---

## 互動規則（貫穿整個流程）

### 一次只問一題

提問時遵守下列格式，**永遠不透露後續問題**：

**選擇題（優先使用）：**

```
[Q3/8] <問題描述>

**推薦：B** — <1-2 句理由>

| 選項 | 說明 |
|------|------|
| A | <選項描述> |
| B | <選項描述> |
| C | <選項描述> |
| D | 其他（請簡述） |

回覆選項代號即可，或說「yes」接受推薦。
```

**簡答題（僅在選項無意義時使用）：**

```
[Q5/8] <問題描述>

**建議：** <你的建議答案> — <理由>

請提供簡短答案，或說「yes」接受建議。
```

### 回答處理

1. 使用者回覆 "yes" / "推薦" / "建議" → 採用推薦/建議
2. 使用者選擇某選項 → 採用該選項
3. 回答模糊 → 追問釐清（sub-question，不佔用問題編號）
4. 採納後直接進下一題，**不展示更新內容、不要求確認寫入結果**
5. 保持節奏：問題 → 回答 → 下一題，中間不插入大段說明

### Sub-question 不計入編號

只有「切換到新的追蹤地圖項目」才計為下一題。同一項目內的延伸追問、回答模糊的釐清，都是 sub-question，不動主編號。

---

## 階段 1：釐清規格

用上面的「互動規則」**一題一題**問。下面是必問清單，依序問，每題先給使用者你的建議答案和理由。

### Q1：HTTP 方法與 URL 設計

根據 API 用途選擇：

- **查詢單一資源**: `GET /resources/:id`
- **列表查詢（含分頁/過濾）**: `GET /resources?page=&limit=&status=`
- **批次以 id 查詢**: `GET /resources/status?ids=a,b,c`（逗號分隔，適合 ≤ 50 個 id）
- **批次查詢但 id 數量大**: `POST /resources/query`（body 放陣列，語意上違反 REST 但避開 URL 長度限制）
- **建立 / 更新 / 刪除**: POST / PATCH / DELETE + RESTful URL

### Q2：輸入驗證規則

依輸入型別逐項問：

- **陣列輸入**: max 長度？空陣列視為合法還是 400？重複元素 dedupe 還是 400？
- **字串輸入**: max 長度？允許空字串？trim？
- **數字輸入**: 範圍？預設值？
- **Enum**: 預設值？`optional` 還是 required？

**id 格式（UUID）該不該在 validator 層檢查？**

- **預設推薦：不檢查**。理由：Prisma 對 UUID 欄位的 `id: { in: [...] }` 會 per-element 自然找不到非 UUID 字串，不會拋錯。把格式判斷交給 DB 可以：
  1. 避免把「id 是 UUID」這個假設耦合到 HTTP 層（未來 schema 改成其他 id 格式，validator 不用改）
  2. 讓 validator 保持單一職責：只做「切分、長度上限、dedupe」
  3. 和靜默過濾策略天然契合（Q3）
- **例外**：若該 API 的 id 格式不是來自 DB（例如來自第三方），且格式錯誤有明確的錯誤訊息需求，那才在 validator 層做 regex 檢查並 400

### Q3：權限與跨 user 資源的處理

所有 user-scoped API 都要決定：如果使用者傳入「不屬於自己的 resource id」該如何回？

- **A. 靜默過濾（Silent filter）** — 從 response 過濾掉，和「不存在」一視同仁。**預設推薦**。理由：(a) 不洩漏資源存在性 (b) 不洩漏是否屬於別人 (c) 實作一致簡單（DB 查詢用 `where: { userId, id: { in: ids } }` 自然過濾）
- **B. 明確標記 NOT_FOUND / FORBIDDEN** — response 為每個 request id 回一筆帶錯誤標記。僅在 client 明確需要 per-id 狀態（例如 polling）時才用
- **C. 整批拒絕（403）** — 嚴格場景才用，預設不要

### Q4：不存在的 id / 資源

延續 Q3：不存在的 id 怎麼回？通常和 Q3 一致（靜默過濾），但若是單一資源查詢（GET :id），404 是常規做法。

### Q5：Response 結構粒度

- **A. 極簡**: `{ id, status }` — 僅給 client polling 狀態用
- **B. 中等**: `{ id, status, 必要業務欄位 }` — polling 時也能直接顯示
- **C. 完整**: 和 list API 同一組欄位 —— **推薦**，因為方便共用 mapper、response schema

### Q6：Response 包裝

- 列表/批次：`{ success: true, data: [...] }` 或 `{ success: true, data: [...], pagination: {...} }`
- 單一資源：`{ success: true, data: {...} }`
- 錯誤：走 `handleError` utility（已統一）

### Q7：排序

批次 / 列表查詢必問：

- **A. 按 request id 陣列順序**（Stripe 等採用）—— client 可 index 對應，但 service 層要 post-sort，實作稍重
- **B. `createdAt DESC`** — 和本專案 list API 一致，DB 原生支援，**推薦**
- **C. 其他業務欄位** — 有需要才用

### Q8：測試範圍

- **預設：Service integration test + Validator unit test**
- Service integration test：走 testcontainer 真 DB，驗證完整查詢邏輯、user 隔離、欄位映射
- Validator unit test：純 zod schema parse，驗證 transform / dedupe / 長度上限 / 邊界值
- E2E（controller 層）：**預設不做**，除非使用者明確要求。原因：integration test 已覆蓋 service，HTTP boundary 的行為由 validate middleware + handleError 已經穩定

### 其他可能需要的釐清（當 sub-question）

若下列事項從需求說明看不出來，以 sub-question 補問：

- 是否需要交易（transaction）包住多次 DB 操作？
- 是否要呼叫外部服務（Redis、LLM、Firebase）？
- 是否需要新增 Prisma schema 欄位？（若是，要先補 migration 才能動工）

---

## 階段 2：呈現完整規劃給使用者確認

釐清結束後，把規劃整理成下列格式給使用者看，**等確認才動工**：

```markdown
## 完整規劃

### API 規格
- Method + URL: <例：GET /device/voice-postcards/status?ids=...>
- Auth: <例：requireMobileApiKey + requireAppUserAccessToken>
- Query params / Body: <逐項列出欄位、型別、驗證規則>
- Response 200: <JSON 結構>
- Response 400 / 401 / 404: <什麼條件觸發>

### 「靜默過濾」處理對照（若適用）
1. 重複 id → validator dedupe
2. 非 UUID 格式 id → Prisma `id: { in: [...] }` 對 UUID 欄位 per-element 自然找不到（不拋錯）
3. 不存在的 id → DB findMany 自然過濾
4. 不屬於當前 user 的 id → DB where: { userId } 過濾

### 檔案清單
1. <validator 檔案路徑>：新增 schema + type export
2. <repository 檔案路徑>：新增 <method 簽章>
3. <service 檔案路徑>：<新增或修改說明>
4. <controller 檔案路徑>：<新增或修改 method>
5. <route 檔案路徑>：<新增路由>
6. <swagger paths 檔案路徑>：<新增 path>
7. <service integration test 檔案路徑>
8. <validator unit test 檔案路徑>

### Service Integration Test 情境（列 N 個）
1. ...

### Validator Unit Test 情境（列 N 個）
1. ...
```

也要提兩個容易被忽略的決策：

- **欄位映射是否抽共用 mapper？** 若 DB → API 的欄位轉換邏輯（例如 `url → audioUrl`、Date → ISO 字串）在多個 service 都會用到，抽到 `backend/src/services/helpers/<domain>.mapper.ts`。若只一個 service 用，直接 private method。
- **Test 檔案位置**：service integration test 放 `backend/tests/unit/services/<name>.int.test.ts`；validator unit test 放 `backend/tests/unit/validators/<name>.validator.test.ts`（若目錄不存在，建立）。

---

## 階段 3：依序實作

### 分層依賴規則（不可違反）

```
Router → Controller → Service → Repository → Prisma
```

1. **單向依賴**：每一層只能呼叫「右邊相鄰的那一層」
2. **禁止跨層呼叫**：Controller 不可直接 import Repository 或 Prisma
3. **禁止反向依賴**：Service 不可 import Controller

`@/utils`、`@/types`、`@/constants`、`@/configs`、`@/exceptions` 屬共用模組，任何層都可 import。Middleware 和 Validator 屬橫切關注點，主要在 Router 層使用。

### 實作順序

由底層往上：

```
mapper（若有）→ validator → repository → service → controller → route → swagger
```

### Mapper（若多個 service 會共用）

位置：`backend/src/services/helpers/<domain>.mapper.ts`

模式：

```ts
import type { <Entity> } from "@prisma/client";
import type { <EntityItem> } from "@/validators/device/<domain>.validator";

/**
 * 將 <Entity>（DB entity）映射為對外的 <EntityItem>。
 * 重新命名 DB 欄位：<列出重要的重新命名>。
 */
export function to<EntityItem>(item: <Entity>): <EntityItem> {
  return { /* 明確列出 API 要對外的欄位 */ };
}
```

### Validator

位置：`backend/src/validators/device/<domain>.validator.ts`（或 admin 子目錄）

重點：

1. 用 `z.coerce.number()` 處理 query 數字（query string 都是字串）
2. 用 `z.string().default("").transform((val, ctx) => { ... })` 處理逗號分隔陣列：
   - 先 `split(",").map(trim).filter(empty)`
   - **先檢查長度上限**（DoS 防線要在其他處理前）
   - 最後 `Array.from(new Set(...))` dedupe
   - **不做 id 格式檢查**（除非 Q2 決定要）—— 把格式判斷留給 DB 層
3. 對外常數用 export（例如 `export const MAX_QUERY_IDS = 30;`）讓 test 和 error 訊息共用
4. Response schema 用 `.openapi("<Name>")` 命名，方便 Swagger 引用
5. 所有 type 用 `z.infer<typeof schema>` export

### Repository

位置：`backend/src/repository/<domain>.repository.ts`

重點：

1. 方法簽章接 `params: {...}` 物件，不要一堆 positional args
2. 可選的 `tx?: PrismaTransactionClient`，用 `const client = tx || prisma` 取得 client
3. **空陣列短路**：若 method 接受 `ids: string[]`，第一件事就是 `if (ids.length === 0) return [];`。非常重要 —— Prisma 的 `where: { id: { in: [] } }` 會白跑 DB（或某些情境行為出乎意料）
4. `.catch` 轉成 `DatabaseOperationException`，不要讓 Prisma 原生錯誤漏到 service 層

### Service

位置：`backend/src/services/<domain>-<action>.service.ts`

重點：

1. 每個 API 一個獨立 service 檔（例如 `voice-postcard-list.service.ts` / `voice-postcard-query-by-ids.service.ts`），不要把多個 API 塞進同一個 class
2. Service 負責：協調 repository + 欄位映射 + 分頁計算。不負責 HTTP 格式
3. 用共用 mapper（若有）；沒有就寫 private method
4. 同時需要 `findMany` + `count` 時用 `Promise.all` 平行

### Controller

位置：`backend/src/controllers/device/<domain>.controller.ts`

重點：

1. 同一個 domain 的所有 method 放同一個 class，不要每個 API 一個 controller 檔
2. `try/catch` 包整個 body，`catch` 用 `handleError(error, res, "<描述>")`
3. 從 `req.appUser!.id` 取 user id（middleware 已保證非 null）
4. `req.query as unknown as <QueryType>`（query 已被 validate middleware 轉成 typed）

### Route

位置：`backend/src/routes/device/<domain>.routes.ts`

重點：

1. `router.use(requireMobileApiKey)` + `router.use(requireAppUserAccessToken)` 一次套用所有路由
2. 每個 endpoint：`router.get("/", validate(schema, "query"), controller.method.bind(controller))`
3. 注意路徑優先順序：`/status` 這類靜態路徑要放在 `/:id` 這類動態路徑**之前**，避免被吃掉

### Swagger Paths

位置：`backend/src/swagger/paths/device/<domain>.paths.ts`

重點：

1. 用 `registerApiPaths(registry, [...])` 批次註冊
2. 每個 path 要填：method / path / summary / description / tags / security / request / responses（至少 200 / 400 / 401）
3. `description` 要寫對外 client 看得懂的說明（例如「靜默過濾不存在的 id」這種策略要寫出來）

---

## 階段 4：寫測試

### Service Integration Test

位置：`backend/tests/unit/services/<domain>-<action>.service.int.test.ts`

**檔頭註解**（固定格式）：

```ts
/**
 * Integration test — <ServiceName>.<method>
 *
 * Scope: Service → Repository → Prisma → PostgreSQL（Testcontainers 真 DB）
 * Mocks: <列出；通常「無」>
 * SUT:   <Subject Under Test 的完整簽章>
 *
 * 目的：驗證「<一句話描述 service 的責任>」—
 *       <列 2–3 個關鍵驗證點，例如「user 隔離」「欄位映射」>
 *
 * 備註：<說明哪些不在此測試範圍，例如「validator 層的參數檢查屬 HTTP boundary 責任」>
 */
```

**describe 開頭列測試情境清單**（當目錄，讓 reviewer 快速掃）：

```ts
/**
 * 測試情境一覽：
 *
 * 1. <情境描述>
 * 2. <情境描述>
 * ...
 */
describe("<Service>.<method> (integration)", () => { ... });
```

**每個 it 的 body**用 Given / When / Then 三段式，Then 的每個 expect 前都附 `// 斷言：<為什麼這樣斷>` 註解解釋 **why**，不是 what：

```ts
it("<情境描述>", async () => {
  // Given: <前置資料>
  ...

  // When: <執行 SUT>
  const result = await sut.method(...);

  // Then:
  // 斷言：<為什麼這樣斷 —— 例如「user-scoped 查詢的基本隔離契約」>
  expect(result.data).toHaveLength(1);
});
```

**檔尾放 helper**（factory 函式），用 `[IT]` 前綴的穩定假資料（避免測試失敗時混淆真假資料）：

```ts
async function create<Entity>(...overrides): Promise<<Entity>> {
  return prisma.<entity>.create({
    data: { ..., text: "[IT] <fallback text>" }
  });
}
```

**必測情境**：

1. User 隔離（user A 查詢 user B 的資源 → 不回傳）
2. 排序（依 Q7 決定的 order）
3. 欄位白名單（`Object.keys(item).sort()` 比對預期 key 集合 + 個別檢查 DB 敏感欄位沒外露：`userId` / `updatedAt` / 其他內部欄位）
4. DB → API 欄位映射（名稱改寫 + Date → ISO 字串 + null 處理）
5. 空輸入 / 無匹配 → 回 `[]`，不拋錯
6. 分頁（若是列表 API）：第 1 頁、第 N 頁、total / totalPages 計算

### Validator Unit Test

位置：`backend/tests/unit/validators/<domain>.validator.test.ts`

**直接呼叫 `schema.safeParse()`**，不經 middleware。middleware 的 400 行為屬 integration layer，不在此範圍。

**必測情境**：

1. 單一合法輸入 → 通過
2. 多個輸入 → 陣列順序保留
3. 重複輸入 → dedupe
4. 前後空白 → trim
5. 連續逗號 / 前後逗號 → 空字串被過濾
6. 邊界值：`length = MAX` → 通過；`length = MAX + 1` → 400
7. 空字串 / missing query param → 依 Q2 決策
8. （若 validator 不做格式檢查）含格式非 UUID 元素 → 原樣保留；並在 service integration test 追加一個「含非 UUID 格式字串不拋錯、自然找不到」的情境，驗證 DB 層行為

若 Q2 決定要在 validator 做格式檢查，則加測：
- 含非法格式元素 → 依 Q2 決策（過濾或 400）
- **長度檢查位置驗證**：大量非法 + 1 個合法、總數超過 MAX → 仍 400（驗證長度檢查在 regex 過濾前，這是 DoS 防線）

---

## 階段 5：驗證

依序執行：

```bash
cd backend
bun x tsc --noEmit                                      # type check
bun x jest tests/unit/validators/<domain>.validator.test.ts
bun x jest tests/unit/services/<domain>-<action>.service.int.test.ts
# 若重構到既有 service，也要跑既有 integration test 確保沒壞
```

tsc + 所有測試綠燈後才進下一階段。任一紅燈：不要 `--no-verify` 或跳過，回去修。

---

## 階段 6：Commit

**Commit 慣例（本專案）**：

- `[tag]` 前綴格式（`add` / `mod` / `del` / `fix` / `chore`），**不用 Conventional Commits**
- **不加 `Co-Authored-By` 行**
- Commit body 的 bullet 要寫「做了什麼 + 為什麼」（例如「Repository 新增 findManyByUserAndIds：原本只有 create / updateCompleted，沒有可用於列表查詢的方法」）

**Commit 流程**：

1. 先問使用者要根據哪種變更撰寫 commit 訊息：
   - **staged**：只看已 `git add` 的變更 → 執行 `git diff --staged`
   - **both**：staged + unstaged 都看 → 執行 `git diff --staged` 和 `git diff`
2. 同時執行 `git log --oneline -10` 查看最近 commit 風格作為參考
3. 根據 diff 擬 commit 訊息（第一行簡潔描述，複雜變更加詳細說明）
4. **將草擬訊息展示給使用者確認**，詢問是否需要修改
5. 使用者確認後：
   - 若選 **both**，先列出未 staged 檔案，詢問是否要 `git add` 相關檔案
   - 執行 `git commit`，用 HEREDOC 傳入訊息避免格式跑掉
6. **不要自動 push**，除非使用者明確要求
7. **不要用 `git add -A` 或 `git add .`**，列出具體檔案讓使用者確認

HEREDOC 範例：

```bash
git commit -m "$(cat <<'EOF'
[add] <標題>

- bullet 1
- bullet 2
EOF
)"
```

---

## 常見陷阱

1. **validator 過早做 id 格式檢查**：把 UUID regex 放到 validator，不只是多餘的程式碼，還把「id 必須是 UUID」這個假設耦合到 HTTP 層。Prisma 對 UUID 欄位的 `IN` 查詢會 per-element 自然過濾，交給 DB 更乾淨。例外：id 非來自 DB 時才自己檢
2. **Prisma `IN []` 沒短路**：repository 接空陣列的 method 一定要 `if (ids.length === 0) return [];` 開頭
3. **Service 忘記做欄位映射**：直接把 DB entity 回傳會洩漏 `userId`、`updatedAt`、`responseMeta` 這類敏感欄位。務必過 mapper
4. **Test 只檢查「有回結果」不檢查排序**：排序是容易 regress 的，要明確 assert 順序
5. **Route 順序寫反**：`/:id` 放在 `/status` 前面會吃掉 `/status` 的請求
6. **裝飾性的 dead code 檔案**：新增 helper / utility 前要確認真的有被 import，避免留下沒人用的殼子

---

## 參考既有實作

- List API（分頁 + 過濾）：`backend/src/services/voice-postcard-list.service.ts` + 對應 integration test
- 批次以 ids 查詢：`backend/src/services/voice-postcard-query-by-ids.service.ts` + 對應 integration test + validator unit test
- 共用 mapper：`backend/src/services/helpers/voice-postcard.mapper.ts`

這兩支 API 都是此 skill 的「reference implementation」，新 API 直接仿照結構即可。
