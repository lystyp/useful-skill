---
name: project-conventions
description: 本專案的程式碼規範與慣例集合。任何 agent 在產生新程式碼、修改既有程式碼、或 review code 之前都必須先閱讀此 skill。同時支援新增規範：當使用者說「加一條規範」、「記下這個慣例」、「以後都要這樣寫」時，使用此 skill 將新規範追加到下方 Conventions 區塊。
user-invocable: true
argument-hint: "[新規範內容（選填）]"
input: 可選的新規範描述
output: 閱讀並遵循規範，或將新規範追加到本檔案
---

# Project Conventions

本專案（backend-v2）的程式碼規範集合。所有 agent 在產生或修改 code 之前都必須先讀完此檔，並遵守下方列出的每一條規範。

---

## 使用方式

### 模式 A：閱讀規範（預設）

無參數呼叫時，agent 必須：

1. 完整讀過下方 **Conventions** 區塊的每一條規範
2. 在後續產生/修改 code 時嚴格遵守
3. 若規範之間衝突，以較具體的規範為準；仍有疑義時詢問使用者

### 模式 B：新增規範

當使用者的呼叫帶有參數，或明確表達「加一條規範」、「記下這個慣例」、「以後都要 X」、「不要再 Y」時：

1. 把使用者的描述整理成一條清晰、可執行的規範
2. 用 Edit 工具將新規範追加到下方 **Conventions** 區塊最末端
3. 格式必須遵守下方 **Convention Entry Format**
4. 追加完成後回報新增的規範編號與標題

### Convention Entry Format

每條規範以下列格式記錄：

```markdown
### C{編號}. {簡短標題}

**規則**：{一句話說明要做什麼 / 不要做什麼}

**原因**：{為什麼這樣訂 — 通常是過去踩過的坑、團隊偏好、或架構考量}

**適用範圍**：{什麼情境下要套用 — e.g. 所有 validator、僅 device API、只有在寫新功能時}

**範例**（選填）：
\`\`\`ts
// ✅ 正確
...

// ❌ 錯誤
...
\`\`\`
```

新增規範時，編號取當前最大編號 + 1。

---

## Conventions

<!-- 新規範追加到本區塊最末端。保持編號連續。 -->

### C1. 錯誤一律用 BusinessException

**規則**：Service/Repository `throw new XxxException(msg, details?)`，Controller 用 `try/catch` + `handleError(error, res, "op name")`。禁止自組 `res.status().json()`、禁止 `throw new Error()`、Service 不可碰 `res`。

**原因**：統一 response 格式、HTTP status 由 exception 集中管理、分層乾淨。

**類型**（完整列表見 [`business.exception.ts`](backend-v2/src/exceptions/business.exception.ts)）：

| Exception | HTTP | 時機 |
|---|---|---|
| `ValidationException` | 400 | 輸入驗證失敗 |
| `AuthenticationException` | 401 | 未登入/token 無效 |
| `PaymentRequiredException` | 402 | 餘額不足 |
| `PermissionDeniedException` | 403 | 無權限 |
| `ResourceNotFoundException` | 404 | 查無資源 |
| `ConflictException` | 409 | 重複/狀態衝突 |
| `UnprocessableEntityException` | 422 | 語意上無法處理 |
| `DatabaseOperationException` | 500 | DB 錯誤（repo `.catch` 包裝） |
| `ExternalServiceException` / `FirebaseException` | 502 | 第三方 API 失敗 |
| `FeatureUnavailableException` | 503 | 功能暫時關閉 |

**範例**：
```ts
// Service
if (!avatar) throw new ResourceNotFoundException(`Avatar not found: ${id}`);

// Repository
return prisma.avatar.create({ data }).catch(() => {
  throw new DatabaseOperationException("Create avatar failed");
});

// Controller
try { ... } catch (error) { handleError(error, res, "get avatar"); }
```

**注意**：優先用現有 exception；有 domain 特殊處理才新增子類放 `src/exceptions/{domain}.exception.ts`；`details` 不可放敏感資訊。

### C2. Controller 禁止直接呼叫 Repository

**規則**：Controller 只能 import / 呼叫 `@/services` 的 service，**不得** import `@/repository` 或任何 `*.repository.ts`。所有資料存取都必須透過 service 層轉交。即使是單純的 CRUD passthrough（controller 只把 repo 結果原封不動回傳），也必須經過 service。

**原因**：
- 守住分層：Controller = HTTP、Service = 業務邏輯、Repository = 資料存取，三者職責不能混
- 業務邏輯有地方住：跨 repo 的協作（trans­action、事件發送、cache 失效、扣點）只能住在 service；一旦 controller 直接碰 repo，邏輯會散逸到 controller
- 可重用：同一個業務動作可能被多個 controller（device API / admin API / webhook）或 worker 呼叫，邏輯集中在 service 才不會複製
- 可測試：Service 可脫離 Express 單元測試；controller 直接碰 repo 會讓測試被迫 mock DB 或起 HTTP server
- 一致性優先於 DRY：今天沒業務邏輯不代表永遠沒有，一致的 pipeline 讓新人不用判斷「這條 API 可不可以跳過 service」

**適用範圍**：所有 `src/controllers/**/*.controller.ts`。包含 admin、device、webhook 等所有 controller。新寫的 controller 必須遵守；既有違規檔案（已知至少 10 個）應在修改時順手搬到 service，或安排專門的 refactor PR。

**範例**：
```ts
// ❌ 錯誤：controller 直接 import repository
import { avatarRepository } from "@/repository";

async getById(req: Request, res: Response) {
  try {
    const avatar = await avatarRepository.findById(req.params.id);
    res.json({ data: avatar });
  } catch (error) { handleError(error, res, "get avatar"); }
}

// ✅ 正確：controller 只認 service
import { avatarService } from "@/services";

async getById(req: Request, res: Response) {
  try {
    const avatar = await avatarService.getById(req.params.id);
    res.json({ data: avatar });
  } catch (error) { handleError(error, res, "get avatar"); }
}

// ✅ 即使 service 內部只是 passthrough，仍要寫這一層
// avatar.service.ts
async getById(id: string) {
  return avatarRepository.findById(id);
}
```

**例外**：無例外。若確實遇到 service 會變成純 wrapper 而覺得冗贅，請在 service 的 method 留 TODO 註記未來可能加入的業務邏輯位置（權限、cache、事件等），而不是跳過 service。