# useful-skill

個人收集的 Claude Code Skills，以及管理三個獨立 Plugins 的 `daniel-useful-skills` Marketplace。

## Marketplace Plugins

| Plugin 安裝 ID | 上游來源與 Plugin 路徑 | Skill namespace |
| --- | --- | --- |
| `useful-skills@daniel-useful-skills` | 本 Repository 根目錄，維持既有設定 | `/useful-skills:<skill>` |
| `mattpocock-skills@daniel-useful-skills` | [mattpocock/skills](https://github.com/mattpocock/skills) 根目錄，使用 `github` source | `/mattpocock-skills:<skill>` |
| `pstack@daniel-useful-skills` | [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) 的 `plugins/pstack`，使用 `git-subdir` source | `/pstack:<skill>` |

三個 Plugin 可分別安裝、啟用、停用。Marketplace 只登記上游來源，不複製上游程式碼、不改寫 SKILL.md；安裝時由 Claude Code 抓取 Plugin。兩筆外部來源未設定 `ref`、`sha` 或額外的 `version`，沿用上游預設分支與 manifest 版本。升級到最新版 Claude Code 後使用，避免舊版不接受 `git-subdir` 的問題。

pstack 保留上游完整 Plugin，包含 agents 與 SessionStart hook；啟用 pstack 時，其上游內建工作流程也會載入。本 Marketplace 不另外增加 Router 或自動選擇機制。上游完整功能所需的執行環境與依賴，請依各自 README 設定。

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
| [isolated-worktree-session](skills/isolated-worktree-session/) | 平行多 session 改 code 時避免互相污染。**純手動：只有輸入 `/isolated-worktree-session` 才執行** —— 不自動觸發，也不會主動問你要不要啟用。呼叫後從 HEAD 切 temp branch + 開 worktree（開在 repo root 外的 sibling，雙向隔離），並補上 git 不會帶過去的兩樣東西：被 gitignore 的 `.env`（依相對路徑放，monorepo 各層各一份都會帶）、以及**當前這段對話**（複製到 worktree 對應的 session 目錄，用新的 VS Code 開 worktree 就能 resume 同一段對話接著做）。之後嚴格鎖定 session 在 worktree 內、結束時詢問是否 cherry-pick 回原 branch。 |
| [design-sparring-partner](skills/design-sparring-partner/) | 不教寫某種 code，而是定義「跟使用者做非瑣碎開發時 AI 該有的協作姿態」：① 先診斷對齊、不急著產 code 並嚴守 scope guard；② 設計決策用「攤牌式」攤開思路與權衡軸、反 sycophancy（雙向）；③ 一切對著 code 驗證不憑記憶；④ 抵抗過度工程，含變化軸／DIP 抽象判準（essential vs coincidental、≥2 實作或被點名才抽象、依賴方向、聆聽變化軸訊號）；⑤ 尊重使用者主導的節奏與乾淨 diff。附具體慣例 references：patterns（設計模式↔變化軸）、layered-architecture（分層結構/命名/主流程呈現）、readability-review（兩遍冷讀方法論）。 |
| [useful-tools](skills/useful-tools/) | 實用工具設定集，每個工具一份 reference（完整設定步驟＋原理解說＋排查 SOP）。目前收錄：claude-code-notifications —— Claude Code 的 macOS 通知（含回覆完成通知與 AskUserQuestion 問句通知，內容帶當輪提問／問題文字、點通知跳回對應專案的 VSCode 視窗；terminal-notifier 實作，含勿擾模式踩雷指南）。 |
| [jira](skills/jira/) | 用 Jira Cloud REST API v3 查詢與操作 issue：JQL 搜尋、讀單票、建立 / 更新 / comment / 轉狀態。透過純 stdlib 的 `jira.py` wrapper，已處理好 Basic Auth、ADF 格式轉換、`/search/jql` cursor 分頁三個易踩雷點；憑證從 `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` 環境變數讀，不寫進檔案。寫入類操作動到真 Jira，執行前先跟使用者確認。 |
| [code-review](skills/code-review/) | 逐項審一份改動——本地 branch diff、GitHub PR（`gh`）、GitLab MR（`glab`）、或指定路徑皆可。**先讀懂改動目的**（PR/MR 描述或 commit 訊息）再開審，用「目的對齊 / 完整性 / 副作用」三視角與 checklist 並列。12 個面向各一份 `handlers/*.md`：可讀性 / 註解品質 / 函式控制流 / DRY / 單一職責 / 擴充性 / 耦合內聚 / 型別與資料形狀 / 錯誤處理 / 累積教訓 / API 健壯性 / 安全性(OWASP)；各派一個 subagent 只扛一份、再各派一個 critic 覆核覆蓋率與證據——**舉不出行號的 PASS 一律改判 UNSURE，禁空證據 PASS**。fan-out 前先報成本取得同意；預設只出清單不改 code。可讀性類問題強制成獨立一桶呈現，不得在 triage 被「嚴重度低」無聲過濾。語言與框架中立。 |
| [review-finding-format](skills/review-finding-format/) | review 問題的呈現格式，`code-review` 與 `pr-inline-comment` 共用同一套（所以 review 完的內容可直接發成留言）。每項含位置、問題、**🗣️ 白話情境**、建議解法。白話情境依 bug report 重現步驟的慣例寫：編號步驟、一行一動作、最短路徑、以「預期：… 實際：…」收尾——並發情境用「請求 A / 請求 B」交錯步驟表達，不標絕對時間。 |
| [pr-inline-comment](skills/pr-inline-comment/) | 把問題發成 GitHub PR 或 GitLab MR 的 inline 留言（發 / 改 / 刪）。處理好三個踩雷點：commit SHA 取得、新增 / 刪除 / 未變動行各自的行號錨定規則、以及 **行號必須以整數送出**——用 `-f` 送成字串會讓 GitLab 靜默丟棄整個 position、把留言降級成不掛在任何行上的一般留言。附「確認確實是 inline」的驗證指令。 |
| [debug-patches](skills/debug-patches/) | 「只在本機才要有」的 debug 改動 catalog（`patches/` 一筆一檔）。**純手動觸發**：呼叫後把符合當前 repo 的 patch 套進去、跑型別檢查、單獨包成一個 `temp:` commit，跟正在做的功能改動分開，測完可整包 drop。套用前會擋兩件事：既存的 temp commit、以及目標檔案已有的未 commit 改動（混在一起就 drop 不乾淨）。新增的行一律帶 `[temp-debug]` 標記，`remove` 模式據此清光。目前收錄：request 完成時把 req/res body 印進 access log。 |
| [write-for-cold-reader](skills/write-for-cold-reader/) | 任何給人看的產出（程式碼註解、commit message、PR/MR 留言、文件、筆記、session 回話）共用同一套寫作標準：讀者只憑他手上真的有的東西就要讀得懂。先分清不對稱是哪一種——**A 讀者不在場**（註解／commit／文件）三條規則全開；**B 讀者在場但沒有你腦裡的東西**（session 回話）只需守「不依賴我讀過卻沒說出口的東西」。三條規則——① 只引用讀者手上有的東西（禁 .md 指標／自創詞／被砍掉的符號／未落地計畫）；② 逐句過「讀到這句會不會冒問號」測試（名詞要 grep 得到、結論寫死、修正句不擺句尾）；③ 解釋給機制不給生活類比，不熟的名詞當場展開。附各載體的「讀者手上有什麼」對照表與分段收尾自檢清單。 |
| [explain-mr](skills/explain-mr/) | 白話具體說明一份 branch／MR／PR 在幹嘛、為什麼要做。 |
| [explain-code-flow](skills/explain-code-flow/) | 替一份改動排一條從最外層入口一路往下讀的閱讀路線：一個入口一條路線、照執行順序排站，每站附 `檔案:行號` 與這站要看什麼，最後對照測試。 |

## 安裝

### 方法一：Plugin marketplace（推薦）

以下 `claude ...` 指令在終端機執行。加入 Marketplace 後，可依需要各別安裝：

```bash
claude plugin marketplace add lystyp/useful-skill
claude plugin install useful-skills@daniel-useful-skills --scope user
claude plugin install mattpocock-skills@daniel-useful-skills --scope user
claude plugin install pstack@daniel-useful-skills --scope user
claude plugin list
```

已加入 Marketplace 的使用者，先執行 `claude plugin marketplace update daniel-useful-skills` 取得新增項目。也可以在 Claude Code Session 內使用 `/plugin marketplace add lystyp/useful-skill`，並透過 `/plugin` 選取要安裝的 Plugin。

安裝與啟用是兩件事：Plugin 可以留在本機快取，停用後不載入其元件。安裝通常會啟用 Plugin；若要每次 Session 自行挑選，安裝完成後先停用這三個預設值：

```bash
claude plugin disable useful-skills@daniel-useful-skills --scope user
claude plugin disable mattpocock-skills@daniel-useful-skills --scope user
claude plugin disable pstack@daniel-useful-skills --scope user
```

如果已停用，指令可能回報 already disabled；用 `claude plugin list` 核對狀態即可。

#### 每次 Session 只載入指定的一套 Plugin

Claude Code 官方支援 `--settings` 搭配 `enabledPlugins`，只覆寫這次啟動的設定，不寫回設定檔。先完成上述安裝，再依需求執行其中一條：

```bash
# Session A：Matt
claude --settings '{"enabledPlugins":{"useful-skills@daniel-useful-skills":false,"mattpocock-skills@daniel-useful-skills":true,"pstack@daniel-useful-skills":false}}'

# Session B：pstack
claude --settings '{"enabledPlugins":{"useful-skills@daniel-useful-skills":false,"mattpocock-skills@daniel-useful-skills":false,"pstack@daniel-useful-skills":true}}'

# Session C：useful-skills
claude --settings '{"enabledPlugins":{"useful-skills@daniel-useful-skills":true,"mattpocock-skills@daniel-useful-skills":false,"pstack@daniel-useful-skills":false}}'
```

這會實際控制這三個 Plugin 的載入，包含 skills、agents、hooks 等元件。三個 ID 都明確寫出，因為 `enabledPlugins` 會逐個 ID 合併，省略某個 ID 會沿用既有設定。也可把其中一份 JSON 自行存檔，再用 `claude --settings /absolute/path/to/settings.json` 啟動，無需自訂工具。恢復對話時，也請在 `claude --resume ...` 同時傳入所選的 `--settings`。

這三組指令只控制本 Marketplace 的三個 ID；其他已安裝 Plugin、從其他 Marketplace 安裝的同名副本，以及手動放在 `~/.claude/skills/` 或專案 `.claude/skills/` 的獨立 skills，不會因此停用。如果要只保留一套，先檢查是否有這些副本並分別停用或移除。組織 managed settings 優先於 `--settings`，若管理員強制啟用某個 Plugin，這些指令無法覆蓋。

進入 Session 後，用 `/plugin` 的 Installed 與 Errors 檢查實際載入及錯誤；用 `/skills` 核對可用 skills。若要切換套件，結束後以另一條指令開新 Session；既有對話中已注入的內容不會因停用而消失。

#### 持久啟用／停用與設定範圍

以下以 pstack 為例，將 ID 換成表格中的另外兩個即可：

```bash
claude plugin enable pstack@daniel-useful-skills --scope user
claude plugin disable pstack@daniel-useful-skills --scope user
```

`user` 寫入 `~/.claude/settings.json`，影響所有專案；`project` 寫入專案 `.claude/settings.json`；`local` 寫入專案 `.claude/settings.local.json`，適合自己的專案覆寫。持久化命令的 scope 沒有 `session`，單次 Session 使用上面的啟動參數即可。

設定優先順序為 managed → `--settings` → local → project → user。在 Session 內可使用 `/plugin enable <ID>`、`/plugin disable <ID>` 或 Installed 頁面管理；這些會保存設定，不是單次 Session 選擇。變更後開新 Session，或依提示執行 `/reload-plugins`；SessionStart hook 的完整啟動行為仍應以新 Session 驗證。

#### 更新 Marketplace 與 Plugin

更新目錄和更新已安裝 Plugin 是不同步驟：

```bash
claude plugin marketplace update daniel-useful-skills
claude plugin update useful-skills@daniel-useful-skills --scope user
claude plugin update mattpocock-skills@daniel-useful-skills --scope user
claude plugin update pstack@daniel-useful-skills --scope user
```

只需執行已安裝 Plugin 的更新命令；若安裝在 project 或 local，改用該 scope。更新後開新 Session，或在既有 Session 執行 `/reload-plugins`。

useful-skills 的 `plugin.json` 與 marketplace 條目刻意不寫 `version`，讓 Claude Code 以 git commit SHA 當版本，每次 push 都會被 `claude plugin update` 視為新版。不要加回 `version`：版本字串沒變時，update 會判定已是最新，新推的 skill 不會進到已安裝的快取。

Matt 與 pstack 從各自上游取得更新，不需把程式碼同步到這個 Repository。Claude Code 優先使用上游 `plugin.json` 的版本辨識更新；若上游只改 commit 而未改 manifest 版本，可能仍被視為同版本，不能保證每個上游 commit 都會刷新快取。本 Marketplace 不改寫上游版本機制。

> `code-review-skill` 是既有外部 git submodule；維持原本安裝限制，需要的話請去 [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) 另外安裝。

#### 驗證與目前限制

本次已檢查 JSON 可解析、三個 Plugin 名稱唯一、Marketplace 欄位與來源格式符合官方文件、兩個上游 manifest 的名稱與實際 Plugin 路徑相符，以及既有 useful-skills 登錄未改動。

準備這份變更的環境沒有安裝 Claude Code，因此尚未實際執行官方驗證器、安裝、更新、Session 載入與停用測試。可在本機 checkout 此變更後執行：

```bash
claude --version
claude plugin validate .
```

接著依上方安裝與三組啟動指令，分別確認只有選定的一套載入、另兩套停用，並檢查 pstack 的 SessionStart hook 是否正常。官方驗證器只驗證本機目錄，不會抓取外部來源；外部 Plugin 的下載與執行仍須透過實際安裝測試。

官方文件：[Marketplace 來源格式](https://code.claude.com/docs/en/plugins/marketplace-reference)、[Plugin 指令](https://code.claude.com/docs/en/plugins/cli-reference)、[載入與設定優先順序](https://code.claude.com/docs/en/plugins/loading)、[單次 Session 設定](https://code.claude.com/docs/en/settings#change-a-setting-for-one-session)。

### 方法二：手動 symlink 個別 skill

只想挑幾支、或不走 plugin，就把要的 skill 連進 `~/.claude/skills/`：

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git ~/useful-skill
mkdir -p ~/.claude/skills
ln -s ~/useful-skill/skills/design-sparring-partner ~/.claude/skills/design-sparring-partner
# 其餘照樣挑要的連過去
```

專案層級的 skill 則放到 `<project>/.claude/skills/`。
