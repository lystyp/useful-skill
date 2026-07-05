---
name: test-writing-style
description: Unit Test 與 Integration Test 的寫作風格規範：檔頭註解、測試命名、段落排版、import 分群、斷言寫法、錯誤路徑組織。本 skill 專注在「測試程式碼本身怎麼排版、怎麼寫註解、怎麼組織結構」。當撰寫或 review 測試程式碼的格式與風格時使用。
user-invocable: false
---

# Test Writing Style Guide

本 skill 規範測試程式碼的**排版、註解、命名、結構**。不綁定語言或框架，但範例以 TypeScript + Jest 風格呈現（觀念通用）。

> 本 skill 只管「測試程式碼怎麼寫才好讀好維護」（排版、命名、斷言、結構）；「測什麼、怎麼選 mock」的方法論不在範圍內。

---

## 1. 檔頭 JSDoc — 讓人不用讀 code 就知道這份測試在幹嘛

每份測試檔頂端寫一個 JSDoc block，包含四個欄位：

```ts
/**
 * <測試類型> — <被測對象>
 *
 * Scope:  <被測物呼叫了哪些層>
 * Mocks:  <哪些依賴被替換 / 無>
 * SUT:    <被測的函式或 method 全名>
 *
 * 目的：<一句話說明這組測試要驗證什麼>
 */
```

### 範例

**Integration test**：
```ts
/**
 * Integration test — OrderService.placeOrder
 *
 * Scope:  Service → Repository → DB (real)
 * Mocks:  無 — 所有資料存取走真 DB
 * SUT:    OrderService.placeOrder(userId, items)
 *
 * 目的：驗證下單流程的資料一致性 — 庫存扣減、訂單建立、wallet 扣款
 */
```

**Unit test**：
```ts
/**
 * Unit test — expandRewardItem
 *
 * Scope:  純函式，無外部依賴
 * Mocks:  無
 * SUT:    expandRewardItem(spec)
 *
 * 目的：驗證獎勵展開邏輯 — VOICE_POSTCARD 按數量拆分、COIN 保持單筆
 */
```

**有 mock 的 unit test**：
```ts
/**
 * Unit test — NotificationService.sendReminder
 *
 * Scope:  Service（邏輯層）
 * Mocks:  EmailClient (stub), UserRepository (stub)
 * SUT:    NotificationService.sendReminder(userId)
 *
 * 目的：驗證發送條件判斷 — 已讀不發、未讀才發、過期不發
 */
```

### 為什麼

- 六個月後回來看這份測試，不需要讀完 200 行就知道它在幹嘛
- Review 時可以快速判斷「mock 策略對不對」「scope 有沒有超出 UT 的範圍」
- 新人 onboarding 時這就是最好的文件

---

## 2. 測試情境索引 — 在 describe 前列出所有 case 的摘要

當一個 describe 裡有 3 個以上的 `it`，在 describe 前加一個**編號索引**：

```ts
/**
 * 測試情境一覽：
 *
 * 1. 正常下單 → 庫存扣減、訂單建立、wallet 扣款、回傳 receipt
 * 2. 混合商品（實體 + 虛擬）→ 各走不同出貨流程
 * 3. 已下過同樣的單 → 冪等，回傳既有訂單
 * 4. 庫存不足 → throw
 * 5. wallet 餘額不夠 → throw、庫存不變
 * 6. userId 不存在 → throw
 */
describe("OrderService.placeOrder (integration)", () => {
```

### 為什麼

- 一眼就看到全貌：哪些情境有蓋到、哪些漏了
- Review 時可以先看索引決定要不要深入讀 code
- 索引跟實際 `it` 的順序保持一致

---

## 3. describe 命名

格式：`ClassName.methodName (test type)`

```ts
describe("UserService.createUser (unit)", () => { ... });
describe("OrderService.placeOrder (integration)", () => { ... });
describe("expandRewardItem (unit)", () => { ... });  // 純函式不用 class 名
```

- `(unit)` / `(integration)` 標記讓跑測試時一眼分辨
- 如果是巢狀 describe（同一個 method 分 context），內層用情境描述：

```ts
describe("UserService.createUser (unit)", () => {
  describe("when email is valid", () => { ... });
  describe("when email already exists", () => { ... });
});
```

---

## 4. it 命名 — 描述行為，不是 method 名

### 原則

讀 `it` 名稱就該知道「什麼情境 → 什麼結果」，不需要打開 test body。

### 格式

`<前提條件>時，<預期行為>`（用該專案的語言）

