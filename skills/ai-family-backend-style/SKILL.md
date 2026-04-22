---
name: ai-family-backend-style
description: ai_family_backend / backend-v2 專案的 coding style 與實作 tips — 分層架構（Controller → Service → Repository）、Zod validator 慣例、Import 分群、Prisma + Exception 處理、Pagination、Swagger/Router/Service/Repository 的新增流程、SRP 檢查四問、Commit 規範。當在 /Users/daniel.shi/hephai/ai_family_backend 這個 repo 內寫或改 code（特別是 controllers/services/repository/validators/routes/swagger）時觸發。
user-invocable: true
---

# ai_family_backend 專案 Coding Style & Tips

本 skill 是 `ai_family_backend`（內部代號 backend-v2）的專案慣例速查。目標是讓每次進這個 repo 都能立刻產出符合既定風格的 code，不需要重新對齊。

Source of truth：`backend/guidelines/*.md`（專案內既有）。本 skill 是**摘要 + 高頻 tips**，遇到衝突時以 repo 內的 guideline 檔為準。

---

## 0. 何時觸發

- cwd 在 `/Users/daniel.shi/hephai/ai_family_backend` 底下
- 正在動 `backend/src/{controllers,services,repository,validators,routes,swagger}/*`
- 使用者提到「backend-v2」、「ai_family_backend」
- 要產 API、API spec、swagger、zod schema

---

## ⚠ 鐵律 — 不要重造輪子（最常犯的錯，先看這區）

動手寫任何一段新 code **之前**，先確認下面這些：

1. **Response 絕對不要自己組** — 不要 `res.status(...).json({ success: true, ... })`，一律用 `@/utils` 的 response function：
   - `successResponse(res, data, message)` — 200
   - `createdResponse(res, data, message)` — 201
   - `errorResponse` / `validationErrorResponse` — 錯誤
   - 錯誤一律走 `handleError(error, res, "中文情境")`，不要自己組 error body
2. **Service input 不要自己多生一個型別** — 直接吃 controller 解析後的 request（就是 validator 匯出的 `XxxQuery` / `XxxBody`）。看到 `service.doX(customInputType)` 而 `customInputType` 長得跟 validator 型別幾乎一樣，就是在造輪子。
3. **寫 Validator 前先看 `src/validators/common.validator.ts`** — 裡面已經有一堆可重用的東西，不要自己刻：
   - `createUuidSchema(desc, errMsg?)` — UUID
   - `basicDataSchema` — id / createdAt / updatedAt 三件組
   - `paginationQuerySchema` — page / limit
   - `commonFields` — id / createdAt / updatedAt 的原始欄位
   - `requiredError` / `enumError(EnumClass)` — 錯誤訊息 helper
   - 其他 validator 檔裡能 re-export 的也先找
4. **寫 helper 前先看 `src/utils/`** — 既有工具清單（`@/utils` 都有匯出）：
   - `async-handler` — `asyncHandler`
   - `date.helper` — 日期相關
   - `password.helper` — 密碼 hash
   - `common.util` — 通用
   - `query.helper` — DB query 組合
   - `response.helper` — **所有** response function 都在這
   - `prisma.helper` — pagination（`calculatePagination` / `createPaginationMeta`）、transaction
   - `reward-bundle.helper` / `picture-url.helper` / `voice-postcard.helper` — 領域 mapper
   - `zod-snake-case.util` — snake_case 轉換（給 `/device/*`）
   - 找不到既有的，才考慮新增；新增時放對位置、對應 `helper` or `util` 命名、記得在 `src/utils/index.ts` re-export
5. **新增 API 一定要同步 Swagger** — 不是可選步驟。沒 swagger 等於沒做完。流程：**先** 改 `src/swagger/paths/*` + `src/swagger/schemas/*` + validator，**才**開始寫 controller/service。只加成功 response，失敗留著之後補。
6. **Service 預設與 API 一對一，但視場景而定** — 檔名跟著 API 走（例如 `voice-postcard-list.service.ts` 對應 `GET /device/voice-postcards`、`voice-postcard-query-by-ids.service.ts` 對應 `GET /device/voice-postcards/status`）。這是預設，不是鐵規：
   - **可以合併**：多個 API 共用同一段商業邏輯、或是查詢參數不同但流程幾乎一樣（例如 `findOne` / `findMany` 可以在同一個 service）
   - **可以拆更細**：單一 API 內部流程太長、或不同步驟本身就是獨立職責（見 SRP 四問），就拆成多個 service 互相 compose
   - 判斷原則：**以職責為單位**，一對一只是大多數時候最剛好。不要為了一對一硬拆，也不要為了少寫一個檔硬塞

