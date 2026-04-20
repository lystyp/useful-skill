---
name: project-conventions
description: 專案的程式碼規範與慣例集合。任何 agent 在產生新程式碼、修改既有程式碼、或 review code 之前都必須先閱讀此 skill。同時支援新增規範：當使用者說「加一條規範」、「記下這個慣例」、「以後都要這樣寫」時，使用此 skill 將新規範追加到下方 Conventions 區塊。
user-invocable: true
argument-hint: "[新規範內容（選填）]"
input: 可選的新規範描述
output: 閱讀並遵循規範，或將新規範追加到本檔案
---

# Project Conventions

專案的程式碼規範集合。所有 agent 在產生或修改 code 之前都必須先讀完此檔，並遵守下方列出的每一條規範。

本檔內容面向**一般後端 web service**（分層架構 + RESTful API + 關聯式資料庫 + 分層測試），不綁定任何特定語言或框架。範例一律使用技術棧中立的偽碼（pseudo-code）。落地到 Node.js / TypeScript / Python / Go / Java / Kotlin / C# 等語言時，請依各語言慣例實作，以規範背後的「意圖」為準。

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

**適用範圍**：{什麼情境下要套用 — e.g. 所有 validator、僅 client-facing API、只有在寫新功能時}

**範例**（選填）：
（用技術棧中立的偽碼描述正反面對照）
```

新增規範時，編號取當前最大編號 + 1。

---

## Conventions

<!-- 新規範追加到本區塊最末端。保持編號連續。 -->

### C1. 錯誤一律用領域例外（Domain Exception），由統一 handler 轉成 HTTP 回應

**規則**：
- Service / Repository 發現錯誤 → 直接 `throw` 對應語意的「領域例外類別」（Domain Exception），不回 HTTP status、不碰 response 物件
- Controller（或 HTTP adapter 層）用 `try / catch` 接住例外，交給**統一的 error handler** 把例外轉成對應的 HTTP response
- 禁止：Service 自組 HTTP response / 裸 `throw Error("...")` / Controller 自己判斷 status code

**原因**：統一 response 格式、HTTP status 由 exception 集中管理、分層乾淨。上層框架改變（Express → Fastify、HTTP → gRPC）時，領域例外不需要動。

**HTTP Status 與情境對照**（類別名稱為**建議**，各專案可自訂；重點是「HTTP status 與情境的對應」要在團隊內一致）：

| HTTP | 情境 | 常見類別名範例 |
|---|---|---|
| 400 | 輸入驗證失敗、格式錯誤 | `ValidationException` / `InvalidInputError` / `BadRequestError` |
| 401 | 未登入、token 無效 / 過期 | `AuthenticationException` / `UnauthenticatedError` |
| 402 | 餘額不足、需要付費 | `PaymentRequiredException` |
| 403 | 已登入但無權限 | `PermissionDeniedException` / `ForbiddenError` |
| 404 | 查無資源 | `ResourceNotFoundException` / `NotFoundError` |
| 409 | 重複資源、狀態衝突 | `ConflictException` |
| 422 | 格式正確但語意上無法處理（業務規則衝突） | `UnprocessableEntityException` |
| 500 | 資料庫操作失敗 | `DatabaseOperationException` |
| 502 | 第三方 API 回應失敗 | `ExternalServiceException` / `UpstreamError` |
| 503 | 功能暫時關閉 / 維護中 | `FeatureUnavailableException` / `ServiceUnavailableError` |
| 504 | 第三方 API 超時 | `UpstreamTimeoutException` |

專案啟動時先挑一組類別名，並集中定義於一個 exceptions 模組（例如 `exceptions/` 或 `domain/errors/`），全專案共用。

**範例**（pseudo-code）：
```
// Service 層：只關心領域語意，不知道 HTTP 存在
service.getOrder(id):
    order = repository.findById(id)
    if order is null:
        throw ResourceNotFoundException("Order not found: " + id)
    return order

// Repository 層：DB 錯誤包成 DatabaseOperationException
repository.createOrder(data):
    try:
        return orm.orders.create(data)
    catch dbError:
        throw DatabaseOperationException("Create order failed", cause = dbError)

// Controller / HTTP adapter：只負責轉交
controller.getOrder(request, response):
    try:
        order = service.getOrder(request.params.id)
        return respond(response, 200, order)
    catch error:
        return handleError(error, response, operation = "get order")

