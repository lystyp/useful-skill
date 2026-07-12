# Claude Code 通知（macOS）

這份文件涵蓋兩種 Claude Code 的 macOS 通知，共用同一套 terminal-notifier 機制、同一份前置需求與排查 SOP，只是掛在不同的 hook 事件上：

- **完成通知**（`Stop` 事件）：每一輪回覆完成時通知。
- **問句通知**（`PreToolUse` → `AskUserQuestion`）：Claude 用 AskUserQuestion 工具（選單型提問）問你之前通知。

兩者可以獨立啟用，也可以一起放進同一個 `hooks` 區塊。

## 最終行為

### 完成通知（Stop）

每次 Claude Code 回覆完成（Stop 事件）時：

1. macOS 跳出通知：標題「Claude Code ✅」，內容「已完成：<這一輪使用者問了什麼，前 60 字>」，Glass 音效。
2. **點擊通知 → 跳回該 session 專案的 VSCode 視窗**（多專案多 session 各跳各的，因為專案目錄是 hook 執行當下動態取得的）。
3. 設定在使用者層級（`~/.claude/settings.json`），所有專案的 session 都生效。

### 問句通知（AskUserQuestion）

Claude 一「挑出問句」要問你（就是那種帶選項的 AskUserQuestion 選單）之前：

1. macOS 跳出通知：標題「Claude Code ❓」，內容「詢問：<問句內容，前 80 字；多題以 ` | ` 串接>」，Submarine 音效（刻意跟完成通知的 Glass 區分，一聽就知道是「要你做選擇」還是「做完了」）。
2. 點擊通知 → 一樣跳回該 session 專案的 VSCode 視窗。
3. `async` 在背景發，不會擋住問句選單跳出來。
4. 同樣設在使用者層級，所有專案的 session 都生效。

> 只有「AskUserQuestion 工具的選單型提問」會觸發。Claude 直接在對話文字裡問你（沒呼叫工具）不會觸發，因為那不是一次 tool call。

## 前置需求

（兩種通知共用）