違反這六條是這個 repo 最常見的 code review comment，寫 code 前再確認一次。

---

## 1. 分層架構與職責

```
Route → Controller → Service → Repository → Prisma
                ↘ Validator (Zod)
                ↘ Utils (handleError / successResponse / pagination)
                ↘ Exceptions (DatabaseOperationException / ResourceNotFoundException / ...)
```

職責分工：

| 層 | 職責 | 禁忌 |
|---|---|---|
| Controller | 抽 req → call service → response | 不要放商業邏輯、不要直接碰 Prisma |
| Service | 商業邏輯、跨 repo 協調、交易 | 不要接 `req`/`res`、不要組 HTTP status |
| Repository | Prisma 查詢、DB exception 包裝 | 不要寫商業判斷、不要 throw HTTP error |
| Validator | Zod schema + 型別匯出 | 不要放業務預設值邏輯 |

**SRP 四問**（改 code 前先自檢，詳見 `backend/guidelines/check-srp.md`）：
1. 商業規則改了，我會改這段嗎？
2. 技術細節（DB/infra）改了，我也會改這段嗎？
3. 這段只是在「做一件事」嗎？
4. 這段是否同時包含「政策」和「技術」？

兩個 Yes 以上就要拆。

---

## 2. Controller 樣板

每個 method 固定長這樣：

```ts
async methodName(req: Request, res: Response): Promise<void> {
  try {
    const userId = req.appUser!.id;                         // 取身份
    const query = req.query as unknown as XxxQuery;         // 取入參（走 validator 型別）

    const result = await xxxService.doSomething(userId, query);

    successResponse(res, result, "English success message");
  } catch (error) {
    handleError(error, res, "中文情境描述（會進 log）");
  }
}
```

- `successResponse` / `createdResponse` / `handleError` 來自 `@/utils`，**一律**用它們，不要 `res.status().json(...)` 手組（見鐵律 1）
- method 上方加 JSDoc：第一行寫 `GET /device/xxx`，第二行寫中文說明
- class 底下 `export default new VoicePostcardController();` —— 預設 singleton，其他地方用 default import
- Controller 抽完的 `query` / `body`（型別來自 validator）**直接**丟給 service，不要再包一層 input DTO（見鐵律 2）

---

## 3. Service 樣板

```ts
export class VoicePostcardListService {
  async list(userId: string, query: ListVoicePostcardsQuery): Promise<ListVoicePostcardsData> {
    const { page, limit, status } = query;
    const { skip, take } = calculatePagination(page, limit);

    const [rows, total] = await Promise.all([
      voicePostcardRepository.findManyByUser({ userId, status, skip, take }),
      voicePostcardRepository.countByUser({ userId, status }),
    ]);

    return {
      items: rows.map(toVoicePostcardItem),
      meta: createPaginationMeta(page, limit, total),
    };
  }
}
export default new VoicePostcardListService();
```

Tips：
- 能並行的查詢就 `Promise.all`
- Pagination 固定用 `calculatePagination` + `createPaginationMeta`（在 `@/utils`）
- Row → API shape 的轉換用 `toXxxItem` mapper helper，放在 `src/utils/xxx.helper.ts`
- 檔名就是 `<domain>-<action>.service.ts`（例如 `voice-postcard-list.service.ts`、`voice-postcard-query-by-ids.service.ts`）
- **Service 吃 validator 型別，不要自己生 input DTO**（鐵律 2）— 參數型別直接用 `ListVoicePostcardsQuery` / `CreateXxxBody`。需要拆欄位在 method 裡解構就好，不要為了「解耦」多造一個同構的型別，那只是徒增維護成本

---

