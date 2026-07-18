# 應用層安全 Security Code Review 規範（per-endpoint 端到端追鏈）

> 審查單位是**單一 endpoint**：從請求入口出發，沿「請求入口 → 請求處理 → 商業邏輯 → 資料存取 → 回應路徑」追整條資料流，逐條對照下列訊號。與 `api-robustness.md`（效能 / Bug / 併發）同為端到端追鏈、不同 lens。
> 骨幹用 **OWASP API Security Top 10 (2023)**。後端最常漏的是**授權**（authorization）而非認證——認證通常有共用攔截器 / 中介層一次做掉，但每個物件 / 欄位 / 功能的授權必須在鏈路內逐一實作，最容易被省略。

## 核心原則（四類最高頻缺口，按風險排序）

1. **BOLA / IDOR（API1，最嚴重最常見）**：endpoint 收到請求帶的 objectId，只驗「有登入」就拿去查 / 改，沒驗「這個登入者是否有權存取這個物件」。典型病灶：資料存取查詢只以主鍵過濾，未帶擁有者／租戶範圍條件（`ownerId` / `userId` / `tenantId`）。
2. **Mass Assignment / BOPLA（API3）**：把未經白名單過濾的請求內容整包交給寫入操作，讓使用者能寫不該由 client 控制的欄位（`role` / `balance` / `status` / `ownerId`）；或回應把整筆記錄 / 關聯樹序列化外洩。
3. **Broken Function Level Authorization（API5）**：管理／後台端點缺 role gate，或不同信任層級的入口共用同一段處理邏輯，繞過該側的授權假設。
4. **Injection**：參數化 / 綁定變數的查詢介面天生安全；風險在**以字串拼接組出查詢語句並帶入使用者輸入**、用「原始片段」逃生口（raw / literal 之類的 API）包住使用者資料而繞過參數化、以及**動態欄位名 / 排序鍵來自使用者輸入**（identifier 不可參數化，只能 allowlist）。

## 偵測訊號（per-endpoint）

> 逐條使用 TodoWrite 工具標記檢查進度。追這條 endpoint 的鏈路，逐條判斷。

**授權 — BOLA / IDOR（API1）**
- [ ] 資料存取查詢**只以主鍵過濾、無擁有者／租戶範圍條件**（`userId`/`tenantId`/`groupId`）→ 任何登入者可存取他人物件
- [ ] 授權只在入口驗「有 token」，但沒有任何一層驗「此 subject 擁有此 object」
- [ ] 巢狀資源（`/parent/{pid}/child/{cid}`）只驗 parent 歸屬，卻用 `cid` 直接查 child 沒驗它屬於該 parent
- [ ] ownership 檢查與實際寫入不在同一個查詢條件內（先查一次再改，TOCTOU）——理想是把 owner 條件併進更新／刪除的過濾條件

**授權 — 屬性層 / Mass Assignment（API3）**
- [ ] 請求內容整包（或 spread / 反序列化成物件後）直接交給新增／更新操作，未經白名單挑欄位 → 可寫 `role`/`balance`/`status`/`ownerId` 特權欄位
- [ ] 輸入 schema 未明列可接受欄位、未拒絕多餘欄位，多餘欄位被靜默放行往下游
- [ ] 回應直接回整筆記錄或整棵關聯樹，未經欄位白名單 / DTO 映射 → 外洩憑證雜湊、內部 audit 欄位、他人 PII、內部關聯 id

**授權 — 功能層（API5）**
- [ ] 管理／後台 endpoint 缺 role / permission gate，僅靠「有登入」
- [ ] 低信任側入口（對外／裝置端）掛到高信任側處理邏輯（或反之），繞過該側授權假設

**認證（API2）**
- [ ] 這條 endpoint 是否確實掛上認證（有無被放進 public allowlist 而不自覺）；token 過期 / 簽章 / issuer 驗證是否成立

**Injection**
- [ ] 查詢語句以字串拼接（或格式化字串 / 模板）組出並帶入使用者輸入，未走參數化 / 綁定變數
- [ ] 使用查詢介面的「原始片段」逃生口包住使用者資料，使該段被當作語句而非參數
- [ ] 動態排序鍵 / 欄位名 / 排序方向直接取自使用者輸入（identifier 不可參數化）