// 統一 error handler 根據 exception 類別決定 HTTP status
handleError(error, response, operation):
    if error is ResourceNotFoundException:   return respond(response, 404, { error: error.message })
    if error is ValidationException:         return respond(response, 400, { error: error.message })
    if error is PermissionDeniedException:   return respond(response, 403, { error: error.message })
    if error is DatabaseOperationException:  return respond(response, 500, { error: "internal" })
    // ... 其他類別
    log.error(operation, error)
    return respond(response, 500, { error: "unknown" })
```

**注意**：
- 優先使用既有 exception 類別；domain 有特殊處理才新增子類
- exception `details` / `cause` 不可放敏感資訊（token、密碼、個資明文、完整 stack trace 若會回給客戶端）

### C2. Controller 禁止直接呼叫 Repository / Data Layer

**規則**：Controller 只能呼叫 Service 層，**不得**直接碰 Repository、ORM、DB driver、或任何資料存取層。即使是單純的 CRUD passthrough（controller 只把 repo 結果原封不動回傳），也必須經過 Service。

**原因**：
- 守住分層：Controller = HTTP、Service = 業務邏輯、Repository = 資料存取，三者職責不能混
- 業務邏輯有地方住：跨 repo 的協作（transaction、事件發送、cache 失效、扣點）只能住在 service；一旦 controller 直接碰 repo，邏輯會散逸到 controller
- 可重用：同一個業務動作可能被多個 controller（client-facing API / admin API / webhook）或 worker 呼叫，邏輯集中在 service 才不會複製
- 可測試：Service 可脫離 HTTP 框架做單元測試；controller 直接碰 repo 會讓測試被迫 mock DB 或起 HTTP server
- 一致性優先於 DRY：今天沒業務邏輯不代表永遠沒有，一致的 pipeline 讓新人不用判斷「這條 API 可不可以跳過 service」

**適用範圍**：所有 controller 檔案，不分 admin / client-facing / webhook。新寫的 controller 必須遵守。對既有違規檔案的處置（若有）：修改時順手搬到 service、或排專門的 refactor PR。

**範例**（pseudo-code）：
```
// ❌ 錯誤：controller 直接依賴 repository
controller.getOrder(request, response):
    try:
        order = orderRepository.findById(request.params.id)    // ← 跨層
        return respond(response, 200, { data: order })
    catch error:
        return handleError(error, response, "get order")

// ✅ 正確：controller 只認 service
controller.getOrder(request, response):
    try:
        order = orderService.getById(request.params.id)
        return respond(response, 200, { data: order })
    catch error:
        return handleError(error, response, "get order")

// ✅ 即使 service 內部只是 passthrough，仍要保留這一層
service.getById(id):
    return orderRepository.findById(id)
    // TODO: 未來加 permission check / cache / event 時就住在這裡
