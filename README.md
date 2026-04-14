# useful-skill

個人收集的 Claude Code Skills。

## Skills

| Skill | 用途 |
| --- | --- |
| [research-industry-practices](skills/research-industry-practices/) | 遇到技術選型、最佳實踐、工具比較類問題時，強制透過 WebSearch/WebFetch 查詢當前業界實務，避免依賴 LLM 過時的內建知識。 |
| [project-conventions](skills/project-conventions/) | 專案程式碼規範集合。任何 agent 產生或修改程式碼前先閱讀；也支援用一句話追加新規範（「以後都要這樣寫」）。 |
| [commit](skills/commit/) | 根據 git staged/unstaged changes 分析變更並撰寫 commit 訊息，提交前會先讓使用者確認。 |
| [learning-note](skills/learning-note/) | 將工作中遇到的知識點製作成結構化學習筆記，用「問題驅動」敘事方式講解原理，搭配簡單範例。 |
| [code-review-skill](skills/code-review-skill/) | 多語言 code review 指引（React/Vue/Rust/TS/Java/Python/C++），catch bugs、提升品質、給建設性 feedback。以 git submodule 連結上游 [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill)。 |

## 安裝

Claude Code 會從 `~/.claude/skills/` 載入 user-level skills。把這個 repo 的 skills 掛進去即可：

### 方法一：Symlink（推薦，方便 `git pull` 更新）

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git ~/useful-skill
mkdir -p ~/.claude/skills
ln -s ~/useful-skill/skills/research-industry-practices ~/.claude/skills/research-industry-practices
ln -s ~/useful-skill/skills/project-conventions        ~/.claude/skills/project-conventions
ln -s ~/useful-skill/skills/commit                     ~/.claude/skills/commit
ln -s ~/useful-skill/skills/learning-note              ~/.claude/skills/learning-note
ln -s ~/useful-skill/skills/code-review-skill          ~/.claude/skills/code-review-skill
```

### 方法二：直接複製

```bash
git clone --recursive https://github.com/lystyp/useful-skill.git
cp -R useful-skill/skills/* ~/.claude/skills/
```

也可以只挑需要的 skill 安裝。專案層級的 skill 則放到 `<project>/.claude/skills/`。
