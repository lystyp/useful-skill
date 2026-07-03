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
| [test-writing-style](skills/test-writing-style/) | UT / Integration Test 的寫作風格規範：檔頭註解、測試命名、段落排版、import 分群、斷言寫法、錯誤路徑組織。與 write-unit-test（方法論）互補，專注在「測試程式碼怎麼排版寫」。 |
| [ai-family-backend-style](skills/ai-family-backend-style/) | `ai_family_backend` / backend-v2 專案專用的 coding style & tips：分層架構、Zod validator 慣例、Prisma + Exception 處理、Swagger 流程、SRP 四問、Commit 規範。包含「不要重造輪子」六條鐵律（response function、service 吃 validator 型別、common validator / utils 先用既有、swagger 同步、service 一對一原則）。 |
| [grill-me](skills/grill-me/) | 對使用者的 plan / design 進行連環追問，沿著決策樹一個分支一個分支收斂，每題都附上建議答案，每次只問一題；可由 codebase 回答的就直接探索。鏡像自 [mattpocock/skills/grill-me](https://github.com/mattpocock/skills/tree/main/grill-me)。 |
| [isolated-worktree-session](skills/isolated-worktree-session/) | 平行多 session 改 code 時避免互相污染。**不自動觸發** —— 使用者要改 code 時，先問要不要啟用；同意後從 HEAD 切 temp branch + 開 worktree、嚴格鎖定 session 在 worktree 內、結束時詢問是否 cherry-pick 回原 branch。 |
| [design-sparring-partner](skills/design-sparring-partner/) | 不教寫某種 code，而是定義「跟使用者做非瑣碎開發時 AI 該有的協作姿態」：① 先診斷對齊、不急著產 code 並嚴守 scope guard；② 設計決策用「攤牌式」攤開思路與權衡軸、反 sycophancy（雙向）；③ 一切對著 code 驗證不憑記憶；④ 抵抗過度工程，含變化軸／DIP 抽象判準（essential vs coincidental、≥2 實作或被點名才抽象、依賴方向、聆聽變化軸訊號）；⑤ 尊重使用者主導的節奏與乾淨 diff。附具體慣例 references：patterns（設計模式↔變化軸）、layered-architecture（分層結構/命名/主流程呈現）、readability-review（兩遍冷讀方法論）。 |

## 安裝

Claude Code 會從 `~/.claude/skills/` 載入 user-level skills。把這個 repo 的 skills 掛進去即可：

### 方法一：Symlink（推薦，方便 `git pull` 更新）

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git ~/useful-skill
mkdir -p ~/.claude/skills
ln -s ~/useful-skill/skills/research-industry-practices ~/.claude/skills/research-industry-practices
ln -s ~/useful-skill/skills/project-conventions        ~/.claude/skills/project-conventions
ln -s ~/useful-skill/skills/commit                     ~/.claude/skills/commit
ln -s ~/useful-skill/skills/learn-from-known           ~/.claude/skills/learn-from-known
ln -s ~/useful-skill/skills/code-review-skill          ~/.claude/skills/code-review-skill
ln -s ~/useful-skill/skills/test-writing-style         ~/.claude/skills/test-writing-style
ln -s ~/useful-skill/skills/ai-family-backend-style    ~/.claude/skills/ai-family-backend-style
ln -s ~/useful-skill/skills/grill-me                   ~/.claude/skills/grill-me
ln -s ~/useful-skill/skills/isolated-worktree-session  ~/.claude/skills/isolated-worktree-session
ln -s ~/useful-skill/skills/design-sparring-partner    ~/.claude/skills/design-sparring-partner
```

### 方法二：直接複製

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git
cp -R useful-skill/skills/* ~/.claude/skills/
```

也可以只挑需要的 skill 安裝。專案層級的 skill 則放到 `<project>/.claude/skills/`。