```

**例外**：無例外。若遇到 service 會變成純 wrapper 而覺得冗贅，請在 service 的 method 留 TODO 註記未來可能加入的業務邏輯位置（權限、cache、事件等），而不是跳過 service。

### C3. 設計必須符合業界標準（Design Patterns + Clean Code）

**規則**：在產生新程式碼、重構或做架構決策之前，必須以「熟讀 Design Patterns（GoF）與 Clean Code」的水準思考並給出**符合業界標準**的設計。不可只追求「能跑就好」，也不可堆砌模式炫技。具體要求：

1. **SOLID 必須守**：
   - **S**ingle Responsibility — 一個 class / function 只做一件事
   - **O**pen/Closed — 加新能力靠「加檔案」而不是「改既有檔案的 switch」（例：新增一家 payment gateway 不該改 `paymentService` 本體）
   - **L**iskov — 子類 / 實作不能偷偷改變契約語意
   - **I**nterface Segregation — 介面要小、要切；不要逼 client 依賴它用不到的 method
   - **D**ependency Inversion — 高層依賴抽象，不依賴具體實作（例：controller 依賴 `PaymentProvider` interface，不依賴 `StripeService` 具體類別）

2. **Clean Code 基本功必須守**：
   - **命名**表達意圖（`calculateCost` 而非 `calc`、`paymentProvider` 而非 `svc`）
   - **函式短小**（一個 function 只做一層抽象、建議 20 行內）
   - **避免 magic number / magic string**（抽常數或 enum）
   - **避免深層巢狀**（early return、guard clause）
   - **註解解釋「為什麼」而非「做什麼」**（code 該自己解釋「做什麼」）
   - **DRY** 但要與 WET /「rule of three」取得平衡（兩處重複可容忍，三處就該抽）

3. **選用設計模式前先問三個問題**：
   - 有沒有真的需要這個模式？還是想炫技？（YAGNI）
   - 專案既有慣例是否已經解決這個問題？（一致性優先於理論最佳）
   - 加進去之後，團隊其他人讀得懂嗎？

4. **當使用者的需求可以用多種方式實作時**，agent 必須：
   - 明確說明有哪幾種主流做法（而不是只給一個）
   - 點出每種做法的 trade-off（複雜度、可擴展性、一致性、成本）
   - 推薦一個並說明為什麼，但把決定權交回使用者
   - 若不確定業界現況，應配合 `research-industry-practices` skill（或等效查證流程）查證，而不是憑印象回答

**原因**：
- 避免「程式能跑但設計爛」的技術債累積，後續重構成本遠高於一開始寫對
- 多數專案長期都會需要支援多種外部 provider、多種業務規則，沒有良好抽象會變成 if/else 地獄
- AI 產的 code 容易出現「能跑但違反 SOLID」的反模式（例如 God Service、把所有邏輯塞 controller、靠 switch 換實作），必須明文守門
- 使用者有權知道自己的選擇在業界是不是主流做法，而不是被 agent 帶風向

**適用範圍**：**所有**程式碼產出與架構討論，包含新功能、重構、bug fix、review。對既有違反規範的程式碼，原則是「修改到它時順手改善」，不要求一次大規模重寫。

**反面示範**（pseudo-code）：
```
// ❌ God Service：一個 class 塞所有業務（違反 SRP）
class UserService:
    createUser() { ... }
    sendEmail() { ... }
    chargePayment() { ... }
    generateReport() { ... }
    // ... 30 個方法

// ❌ 用 if/else 判斷 provider（違反 OCP，加 provider 要改這裡）
function chargePayment(provider, amount):
    if provider == "stripe":  return stripeImpl(amount)
    if provider == "paypal":  return paypalImpl(amount)
    if provider == "adyen":   return adyenImpl(amount)
    // 每加一家都要改這個 function

// ❌ Magic number + 不表達意圖的命名
function calc(items):
    return sum(items, x => x.price * 0.05 + x.qty * 1.5)
```

```
// ✅ 遵守 OCP / DIP：新增 provider 不用改呼叫端
interface PaymentProvider:
    charge(request)  -> ChargeResult
    refund(chargeId) -> RefundResult

class StripeProvider implements PaymentProvider: ...
class PaypalProvider implements PaymentProvider: ...
// 加新 provider = 加一個 class，不用改任何 consumer

// ✅ 命名表達意圖、常數命名、guard clause
const FEE_RATE = { TAX: 0.05, HANDLING_PER_ITEM: 1.5 }

function calculateOrderTotal(items):
    if items is empty: return 0
    subtotal    = sum(items, item => item.price)
    handlingFee = items.length * FEE_RATE.HANDLING_PER_ITEM
    return subtotal * (1 + FEE_RATE.TAX) + handlingFee
```

**備註**：此規範與 C1、C2 不衝突，而是**更高階的指導原則**。C1/C2 是具體規則，C3 是背後的設計哲學。當未來新增 C4、C5… 等具體規則時，它們也必須先通過 C3 的精神檢驗。

### C4. 測試中每個斷言區塊前要加註解說明在斷言什麼（並用 Given-When-Then 結構）

**規則**：測試檔（unit / integration / e2e）中每一個 test case 必須遵守 **Given-When-Then**（等同 Arrange-Act-Assert）結構，並以註解明確標示三個區段：

- `// Given: ...` — 準備資料 / 狀態，描述情境（「在什麼前提下」）
- `// When:  ...` — 執行被測對象（通常 1~2 行），描述動作（「做了什麼」）
- `// Then:  ...` — 斷言結果，描述**意圖**（「應該發生什麼」），不是覆述斷言本身的字面動作

**Then 區段內部**再依斷言主題切子區塊，每個子區塊前加一行註解說明「這個區塊要斷言的是什麼事實」。同一個邏輯主題的多個斷言算一個子區塊共用一條註解；主題不同就分開。