```ts
// ✅ 好
it("餘額不足時，轉帳失敗且雙方帳戶不變", ...)
it("email 已存在時，拋出 DuplicateEmailError", ...)
it("returns empty array when no items match the filter", ...)
it("庫存剛好等於訂購量時，下單成功且庫存歸零", ...)

// ❌ 壞
it("createUser works", ...)
it("test case 1", ...)
it("should create user", ...)  // 少了「什麼情境」
it("placeOrder", ...)
```

### 有「and」就該拆嗎？

**不一定**。如果多個斷言是「同一件事的不同面向」，可以留在同一個 `it`：

```ts
// ✅ OK — 都是「下單成功」這件事的不同面向
it("正常下單時，庫存扣減、訂單建立、wallet 扣款", ...)

// ❌ 應該拆 — 這是兩件獨立的事
it("下單成功且推播通知寄出", ...)
```

判斷標準：如果其中一個斷言 fail 了，另一個還有獨立意義嗎？有 → 拆。沒有 → 合。

---

## 5. 測試 body 的段落排版

### 5.1 AAA 用註解切段

```ts
it("正常下單時，庫存扣減且訂單建立", async () => {
  // Arrange
  const user = await createUser();
  const product = await createProduct({ stock: 10 });

  // Act
  const result = await orderService.placeOrder(user.id, [{ productId: product.id, qty: 3 }]);

  // Assert
  const updatedProduct = await getProduct(product.id);
  expect(updatedProduct.stock).toBe(7);
  expect(result.orderId).toBeDefined();
});
```

或用 `// When` / `// Then`（較簡潔，適合 Arrange 段落很明顯的情況）：

```ts
it("正常下單時，庫存扣減且訂單建立", async () => {
  const user = await createUser();
  const product = await createProduct({ stock: 10 });

  // When
  const result = await orderService.placeOrder(user.id, [{ productId: product.id, qty: 3 }]);

  // Then
  const updatedProduct = await getProduct(product.id);
  expect(updatedProduct.stock).toBe(7);
});
```

### 5.2 選哪一種？

- **同一份測試檔內統一**，不要混用
- 短的 test（< 10 行）可以省略註解，AAA 用空行隔開就好
- 長的 test（> 15 行）一定要加註解，不然讀起來會迷路

### 5.3 Act 段只有一行

如果 Act 需要多行，這個 test 可能在測兩件事，考慮拆開。

---

## 6. Import 排版

分三個區塊，區塊之間空一行：

```ts
// 1. 外部套件 / 語言標準庫 / 型別
import { randomUUID } from "crypto";
import { OrderStatus, PaymentType } from "@prisma/client";

// 2. App 模組（被測對象及其依賴）
import { prisma } from "@/configs/database";
import orderService from "@/services/order.service";

// 3. Test helpers
import { truncateAll } from "@tests/helpers/db.helper";
import { createUser, createProduct } from "@tests/helpers/order.factory";
```

- 區塊內按字母排序（或按 import path 排序）
- 不要把 test helper 跟 app 模組混在一起

---

## 7. 斷言寫法

### 7.1 Integration test：回資料源查驗

呼叫 SUT 後，**不只看回傳值**，還要去資料源（DB / 檔案 / 外部狀態）確認實際寫入：

```ts
// Act
const result = await service.placeOrder(userId, items);

// Assert — 驗回傳值
expect(result.message).toBe("Order placed");

// Assert — 回 DB 確認
const order = await db.order.findFirst({ where: { userId } });
expect(order.status).toBe("CREATED");

const product = await db.product.findFirst({ where: { id: productId } });
expect(product.stock).toBe(7);  // 原本 10，買了 3
```

### 7.2 部分比對用 `toMatchObject`

只斷言你關心的欄位，不要逐欄比對所有欄位（加新欄位就壞）：

```ts
// ✅ 只比對關心的
expect(order).toMatchObject({
  status: "CREATED",
  totalAmount: 300,
});

// ❌ 比對所有欄位（脆弱）
expect(order.status).toBe("CREATED");
expect(order.totalAmount).toBe(300);
expect(order.createdAt).toBeInstanceOf(Date);  // 不必要
expect(order.updatedAt).toBeInstanceOf(Date);  // 不必要
```

**toMatchObject vs toEqual — 用哪個看「這物件多一個欄位時，測試該不該紅」：**
- **該紅**（你擁有整個形狀、多一欄＝bug 或洩漏）→ `toEqual` 把整包 pin 住。適用：assembled 輸出 / mapper 結果 / 小 value object / **要發出去的 wire payload**（多一欄可能是洩漏、少一欄是壞掉，就是要它變動時強迫你回來確認）。
- **不該紅**（物件帶有你不擁有、不關心的附帶欄位，如 DB record 的 id / createdAt / updatedAt）→ `toMatchObject` 只驗你關心的。

