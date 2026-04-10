# useful-skill

個人收集的 Claude Code Skills。

## Skills

| Skill | 用途 |
| --- | --- |
| [research-industry-practices](skills/research-industry-practices/) | 遇到技術選型、最佳實踐、工具比較類問題時，強制透過 WebSearch/WebFetch 查詢當前業界實務，避免依賴 LLM 過時的內建知識。 |
| [project-conventions](skills/project-conventions/) | 專案程式碼規範集合。任何 agent 產生或修改程式碼前先閱讀；也支援用一句話追加新規範（「以後都要這樣寫」）。 |

## 安裝

Claude Code 會從 `~/.claude/skills/` 載入 user-level skills。把這個 repo 的 skills 掛進去即可：

### 方法一：Symlink（推薦，方便 `git pull` 更新）

```bash
git clone https://github.com/lystyp/useful-skill.git ~/useful-skill
mkdir -p ~/.claude/skills
ln -s ~/useful-skill/skills/research-industry-practices ~/.claude/skills/research-industry-practices
ln -s ~/useful-skill/skills/project-conventions        ~/.claude/skills/project-conventions
```

### 方法二：直接複製

```bash
git clone https://github.com/lystyp/useful-skill.git
cp -R useful-skill/skills/* ~/.claude/skills/
```

也可以只挑需要的 skill 安裝。專案層級的 skill 則放到 `<project>/.claude/skills/`。