**原因**：
- 測試失敗時（CI 紅燈、review 別人 PR、半年後回來改），讀者第一眼要看懂「這個測試在守護什麼契約」，不該先 parse 斷言才能還原意圖
- 斷言往往長得很像（`assert x == y`），沒有註解就要從上下文倒推，浪費時間
- 強迫作者在寫 assertion 時先講清楚意圖，能順手抓到「我到底在測什麼」不清晰的測試
- 註解也扮演測試內部的「小節標題」，讓一個 test case 的結構一目了然（Arrange / Act / Assert 中的 Assert 常被忽略結構化）

**適用範圍**：所有測試檔案（unit / integration / e2e / contract test）。新寫的測試必須遵守；既有測試修改時順手補上。

**範例**（pseudo-code）：
```
// ✅ 正確：Given / When / Then 三段明確分區，Then 內部再依主題切子區塊
test "checkout applies discount and decrements stock":
    // Given: 一個有效的 checkout session，內含兩件商品與一張折價券
    session = seedCheckoutScenario(
        items  = [
            { productId: "p1", quantity: 2, unitPrice: 100 },
            { productId: "p2", quantity: 1, unitPrice: 50 },
        ],
        coupon = { code: "SAVE10", percentage: 10 },
    )

    // When: 使用者確認結帳
    result = checkoutService.confirm(session.id, session.userId)

    // Then:
    // 斷言：回傳的 order 套用了折價券後的總金額（正確算式：(200+50) * 0.9 = 225）
    assert result.order.total == 225
    assert result.order.items.length == 2

    // 斷言：兩件商品的庫存各被扣掉對應數量（非覆寫、累加式扣款）
    p1 = productRepository.findById("p1")
    p2 = productRepository.findById("p2")
    assert p1.stock == 8    // 原本 10 - 2
    assert p2.stock == 4    // 原本 5 - 1

    // 斷言：折價券被標記為「已使用」，不能重複套用
    coupon = couponRepository.findByCode("SAVE10")
    assert coupon.usedBy == session.userId
    assert coupon.usedAt is not null

// ❌ 錯誤：沒註解，讀者要自己倒推意圖
test "checkout applies discount and decrements stock":
    result = checkoutService.confirm(sessionId, userId)
    assert result.order.total == 225
    assert result.order.items.length == 2
    p1 = productRepository.findById("p1")
    assert p1.stock == 8
    coupon = couponRepository.findByCode("SAVE10")
    assert coupon.usedBy == userId

// ❌ 錯誤：註解只是覆述斷言本身，沒傳達意圖
// assert total equals 225
assert result.order.total == 225
// assert stock equals 8
assert p1.stock == 8
```

**備註**：此規範與 C3「註解解釋為什麼而非做什麼」精神一致 — 註解是寫給未來讀者看的意圖說明，不是給 code 配旁白。

### C5. 測試檔最上方要宣告測試範圍（scope）

**規則**：每個測試檔的最頂端（或最外層 test suite 上方）必須用檔頭註解明確標示：

1. **測試層級**：Unit / Integration / E2E / Contract（哪一種測試）
2. **跨度**：真正跑過哪些層（例：`Service → Repository → ORM → Database`、或 `Service（repo 全 mock）`）
3. **真實依賴 vs 替身**：DB 是真 DB（Testcontainers / Docker Compose）？Cache 被 mock？外部 API 用 mock server？講清楚
4. **被測對象（SUT）**：被測的 class / function / API 路徑

**原因**：
- 光看檔名（`xxx_service_test.*`）無法判斷這支測試是 pure unit 還是跑到真 DB，CI 慢 / 穩定度 / 本機要不要開 docker 都取決於此
- 讀者（含 AI）讀測試前會先問「這支測試在保護哪一段？」，scope 宣告直接回答，不用先讀完 imports + setup 才推理出來
- 修改測試時可以立刻判斷新增的斷言「在範圍內嗎」—— 例如 unit scope 的測試不該 assert HTTP status
- 方便 code review 判斷測試層級是否選對（有些邏輯應該寫 unit 不該寫 integration）

**適用範圍**：所有測試檔。新寫的測試必須有；既有測試修改時補上。

