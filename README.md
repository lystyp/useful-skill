# useful-skill

個人收集的 Claude Code Skills。

## Skills

| Skill | 用途 |
| --- | --- |
| [research-industry-practices](skills/research-industry-practices/) | 遇到技術選型、最佳實踐、工具比較類問題時，強制透過 WebSearch/WebFetch 查詢當前業界實務，避免依賴 LLM 過時的內建知識。 |
| [project-conventions](skills/project-conventions/) | 專案程式碼規範集合。任何 agent 產生或修改程式碼前先閱讀；也支援用一句話追加新規範（「以後都要這樣寫」）。 |
| [commit](skills/commit/) | 根據 git staged/unstaged changes 分析變更並撰寫 commit 訊息，要求寫成對 reviewer 友善的版本（含非顯而易見設計決策的動機），提交前先讓使用者確認。 |
| [learn-from-known](skills/learn-from-known/) | 用「從已知推導未知」的依賴關係優先教學法帶使用者學任何新主題：依「舊方法 → 痛點 → 需要的新能力 → 名詞 → 最小模型 → 完整功能」順序教，並把進度寫進一份 Markdown 大綱檔、隨進度更新。使用者說「教我」「我想學」「幫我理解」時觸發。 |
| [code-review-skill](skills/code-review-skill/) | 多語言 code review 指引（React/Vue/Rust/TS/Java/Python/C++），catch bugs、提升品質、給建設性 feedback。以 git submodule 連結上游 [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill)。 |
| [test-writing-style](skills/test-writing-style/) | UT / Integration Test 的寫作風格規範：檔頭註解、測試命名、段落排版、import 分群、斷言寫法、錯誤路徑組織。專注在「測試程式碼怎麼排版寫」。 |
| [ai-family-backend-style](skills/ai-family-backend-style/) | `ai_family_backend` / backend-v2 專案專用的 coding style & tips：分層架構、Zod validator 慣例、Prisma + Exception 處理、Swagger 流程、SRP 四問、Commit 規範。包含「不要重造輪子」六條鐵律（response function、service 吃 validator 型別、common validator / utils 先用既有、swagger 同步、service 一對一原則）。 |
| [grill-me](skills/grill-me/) | 對使用者的 plan / design 進行連環追問，沿著決策樹一個分支一個分支收斂，每題都附上建議答案，每次只問一題；可由 codebase 回答的就直接探索。鏡像自 [mattpocock/skills/grill-me](https://github.com/mattpocock/skills/tree/main/grill-me)。 |
| [isolated-worktree-session](skills/isolated-worktree-session/) | 平行多 session 改 code 時避免互相污染。**不自動觸發** —— 使用者要改 code 時，先問要不要啟用；同意後從 HEAD 切 temp branch + 開 worktree、嚴格鎖定 session 在 worktree 內、結束時詢問是否 cherry-pick 回原 branch。 |
| [design-sparring-partner](skills/design-sparring-partner/) | 不教寫某種 code，而是定義「跟使用者做非瑣碎開發時 AI 該有的協作姿態」：① 先診斷對齊、不急著產 code 並嚴守 scope guard；② 設計決策用「攤牌式」攤開思路與權衡軸、反 sycophancy（雙向）；③ 一切對著 code 驗證不憑記憶；④ 抵抗過度工程，含變化軸／DIP 抽象判準（essential vs coincidental、≥2 實作或被點名才抽象、依賴方向、聆聽變化軸訊號）；⑤ 尊重使用者主導的節奏與乾淨 diff。附具體慣例 references：patterns（設計模式↔變化軸）、layered-architecture（分層結構/命名/主流程呈現）、readability-review（兩遍冷讀方法論）。 |
| [useful-tools](skills/useful-tools/) | 實用工具設定集，每個工具一份 reference（完整設定步驟＋原理解說＋排查 SOP）。目前收錄：claude-code-notifications —— Claude Code 的 macOS 通知（含回覆完成通知與 AskUserQuestion 問句通知，內容帶當輪提問／問題文字、點通知跳回對應專案的 VSCode 視窗；terminal-notifier 實作，含勿擾模式踩雷指南）。 |
| [jira](skills/jira/) | 用 Jira Cloud REST API v3 查詢與操作 issue：JQL 搜尋、讀單票、建立 / 更新 / comment / 轉狀態。透過純 stdlib 的 `jira.py` wrapper，已處理好 Basic Auth、ADF 格式轉換、`/search/jql` cursor 分頁三個易踩雷點；憑證從 `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` 環境變數讀，不寫進檔案。寫入類操作動到真 Jira，執行前先跟使用者確認。 |
| [code-review](skills/code-review/) | 逐項審一份改動——本地 branch diff、GitHub PR（`gh`）、GitLab MR（`glab`）、或指定路徑皆可。**先讀懂改動目的**（PR/MR 描述或 commit 訊息）再開審，用「目的對齊 / 完整性 / 副作用」三視角與 checklist 並列。12 個面向各一份 `handlers/*.md`：可讀性 / 註解品質 / 函式控制流 / DRY / 單一職責 / 擴充性 / 耦合內聚 / 型別與資料形狀 / 錯誤處理 / 累積教訓 / API 健壯性 / 安全性(OWASP)；各派一個 subagent 只扛一份、再各派一個 critic 覆核覆蓋率與證據——**舉不出行號的 PASS 一律改判 UNSURE，禁空證據 PASS**。fan-out 前先報成本取得同意；預設只出清單不改 code。可讀性類問題強制成獨立一桶呈現，不得在 triage 被「嚴重度低」無聲過濾。語言與框架中立。 |
| [review-finding-format](skills/review-finding-format/) | review 問題的呈現格式，`code-review` 與 `pr-inline-comment` 共用同一套（所以 review 完的內容可直接發成留言）。每項含位置、問題、**🗣️ 白話情境**、建議解法。白話情境依 bug report 重現步驟的慣例寫：編號步驟、一行一動作、最短路徑、以「預期：… 實際：…」收尾——並發情境用「請求 A / 請求 B」交錯步驟表達，不標絕對時間。 |
| [pr-inline-comment](skills/pr-inline-comment/) | 把問題發成 GitHub PR 或 GitLab MR 的 inline 留言（發 / 改 / 刪）。處理好三個踩雷點：commit SHA 取得、新增 / 刪除 / 未變動行各自的行號錨定規則、以及 **行號必須以整數送出**——用 `-f` 送成字串會讓 GitLab 靜默丟棄整個 position、把留言降級成不掛在任何行上的一般留言。附「確認確實是 inline」的驗證指令。 |

## 安裝

### 方法一：Plugin marketplace（推薦）

在 Claude Code 裡一次裝整包：

```
/plugin marketplace add lystyp/useful-skill
/plugin install useful-skills@daniel-useful-skills
```

之後 repo 有更新，用 `/plugin marketplace update daniel-useful-skills` 就能拉到最新。

> `code-review-skill` 是外部 git submodule，不會跟著 plugin 一起裝；需要的話請去它的 upstream（[awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill)）另外安裝。

### 方法二：手動 symlink 個別 skill

只想挑幾支、或不走 plugin，就把要的 skill 連進 `~/.claude/skills/`：

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git ~/useful-skill
mkdir -p ~/.claude/skills
ln -s ~/useful-skill/skills/design-sparring-partner ~/.claude/skills/design-sparring-partner
# 其餘照樣挑要的連過去
```

專案層級的 skill 則放到 `<project>/.claude/skills/`。