## 4. Repository 樣板

```ts
async create(data: {...}, tx?: PrismaTransactionClient) {
  const client = tx || prisma;
  return client.voicePostcard
    .create({ data })
    .catch((error) => {
      throw new DatabaseOperationException("Create voice postcard failed", error);
    });
}

async findByIdWithAvatarOrThrow(id: string, tx?: PrismaTransactionClient) {
  const client = tx || prisma;
  return client.voicePostcard
    .findUniqueOrThrow({ where: { id }, include: voicePostcardWithAvatarInclude })
    .catch(() => {
      throw new ResourceNotFoundException(`Voice postcard not found: ${id}`);
    });
}
```

鐵律：
- 每個 method 都要接 `tx?: PrismaTransactionClient`（交易傳得下去）
- 每個 Prisma 操作後面**一定**掛 `.catch(...) throw new DatabaseOperationException(...)`；找不到資源用 `ResourceNotFoundException`
- Method 命名按 JPA 風格：`findBy...`、`findManyBy...`、`countBy...`、`existedById`、`existedByIds`、`findByIdOrThrow`
- Exception 統一從 `@/exceptions` 匯入

---

## 5. Validator（Zod）慣例

**動手寫 schema 前先查 `src/validators/common.validator.ts`**（鐵律 3）— 不要什麼都自己造。常用可重用元件：

| 需要 | 用這個 |
|---|---|
| UUID 欄位 | `createUuidSchema(description, errorMsg?)` |
| 分頁 query | `paginationQuerySchema` |
| id / createdAt / updatedAt 三件組 | `basicDataSchema` or `commonFields` |
| 必填錯誤訊息 | `requiredError` |
| enum 錯誤訊息 | `enumError(EnumClass)` |

其他領域 validator（`avatar.validator.ts`、`task.validator.ts` 等）裡能 re-export 的 schema 也先找過再決定要不要自己寫。看到自己刻的 `z.string().uuid(...)` 或自己拼的「page / limit」就是在重造輪子。

來自 `backend/guidelines/add-swagger.md`，這幾個**很容易錯**：

- API url `/api/*` → 所有欄位 **camelCase**
- API url `/device/*` → 所有欄位 **snake_case**
- enum：`z.enum(EnumClass)` ✅，**不要** `z.nativeEnum(EnumClass)`
- datetime：`z.iso.datetime()` ✅，**不要** `z.string().datetime()`
- uuid：`createUuidSchema("desc", "error msg")` ✅，**不要**手刻 `z.string().uuid(...).openapi(...)`
- enum 參數來源優先序：
  1. `prisma/schema.prisma` 有沒有定義 → 有就直接 import
  2. `src/types/` 有沒有定義 → 有就直接 import
  3. 都沒有 → 在 `src/types/` 新增
- schema 寫完記得在 `src/validators/index.ts` 匯出

Zod schema 寫完要同步產兩個 type：Query/Body 型別 + Response Data 型別，Service/Controller 都吃它們。

---

## 6. Import 分群規範

檔案頂端用**註解標頭**分群，順序固定：

```ts
// Third-party imports
import { Request, Response } from "express";
import type { Prisma } from "@prisma/client";

// Database
import { prisma } from "@/configs/database";

// Repository
import voicePostcardRepository from "@/repository/voice-postcard.repository";

// Services
import voicePostcardListService from "@/services/voice-postcard-list.service";

// Utils
import { handleError, successResponse, calculatePagination } from "@/utils";

// Exceptions
import { DatabaseOperationException } from "@/exceptions";

// Types
import type { ListVoicePostcardsQuery } from "@/validators/device/voice-postcard.validator";
```

- 路徑統一走 `@/` alias，**不要**相對路徑爬 `../../..`
- `import type` 跟一般 import 分清楚（可以同群，但 type 放後面）

---

## 7. 新增一條 API 的標準流程

來自 `backend/guidelines/api-implement.md` — **逐條**開發，不要一次 batch。順序：