**範例**（pseudo-code，JSDoc 風格；其他語言可用該語言的註解等效表達）：
```
/**
 * Integration test — CheckoutService.confirm
 *
 * Scope: Service → Repository → ORM → Database（真 DB，透過 Testcontainers 啟動）
 * Mocks: 無（所有資料存取都走真 DB）
 * SUT:   CheckoutService.confirm()
 *
 * 目的：驗證「結帳流程」整條路徑的資料一致性（order / stock / coupon）
 */

/**
 * Unit test — calculateOrderTotal
 *
 * Scope: 單一 pure function，無外部依賴
 * Mocks: N/A
 * SUT:   calculateOrderTotal(items)
 */

/**
 * Unit test — UserService.register
 *
 * Scope: Service 層邏輯，不跨 Repository
 * Mocks: userRepository（stub）、emailService（stub）
 * SUT:   UserService.register()
 */

// ❌ 錯誤：沒有 scope 宣告，讀者要自己從 imports 推理
test_suite "CheckoutService": ...

// ❌ 錯誤：只寫「integration test」但沒說跨到哪裡
/**
 * Integration test for checkout service
 */
```

**備註**：scope 宣告和 C4 的斷言意圖註解互補 — C5 告訴讀者「這支測試覆蓋到多大」，C4 告訴讀者「每個 assert 在保護什麼契約」。兩者合起來測試檔才算自我解釋。

### C6. 改動範圍節制 — 先做最小改動、大改動先提問

**規則**：收到 code editing 需求時，只做「完成需求所需的最簡單改動」，不順手 refactor、不順手修其他 smell、不順手補 logging / 文件 / 註解。完成後把工作切成兩部分回報：

1. **基本改動**：實際為了滿足本次需求而做的最小改動清單。
2. **建議但未做的大改動**：過程中看到想順手做、但不屬於本次需求的改動。**不要直接動手**，改以提問形式列出：
   - 看到什麼 smell / 可改善點（指出具體檔案與行號）
   - 想怎麼改
   - 這個改動的風險 / 要注意的事
   - 問使用者「要不要一起改」

**等使用者明確回答後才能動第二部分。** 即使你覺得「只是順手一點小改」，也要拉到第二部分問，不要自己決定。

**例外**：typo、明顯 bug — 若不修會讓本次需求壞掉，可以一起修，但必須在第一部分顯著標示「附帶修掉 XXX 因為不修會 YYY」。

**原因**：
- 避免擅自改動造成 diff 膨脹，PR / commit 被混入跟主題無關的改動，review 成本變高
- 減少 merge 衝突：碰到跟其他人工作區域重疊的「順手改」很容易害別人 rebase
- 讓使用者掌握改動範圍；AI 的「我覺得這樣比較好」不等於使用者的設計意圖
- 大改動（尤其涉及命名、分層、interface）常有使用者才知道的約束（其他檔案的依賴、未 commit 的 WIP、團隊偏好），直接動手容易誤傷

**適用範圍**：所有 code editing task，包含：
- 使用者明確要求的改動（「幫我加 X」、「修掉 Y」）
- **refactor 任務也適用** — 不是看到可改點就全部自動動手，超出當下要求的改點先列出來問
- bug fix（修 bug 歸第一部分，看到順手想整理的結構改動歸第二部分）

**範例**：

情境：使用者說「在 `UserService.getById` 加 cache」。
AI 打開檔案看到：
- 需求本身：加 cache ← **第一部分**
- 順便看到方法名 `getById` 想改成 `findUserById`
- 順便看到全套 import 某套 utility library
- 順便看到缺少 method 註解

```
# ✅ 正確回報格式

## 第一部分（基本改動）
- user.service: 在 `getById` 加上 cache（TTL 60s），cache miss 時 fallback 到 repository

## 第二部分（建議但未做，請告訴我要不要改）
1. 方法命名：目前 `getById` 可以改成 `findUserById` 更表意
   - 風險：其他 controller / test 有 3 處引用，要連動改
   - 要一起改嗎？
2. import 優化：目前全套 import utility library 會讓 bundle size 增加
   - 建議改為只 import 實際使用的 function
   - 風險：低，純內部改動
   - 要一起改嗎？
3. 缺註解：`getById` 和新加的 cache 相關方法都沒 method-level 註解
   - 建議補上方法用途與 cache TTL 說明
   - 要一起補嗎？
```

```
# ❌ 錯誤示範

## 改動
- 加 cache
- 順手把 getById 改名成 findUserById
- 順手優化 import
- 順手補註解
```

**備註**：此規則優先於 C3 的「Clean Code / SOLID 最佳化」傾向 — C3 描述的是「寫新 code 時該遵守的設計標準」，但面對既有 code，是否要「順手優化到 C3 標準」必須先經過 C6 的提問流程。

### C7. 命名與架構必須考慮未來擴充性

**規則**：改 code 時不能只看「當下這個 feature」，必須站在「這個 domain 未來還會長什麼」的視角做命名、檔案分類、模組切分、設計模式選擇。具體檢查點：