- macOS（通知與點擊跳轉都依賴 macOS 通知中心）
- [terminal-notifier](https://github.com/julienXX/terminal-notifier)：`brew install terminal-notifier`
- `jq`（撈 transcript／解析 hook payload 用）：macOS 沒內建的話 `brew install jq`
- VSCode（bundle id `com.microsoft.VSCode`；用其他編輯器要換掉 `open -b` 的目標）

## 設定步驟

### 1. 在 `~/.claude/settings.json` 加入 hook

與既有設定合併（不要整檔覆蓋）。兩個通知放在同一個 `hooks` 區塊裡，各自掛在自己的事件上：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "T=$(jq -r '.transcript_path // empty'); MSG=$(jq -rs '[.[] | select(.type==\"user\" and (.isMeta|not)) | .message.content | (if type==\"string\" then . elif type==\"array\" then ([.[] | select(.type==\"text\") | .text] | join(\" \")) else \"\" end) | gsub(\"[\\\\n\\\\r\\\\t]+\"; \" \") | select(length>0) | select(startswith(\"<\")|not)] | (last // \"\") | .[0:60]' \"$T\" 2>/dev/null); [ -z \"$MSG\" ] && MSG=\"回覆完成\"; /opt/homebrew/bin/terminal-notifier -title \"Claude Code ✅\" -message \"已完成：$MSG\" -sound Glass -execute \"open -b com.microsoft.VSCode '${CLAUDE_PROJECT_DIR:-$(pwd)}'\" 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "Q=$(jq -r '[.tool_input.questions[]?.question] | join(\" | \") | .[0:80]' 2>/dev/null); [ -z \"$Q\" ] && Q=\"需要你的選擇\"; /opt/homebrew/bin/terminal-notifier -title \"Claude Code ❓\" -message \"詢問：$Q\" -sound Submarine -execute \"open -b com.microsoft.VSCode '${CLAUDE_PROJECT_DIR:-$(pwd)}'\" 2>/dev/null || true",
            "async": true
          }
        ]
      }
    ]
  }
}
```

只要其中一種通知的，就只放對應的那個 key。

### 2. 重新載入設定

如果 session 是在改設定「之前」啟動的，hook 可能還沒載入：
在 Claude Code 輸入 `/hooks` 開一次選單（會重新載入設定），或重啟 session。

### 3. 驗證（pipe-test）

不用真的等一輪回覆／等 Claude 問問題，直接用假的 hook payload 餵設定檔裡的指令：

```bash
# 完成通知
CMD=$(jq -r '.hooks.Stop[0].hooks[0].command' ~/.claude/settings.json)
T=$(ls -t ~/.claude/projects/*/*.jsonl | head -1)   # 隨便挑一份最近的 transcript
echo "{\"transcript_path\":\"$T\"}" | bash -c "$CMD" && echo OK

# 問句通知
QCMD=$(jq -r '.hooks.PreToolUse[] | select(.matcher=="AskUserQuestion") | .hooks[0].command' ~/.claude/settings.json)
echo '{"tool_input":{"questions":[{"question":"要選哪個方案？","header":"方案"}]}}' | bash -c "$QCMD" && echo OK
```

通知有跳出來、內容對得上（完成帶最後一句提問／問句帶問題文字）、點擊會開 VSCode，就是設定成功。

## 原理解說（逐段）

hook 觸發時，Claude Code 會把 JSON payload 餵進指令的 stdin，指令逐段解析。**兩個通知最大的差別是資料來源**：完成通知讀 `transcript_path` 再去撈檔案，問句通知直接讀 payload 裡的 `tool_input`。

### 完成通知（Stop）

| 片段 | 作用 |
| --- | --- |
| `T=$(jq -r '.transcript_path // empty')` | 從 stdin 的 hook payload 取出該 session 的 transcript（.jsonl）路徑 |
| `MSG=$(jq -rs '[...] \| (last // "") \| .[0:60]' "$T")` | 從 transcript 撈「最後一則使用者訊息」：只取 `type=="user"` 且非 meta 的項目、只取 text 內容（排除 tool_result）、換行壓成空白、排除 `<` 開頭的系統注入內容，取最後一筆截前 60 字（jq 的 `.[0:60]` 按 codepoint 切，不會切壞中文） |
| `[ -z "$MSG" ] && MSG="回覆完成"` | 撈不到就用預設文字 |

### 問句通知（AskUserQuestion）

| 片段 | 作用 |
| --- | --- |
| `Q=$(jq -r '[.tool_input.questions[]?.question] \| join(" \| ") \| .[0:80]')` | 直接從 `PreToolUse` payload 的 `tool_input` 撈所有問句文字（AskUserQuestion 的 `questions[].question`），多題用 ` \| ` 串接、截前 80 字。用 `[]?` 容錯：沒有 questions 也不會噴錯 |
| `[ -z "$Q" ] && Q="需要你的選擇"` | 撈不到就用預設文字 |

用 `PreToolUse` + `matcher: "AskUserQuestion"`（而不是 `Notification` 事件）是因為它剛好在「工具執行前」觸發——AskUserQuestion 的「執行」就是把選單跳給你、等你回答，所以 PreToolUse 正好落在選單出現的前一刻。搭配 `async` 不會擋住選單。

### 兩者共用的尾段

| 片段 | 作用 |
| --- | --- |
| `terminal-notifier ... -execute "open -b com.microsoft.VSCode '${CLAUDE_PROJECT_DIR:-$(pwd)}'"` | 發通知；路徑在 hook 執行當下展開並烙進通知裡，點擊通知時執行 `open -b`，VSCode 會聚焦「已開著該資料夾的那個視窗」。用 `$CLAUDE_PROJECT_DIR`（session 啟動時的專案根目錄）而不是 `$(pwd)`：hook 當下的 pwd 會跟著 session 中的 `cd` 跑，例如 worktree 流程 cd 進 `.worktrees/<branch>` 後 pwd 就是 worktree 路徑，VSCode 沒有視窗開著那個資料夾，點通知會開新視窗而不是跳回原專案。fallback `$(pwd)` 讓沒有這個環境變數的環境（如手動 pipe-test）也能動 |
| `2>/dev/null \|\| true` | 通知失敗不要干擾 Claude Code 本體 |
| `"async": true` | hook 在背景跑，不卡回覆／不卡選單 |

用絕對路徑 `/opt/homebrew/bin/terminal-notifier` 是因為 hook 的執行環境不保證載入 Homebrew 的 PATH。

## 勿擾模式（Focus）踩雷指南 ⚠️

**這是最容易「明明設定都對卻收不到通知」的原因（兩種通知都適用）。** 重點：macOS 是按「通知掛在哪個 app 名下」決定放不放行，而不是按誰真的發的：

- `osascript -e 'display notification ...'` 發的通知 → 掛在「**工序指令編寫程式（Script Editor）**」名下
- `terminal-notifier` 發的通知 → 掛在 **terminal-notifier** 自己名下

所以勿擾模式開啟時，就算把「Claude」或「Visual Studio Code」加進允許清單也沒用——
**要加的是 terminal-notifier**。

已知麻煩：terminal-notifier.app 藏在 `/opt/homebrew/Cellar/terminal-notifier/<版本>/` 裡，
勿擾模式「允許的 App」挑選器可能搜不到它。解法：把 app 複製到「應用程式」資料夾讓 Launch Services 收錄：

```bash
cp -R /opt/homebrew/Cellar/terminal-notifier/*/terminal-notifier.app /Applications/
```

另外首次發通知時 macOS 可能會問「terminal-notifier 想要傳送通知」，要按允許
（事後可到「系統設定 → 通知 → terminal-notifier」確認「允許通知」開啟、樣式選「橫幅」）。

## 已知限制與取捨

- **icon 與精準跳轉不可兼得**：terminal-notifier 的 `-sender com.microsoft.VSCode` 可以把通知掛在 VSCode 名下（icon 變 VSCode、可用 VSCode 身分穿透勿擾），但 `-sender` 會讓 `-execute` 完全失效（實測於 macOS 15 Sequoia 確認），點擊就不會跳轉了。本設定選擇「精準跳轉」，icon 維持 terminal-notifier 預設。
- `-appIcon` 在新版 macOS 已無法替換左側 app icon（實測無效）。
- 點擊跳轉是「聚焦已開啟該資料夾的視窗」；如果該專案沒有開著的 VSCode 視窗，會開一個新的。
- **完成通知**內容撈的是「最後一則使用者訊息」，若該輪是由排程/自動觸發（沒有使用者訊息），會顯示 fallback 文字「回覆完成」。
- **問句通知**只認 AskUserQuestion 工具的選單型提問；Claude 直接在對話裡用純文字問你（沒呼叫工具）不會觸發。撈不到問句文字時顯示 fallback「需要你的選擇」。

## 排查 SOP（由內往外逐層驗證）

「沒收到通知」時照這個順序切，每一步都能把問題砍半：

1. **hook 有沒有觸發？** 在對應 command 前面暫時加 `echo "$(date) fired" >> /tmp/hook-check.txt; `，
   觸發對應事件後（完成通知等一輪回覆／問句通知等 Claude 問一次）看檔案有沒有新行。沒有 → hook 沒載入：檢查 JSON 是否合法
   （`jq . ~/.claude/settings.json`，壞 JSON 會讓整份設定靜默失效）、事件名稱是否正確（完成是 `Stop`、問句是 `PreToolUse` 且 `matcher` 為 `AskUserQuestion`）、
   然後 `/hooks` 或重啟重新載入。
2. **指令會不會失敗？** 用上面的 pipe-test 跑，暫時拿掉 `2>/dev/null || true` 看真實錯誤。
3. **通知發了但沒顯示？** 打開通知中心（點選單列時鐘）——被勿擾靜音的通知不會跳橫幅，
   但都會堆在通知中心。有堆 → 100% 是勿擾模式／允許清單問題，回頭看上面的踩雷指南。
4. **系統層設定**：「系統設定 → 通知 → terminal-notifier」允許通知＋橫幅樣式；
   勿擾模式允許清單；螢幕鏡像輸出時預設也會勿擾（`dndMirrored`）。
5. 還是不行，用「每 10 秒發一則帶編號通知」的迴圈，一邊調系統設定一邊看哪一則開始出現，
   直接定位是哪個開關擋的：
   ```bash
   for i in $(seq 1 30); do terminal-notifier -title "測試 #$i" -message "$(date +%H:%M:%S)"; sleep 10; done
   ```

## 變體

- **想要 VSCode icon**、且接受點擊只是「打開 VSCode app」（不精準跳專案視窗）的話，
  把 `-execute "..."` 換成 `-sender com.microsoft.VSCode`，
  勿擾允許清單改加「Visual Studio Code」即可。
- **想換音效**：`-sound` 換成任一 macOS 系統音（`/System/Library/Sounds/*.aiff` 的檔名，如 `Glass`、`Submarine`、`Sosumi`、`Hero`、`Funk`）。建議完成通知與問句通知用不同音，一聽就能分辨。