注意上面那個 `❌ 比對所有欄位` 是**逐欄 `.toBe()`**（脆弱、又漏驗沒列到的欄位）——它跟整包 `toEqual({...})` 是兩回事。toMatchObject 是「大物件、只 care 幾欄」的預設；但當**確切形狀本身就是契約**時（尤其對外 payload），toEqual 才對，別為了怕「加欄位就壞」而把該 pin 死的契約放掉。

### 7.3 巢狀部分比對用 `expect.objectContaining`

```ts
expect(result).toMatchObject({
  items: [
    expect.objectContaining({ name: "Widget", qty: 3 }),
    expect.objectContaining({ name: "Gadget", qty: 1 }),
  ],
});
```

### 7.4 集合斷言：先長度、再個別

```ts
// 先確認數量對
expect(order.items).toHaveLength(2);

// 再驗個別項目
const widget = order.items.find((i) => i.name === "Widget");
expect(widget).toMatchObject({ qty: 3, price: 100 });
```

當每筆預期相同時，用 for-of：

```ts
expect(snapshots).toHaveLength(3);
for (const snap of snapshots) {
  expect(snap.status).toBe("CLAIMED");
  expect(snap.quantity).toBe(1);
}
```

---

## 8. 錯誤路徑的組織

### 8.1 相似的錯誤用 `it.each`（或框架等價物）

```ts
it.each(["EXPIRED", "SUSPENDED", "CANCELLED"])(
  "狀態是 %s 時，操作會 throw",
  async (status) => {
    const order = await createOrder({ status });
    await expect(service.ship(order.id)).rejects.toThrow();
  }
);
```

- 每個值單獨跑，fail 時知道是哪個值壞了
- 適用於：多種非法狀態、多種無效輸入、多種缺少欄位

### 8.2 錯誤路徑只斷言 throw

除非「副作用沒發生」本身就是被測行為（例如：餘額不足時 wallet 不變），否則錯誤路徑只驗 throw：

```ts
// ✅ 只驗 throw
await expect(service.placeOrder(fakeUserId, items)).rejects.toThrow();

// ✅ 「副作用沒發生」是重點行為時才加
await expect(service.placeOrder(userId, items)).rejects.toThrow("Insufficient");
const wallet = await db.wallet.findFirst({ where: { userId } });
expect(wallet.balance).toBe(originalBalance);  // 沒被扣
```

---

## 9. 冪等性測試的寫法

驗證「已完成的操作再次呼叫不會重複執行」：

```ts
it("訂單已出貨時，再次呼叫 ship 不重複出貨，回傳既有結果", async () => {
  // Arrange — 手動建立「已出貨」的完整狀態
  const order = await createOrder({ status: "SHIPPED" });
  const existingShipment = await createShipment({ orderId: order.id });

  // Act
  const result = await service.ship(order.id);

  // Assert — 回傳既有結果，不新建
  expect(result.shipmentId).toBe(existingShipment.id);
  const shipments = await db.shipment.findMany({ where: { orderId: order.id } });
  expect(shipments).toHaveLength(1);  // 沒有多出一筆
});
```

關鍵：Arrange 手動建完整的「已完成」狀態，不是先呼叫一次 SUT 再呼叫第二次。這樣做測試更快、更不依賴 SUT 的其他行為。

---

## 10. 測試案例排列順序

在 describe 內按這個順序排列 `it`：

1. **Happy path（最簡單）** — 讀者第一個看到的是正常行為
2. **Happy path（變體/組合）** — 多種輸入組合
3. **業務轉換邏輯** — 展開、合併、轉換等
4. **冪等 / 重複操作**
5. **非法狀態 / 錯誤路徑**（用 `it.each` 收攏）
6. **權限 / 隔離**
7. **邊界條件**

### 為什麼這個順序

- 先看到「這個 method 正常做什麼」，再看「什麼會讓它失敗」
- Review 時如果只有時間看前兩個 test，至少看到了最重要的行為
- 錯誤路徑放後面、用 `it.each` 收攏，不會佔版面

---

## Checklist — 寫完一份測試後自檢

- [ ] 有檔頭 JSDoc（Scope / Mocks / SUT / 目的）
- [ ] 3 個以上 `it` 時有測試情境索引
- [ ] `describe` 標記了 `(unit)` 或 `(integration)`
- [ ] 每個 `it` 名稱讀得出「什麼情境 → 什麼結果」
- [ ] body 有 AAA 或 When/Then 註解切段（> 10 行時）
- [ ] Import 分三區、區間空行
- [ ] 斷言用 `toMatchObject` 而非逐欄比對
- [ ] 相似錯誤用 `it.each` 收攏
- [ ] 案例按 happy → error 順序排列