**其他**
- [ ] **SSRF**：拿使用者提供的 URL / host 去 fetch / 下載，未做 allowlist 或內網位址過濾
- [ ] **敏感資料外洩**：回應含 PII / 內部 ID / secrets / audit 欄位；error / log 印出 stack / secrets / 完整請求內容
- [ ] **Security Misconfiguration**：secrets / 金鑰 / 連線字串寫死在程式碼（非環境變數 / secret store）；錯誤處理對 client 回傳 verbose stack
- [ ] **資源耗用（API4）**：list endpoint 無分頁上限（筆數無上限 / 使用者可指定任意大 `limit`）；上傳 / 批次無大小、陣列長度上限
- [ ] **信任邊界驗證**：任何跨 trust boundary 的輸入（body/query/path/header）未經驗證即進入商業邏輯（護欄：不在 YAGNI 精簡範圍）

## 修法對照

| 訊號 | 修法 |
|------|------|
| BOLA：查詢只帶主鍵、無 owner | ownership 併進同一組過濾條件（主鍵 + owner）；查不到即 404/403，不要「先查再比對」 |
| 巢狀資源只驗 parent | child 的過濾條件同時帶自身 id 與 parent id（+ owner） |
| TOCTOU | 授權條件放進更新／刪除的過濾條件，靠「影響筆數為 0」判無權 |
| Mass assignment | 輸入 schema 明列可寫欄位並拒絕多餘欄位；特權欄位由伺服器端決定、永不由 client 帶入 |
| 回應外洩屬性 | 欄位白名單或回應 DTO 映射，絕不把整棵關聯樹原樣回傳 |
| 缺功能層 gate | 加 role/permission 檢查；不同信任層級的入口與處理邏輯嚴格分離 |
| 拼接查詢語句 | 用參數化 / 綁定變數；必須用原始語句時，使用者輸入一律以參數傳入 |
| 動態欄位 / 排序鍵 | allowlist 映射，拒 allowlist 外的鍵；方向限升冪／降冪兩值 |
| SSRF | URL scheme + host allowlist，擋私網 / metadata 位址，禁 redirect 到內網 |
| 敏感資料 / log | 回應走 DTO；log redact secrets/PII；錯誤處理對外只回一般化訊息 |
| Secrets 寫死 | 移到環境變數 / secret manager，程式只讀 config loader |
| 無分頁上限 | 筆數設伺服器端上限（clamp `limit`） |

## per-endpoint 追鏈提示（各角色看什麼）

> 以下是**概念角色**，不是特定框架或分層的層名。專案若無對應分層（單檔 handler、函式式、CQRS 等），就把該角色映射到最接近的位置；同一個檔案同時扮演多個角色時，同一段程式碼要用多個 lens 各看一遍。

- **請求入口（路由 / 端點宣告）**：屬哪個信任側？有無認證 / role gate / rate-limit？有無把低信任側入口綁到高信任側處理邏輯？public allowlist 有無不該放的 endpoint？
- **請求處理（解析輸入、組裝呼叫）**：每個輸入（path/query/body/header）是否都先過驗證且拒絕多餘欄位？有無整包請求內容往下傳？授權主體（userId 等）取自**驗過的 token** 還是誤信 client 帶的 id？
- **商業邏輯**：有無 object-level 授權判斷？特權欄位是伺服器端決定還是沿用 client 值？呼叫外部 URL / 昂貴操作有無 SSRF / 資源耗用防護？
- **資料存取（BOLA 最後防線也最常破口）**：每個查詢條件是否帶 owner / tenant？寫入的欄位集合是否來自白名單？有無字串拼接查詢 / 原始片段包使用者輸入 / 動態 identifier？回傳是否欄位白名單、筆數是否有上限？
- **回應路徑（往回追）**：最終回給 client 的物件是否經 DTO / 欄位白名單，沒帶憑證雜湊 / 內部 id / 他人 PII / audit 欄位 / 整棵關聯樹。

## 建議格式

標籤依 OWASP 分類：`[BOLA]`、`[Mass-Assignment]`、`[AuthZ]`、`[Injection]`、`[Data-Exposure]`、`[SSRF]`、`[Misconfig]`。

```
- **[BOLA]** {檔案}:{行數範圍}（endpoint: {method path}）
  - 情境：{哪個登入者用什麼 objectId 能碰到不該碰的資料}
  - 鏈路：{在哪個角色（請求處理／商業邏輯／資料存取）缺授權}
  - 建議：{把 owner 條件併進查詢條件 / 輸入白名單 / 回應 DTO 收斂等具體修法}
```