1. **Controller 命名以 domain 為主體，不綁定當前 action**
   - ✅ `OrderController`（domain）
   - ❌ `OrderListController` / `ListController`（綁在 list 這個 action）
2. **Service 命名視 domain 複雜度而定**：
   - 簡單 CRUD → 一個 domain service（`OrderService`）
   - 複雜 domain 可切 use-case service（`OrderCheckoutService`、`OrderCancellationService`），**但仍以 domain 名前綴**
   - 不可出現不帶 domain 的 `CheckoutService` / `CancellationService`（除非該 use-case 本身就是獨立 domain）
3. **檔案分類按 domain 分資料夾**：
   - ✅ `controllers/order/{list,detail,create,cancel}.*`
   - ❌ 散落在 `controllers/` 平面下，domain 邊界消失
   - 未來加新功能時，domain 資料夾就是它的家，不用到處找
4. **設計模式預留擴充點**：
   - 看到「現在只有一家 provider / 一種策略」不代表永遠如此；domain 若明顯會擴張（例如 payment gateway、notification channel、auth provider、storage backend），一開始就該預留 Strategy / Factory interface
   - 不是要過度設計，是要避開「加第二個實作時必須 rewrite caller」的坑

**流程要求**：每次新增 controller / service / repository 檔案時，必須先自問：
- 這個 domain 未來還會有哪些功能？
- 若答案是「還會有更多」→ 命名以 domain 為主，不綁 action
- 若答案是「就這一個」→ 可綁 action，但必須在檔案或 method 註解標明「此為一次性，不再擴充」

**例外**：一次性、確定不會擴充的 utility — 例如 migration script、一次性報表、帶時效的 marketing script — 可以用 action-specific 命名，但仍要註解標明「此為一次性」。

**原因**：
- 命名是技術債的高發地：一開始綁死 action，後續要改名得動多處 import（typed import、route 引用、DI 註冊、測試），工程師常因為怕改動太大而「將就」下去，讓 codebase 越來越難維護
- 架構邊界一旦建立就難改：檔案放錯資料夾、類別責任切錯、沒預留 interface，這些問題在第二個 feature 加入時才浮現，代價是整包重構
- AI 容易落入「只看當下需求」的反模式：接到「做列表」就叫 `ListService`、接到「做建立」就叫 `CreateService`，完全忽略 domain 層級的長期結構。必須明文守門
- 好的命名讓未來的擴充變成「加檔案」而不是「改現有檔案」（呼應 C3 的 OCP）

**適用範圍**：所有新增 / 重構的 controller、service、repository、validator、routes 檔。同樣適用於測試檔、helper、types 的命名。

**範例**：

```
當下需求：做一隻 GET /orders 查詢訂單清單 API
未來可預見：建立 / 詳細檢視 / 取消 / 退款 / 評價 …

# ✅ 考慮未來性的命名
controllers/order.controller.*
  class OrderController:
    listOrders(request, response)   // 未來可加 getOrderById, cancelOrder 等

services/order-list.service.*           // use-case service，以 domain 前綴
services/order-checkout.service.*       // 未來加
services/order-cancellation.service.*   // 未來加

routes/order.routes.*                   // domain 為主的 routes 檔
  route GET  "/"     → listController   // 未來加 route DELETE "/:id" → ...

# ❌ 反模式
controllers/order-list.controller.*              // 綁 list action，未來得改名
  class OrderListController: ...

controllers/notification-send.controller.*       // 每個 action 一個 class，domain 被切碎
  class NotificationSendController: ...
controllers/notification-read.controller.*
  class NotificationReadController: ...
// 同一個 notification domain 被拆成多個 controller class，共用邏輯難住

controllers/user-auth.controller.*               // domain 與 concern 混雜
  class UserAuthController: ...
// 「user」還是「auth」？未來加 auth 相關但非 user 的功能（如 apiKey）會尷尬

controllers/list.controller.*                    // 連 domain 名都沒有
  class ListController: ...
```

**備註**：本規範與 C3（SOLID / Open-Closed）呼應 — 未來性好的命名 = 擴充時不用改現有檔案。與 C6 的互動：「做列表功能時 agent 提議把 controller 叫 `OrderController` 而非 `OrderListController`」不算 C6 的「順手改動」，這是新檔案命名的當下決策，agent 必須主動提出最面向未來的命名，但最終由使用者拍板。
