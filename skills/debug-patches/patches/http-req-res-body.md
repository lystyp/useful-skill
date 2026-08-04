# http-req-res-body — request 完成時印出 req/res body

**適用專案**：`ai_family_backend`（`backend/`，Express + pino-http）。辨識方式：存在
`backend/src/middlewares/http-logger.middleware.ts` 且內容用 `pinoHttp`。

**目的**：access log 原本只有 method / url / status，看不出「client 到底送了什麼、我們回了什麼」。
本地重現線上 bug 時，把兩邊 body 一起印出來，省掉逐層加 log 的來回。

**動到的檔案**：`backend/src/middlewares/http-logger.middleware.ts`（單檔）。

**⚠️ 絕不能 merge**：req/res body 含密碼、access token、個資。那支 middleware 本來就刻意不序列化
headers 就是為了這件事——本 patch 等於暫時把這道防線打開，只能活在本機。

---

## 套用方式

現行檔案是 `export const httpLogger = pinoHttp({ ... })` 一個 expression。三處改動：

1. **加 response body 的暫存區**：pino-http 只拿得到 req/res metadata，看不到 response body，
   所以要自己攔 `res.json` 把 payload 存下來。用 `WeakMap<Response, unknown>` 存，request 結束就能被回收。
2. **`customProps` 補兩個欄位**：`reqBody` 取 `req.body`（`express.json()` 掛在 httpLogger 之前，
   而 `customProps` 是在 response 完成時才求值，此時 body 必定已 parse 完成）；`resBody` 從 WeakMap 取。
   兩者都先過截斷（音檔 / base64 payload 會洗爆 log）。
3. **把 `httpLogger` 包成自己的 `RequestHandler`**：原本直接 export pinoHttp 的 middleware，
   現在要在它之前先換掉 `res.json`，所以改成 export 一個外層 handler，內部再呼叫 pinoHttp middleware。

只攔 `res.json`：這支 API 的回應都走 `res.json()`。若要 debug 的端點是 `res.send()` / stream，
同樣手法再攔一次 `res.send`。

## 參考實作

```ts
import { Request, RequestHandler, Response } from "express";
import { pinoHttp } from "pino-http";

import { logger } from "@/utils/logger";

// [temp-debug] 每筆請求完成時連 request / response body 一起印，方便本機重現線上問題。上限 4000 字避免音檔等大 payload 洗爆 log。
const DEBUG_BODY_MAX_CHARS = 4000;
const debugResBodies = new WeakMap<Response, unknown>();

function truncateForLog(body: unknown): unknown {
 if (body === undefined) return undefined;
 const text = typeof body === "string" ? body : JSON.stringify(body);
 if (text === undefined) return undefined;
 return text.length > DEBUG_BODY_MAX_CHARS ? `${text.slice(0, DEBUG_BODY_MAX_CHARS)}…[truncated ${text.length} chars]` : body;
}

const pinoHttpMiddleware = pinoHttp({
 // …原本的 customLogLevel / serializers / autoLogging 原封不動…
 customProps(req, res) {
  const { appUser, appClient, body } = req as Request;
  return {
   appUserId: appUser?.id,
   appPlatform: appClient?.platform,
   appVersion: appClient?.version,
   // [temp-debug]
   reqBody: truncateForLog(body),
   resBody: truncateForLog(debugResBodies.get(res as Response)),
  };
 },
});

// [temp-debug] pino-http 只看 req/res metadata，拿不到 response body；先攔 res.json 把 payload 存起來，
// 供 customProps 在 response 完成時讀取。
export const httpLogger: RequestHandler = (req, res, next) => {
 const originalJson = res.json.bind(res);
 res.json = (body: unknown) => {
  debugResBodies.set(res, body);
  return originalJson(body);
 };
 pinoHttpMiddleware(req, res, next);
};
```

注意 `customProps` 的簽名要從 `(req)` 改成 `(req, res)`，`pinoHttp` 的變數名從 `httpLogger` 改成
`pinoHttpMiddleware`（對外 export 的名字不變，`middlewares/index.ts` 不用動）。

## 驗證

```bash
cd backend && bunx tsc --noEmit
```

實跑：`npm run dev:simple` 打任一支 API，access log 那筆應同時出現 `reqBody` 與 `resBody`。
GET 這種沒有 body 的請求，`reqBody` 會是 `{}` 或消失（pino 自動略去 undefined），屬正常。