1. **Swagger + Zod** (`add-swagger.md`) — 先定 API 形狀（鐵律 5：swagger 不是可選步驟）
   - 更新 `src/validators/<scope>/*.validator.ts` + `src/validators/index.ts`
   - **新增 `src/swagger/paths/*` + `src/swagger/schemas/*`**（經常被忘記）
   - 只加成功 response，失敗之後再補
   - **沒做 swagger 就不算完成**，PR 也不要送
2. **Router + Controller method 殼** (`add-router.md`)
   - Controller 先留 pseudo code 註解區塊，不實作
3. **Pseudo code → 實作** (`implement-controller-method.md`)
   - 把 pseudo code 一條一條換成真 code
   - 有 DB 操作就抽成 repository.method
   - 讀起來不順就把步驟包成 private function，放 class 最下方
4. **職責檢查**：controller 胖了就拆 service；service 胖了就拆更細

---

## 8. Clean code — 「像文章一樣好讀」

出自 `refine-code.md`、`implement-controller-method.md` 步驟 4。主要觀念：

```ts
// 1. 提取請求資料
const data = this.parseRequest(req);

// 2. 並行驗證
const [isCurveExisted, isAllRulesExisted] = await Promise.all([
  intimacyCurveRepository.existedById(id),
  intimacyRuleRepository.existedByIds(ids),
]);
if (!isCurveExisted) throw new ResourceNotFoundException("...");
if (!isAllRulesExisted) throw new ResourceNotFoundException("...");

// 3. 建立
await intimacyConfigRepository.create(data);
```

要點：
- 每個步驟**上方**一行註解寫「在做什麼」
- 複雜邏輯包成 private method，名字說明意圖
- private method 排在 class 最下方
- 不順就重構，不要留 60 行的 controller method

---

## 9. Exception 策略

| 情境 | Exception |
|---|---|
| DB 操作失敗 | `DatabaseOperationException("<Action> failed", error)` |
| 資源找不到 | `ResourceNotFoundException("Xxx not found: <id>")` |
| 其他業務錯誤 | 看 `src/exceptions/` 已定義的類別，沒合適再新增 |

- Service 可以 throw `ResourceNotFoundException`（業務判斷）
- Repository 只負責包裝 Prisma 錯誤
- Controller **不**主動 throw，靠 `handleError` 轉 HTTP response

---

## 10. Commit 規範

本 repo **不用** Conventional Commits。格式：

```
[tag] short imperative summary
```

Tag：`[add]` 新功能 / `[mod]` 修改既有（含 refactor）/ `[del]` 刪除 / `[fix]` bug fix / `[chore]` 維護

規則：
- summary 小寫、無句號、祈使句
- **不加** `Co-Authored-By:` trailer
- **不加** 任何 AI attribution
- 詳見 `backend-v2/.claude/skills/commit/SKILL.md`

---

## 11. 快速檢查清單（提交前）

- [ ] Controller 只有 try/catch + 取參 + call service + response
- [ ] **Response 一律走 `successResponse` / `createdResponse` / `handleError`，沒有手組 `res.status().json(...)`**（鐵律 1）
- [ ] **Service 參數型別就是 validator 的 `XxxQuery` / `XxxBody`，沒有額外造同構 DTO**（鐵律 2）
- [ ] Service 沒碰 `req`/`res`
- [ ] Repository 每個 Prisma 呼叫都有 `.catch` 轉 `DatabaseOperationException`
- [ ] **Validator 有先看 `common.validator.ts`，能用 `createUuidSchema` / `paginationQuerySchema` / `basicDataSchema` 的都用了**（鐵律 3）
- [ ] Validator 符合 `/api` camelCase、`/device` snake_case
- [ ] `z.enum` / `z.iso.datetime()` / `createUuidSchema` 用對了
- [ ] **需要 helper 時先掃 `src/utils/`，沒有才自己寫，寫完有 re-export 到 `index.ts`**（鐵律 4）
- [ ] Import 分群 + `@/` alias
- [ ] 能 `Promise.all` 的都並行了
- [ ] Pagination 走 `calculatePagination` + `createPaginationMeta`
- [ ] Validator、Service、Controller 三處型別都對齊
- [ ] **Swagger paths + schemas 同步更新了**（鐵律 5）
- [ ] Commit message 是 `[tag] ...` 格式，沒有 Co-Authored-By
