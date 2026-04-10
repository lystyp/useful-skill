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

### C3. 設計必須符合業界標準（Design Patterns + Clean Code）

**規則**：在產生新程式碼、重構或做架構決策之前，必須以「熟讀 Design Patterns（GoF）與 Clean Code」的水準思考並給出**符合業界標準**的設計。不可只追求「能跑就好」，也不可堆砌模式炫技。具體要求：

1. **SOLID 必須守**：
   - **S**ingle Responsibility — 一個 class / function 只做一件事
   - **O**pen/Closed — 加新能力靠「加檔案」而不是「改既有檔案的 switch」（例如 C2 之外的 TTS provider 範例：新增 provider 不該改 `ttsService`）
   - **L**iskov — 子類 / 實作不能偷偷改變契約語意
   - **I**nterface Segregation — 介面要小、要切；不要逼 client 依賴它用不到的 method
   - **D**ependency Inversion — 高層依賴抽象，不依賴具體實作（例如 controller 依賴 `TtsProvider` interface，不依賴 `AzurePersonalVoiceService` class）

2. **Clean Code 基本功必須守**：
   - **命名**表達意圖（`calculateCost` 而非 `calc`、`ttsProvider` 而非 `svc`）
   - **函式短小**（一個 function 只做一層抽象、建議 20 行內）
   - **避免 magic number / magic string**（抽常數或 enum）
   - **避免深層巢狀**（early return、guard clause）
   - **註解解釋「為什麼」而非「做什麼」**（code 該自己解釋「做什麼」）
   - **DRY** 但要與 WET / 「rule of three」取得平衡（兩處重複可容忍，三處就該抽）

3. **選用設計模式前先問三個問題**：
   - 有沒有真的需要這個模式？還是想炫技？（YAGNI）
   - 專案既有慣例是否已經解決這個問題？（一致性優先於理論最佳）
   - 加進去之後，團隊其他人讀得懂嗎？

4. **當使用者的需求可以用多種方式實作時**，agent 必須：
   - 明確說明有哪幾種主流做法（而不是只給一個）
   - 點出每種做法的 trade-off（複雜度、可擴展性、一致性、成本）
   - 推薦一個並說明為什麼，但把決定權交回使用者
   - 若不確定業界現況，應配合 `research-industry-practices` skill 查證，而不是憑印象回答

**原因**：
- 避免「程式能跑但設計爛」的技術債累積，後續重構成本遠高於一開始寫對
- 本專案長期要支援多種外部 provider、多種業務規則，沒有良好抽象會變成 if/else 地獄
- AI 產的 code 容易出現「能跑但違反 SOLID」的反模式（例如 God Service、把所有邏輯塞 controller、靠 switch 換實作），必須明文守門
- 使用者有權知道自己的選擇在業界是不是主流做法，而不是被 agent 帶風向

**適用範圍**：**所有**程式碼產出與架構討論，包含新功能、重構、bug fix、review。對既有違反規範的程式碼，原則是「修改到它時順手改善」，不要求一次大規模重寫。

**反面示範**：
```ts
// ❌ God Service：一個 class 塞所有業務（違反 SRP）
class UserService {
  createUser() {}
  sendEmail() {}
  chargePayment() {}
  generateAvatar() {}
  // ... 30 個方法
}

// ❌ 用 if/else 判斷 provider（違反 OCP，加 provider 要改這裡）
async function generateTts(provider: string, text: string) {
  if (provider === "azure") return azureImpl(text);
  else if (provider === "google") return googleImpl(text);
  else if (provider === "elevenlabs") return elevenImpl(text);
  // 每加一家都要改這個 function
}

// ❌ Magic number + 不表達意圖的命名
function calc(t: string) {
  return t.length * 0.5 + (t.match(/[\u4E00-\u9FFF]/g)?.length ?? 0) * 1.5;
}
```

```ts
// ✅ 遵守 OCP / DIP：新增 provider 不用改呼叫端
interface TtsProvider {
  generateSpeech(request: TtsRequest): Promise<TtsResult>;
  calculateCost(request: TtsRequest): CostInfo;
}
// 加新 provider = 加一個 class，不用改任何 consumer

// ✅ 命名表達意圖、常數命名、guard clause
const TTS_RATE = { CHINESE: 1.5, ENGLISH: 0.5 } as const;

function calculateTtsTokens(text: string): number {
  if (!text) return 0;
  const chineseCount = countChineseChars(text);
  const englishCount = countEnglishChars(text);
  return Math.ceil(chineseCount * TTS_RATE.CHINESE + englishCount * TTS_RATE.ENGLISH);
}
```

**備註**：此規範與 C1、C2 不衝突，而是**更高階的指導原則**。C1/C2 是具體規則，C3 是背後的設計哲學。當未來新增 C4、C5… 等具體規則時，它們也必須先通過 C3 的精神檢驗。