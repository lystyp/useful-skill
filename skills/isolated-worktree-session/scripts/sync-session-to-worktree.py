#!/usr/bin/env python3
"""Copy the running Claude Code conversation into the session store of a git
worktree, so opening that worktree in a new editor window lists the same
conversation and lets you continue it there.

Usage:
    sync-session-to-worktree.py <worktree-dir> [--force]

The worktree must contain a .worktree-session-meta file with REPO_ROOT= and
TEMP_BRANCH= lines.

The copy gets a fresh session id rather than reusing the original one, because
~/.claude/file-history/<session id>/ is keyed by that id alone: two windows
carrying the same id would write their undo snapshots on top of each other. The
new id is written back to the meta file, so re-running this updates the same
copy instead of piling up new ones.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
FILE_HISTORY_DIR = Path.home() / ".claude" / "file-history"
META_FILENAME = ".worktree-session-meta"


def die(message: str) -> None:
    print(f"sync-session-to-worktree: {message}", file=sys.stderr)
    sys.exit(1)


def project_dir_name(cwd: str) -> str:
    """Claude Code stores a session under a folder named after the directory it
    was launched in, with every non-alphanumeric character replaced by a dash."""
    return re.sub(r"[^a-zA-Z0-9]", "-", cwd)


def read_meta(worktree: Path) -> dict[str, str]:
    meta_path = worktree / META_FILENAME
    if not meta_path.is_file():
        die(f"{meta_path} not found — create it when the worktree is set up")
    meta = {}
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            meta[key.strip()] = value.strip()
    return meta


def write_meta_key(worktree: Path, key: str, value: str) -> None:
    meta_path = worktree / META_FILENAME
    lines = meta_path.read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def locate_source(session_id: str) -> Path:
    matches = sorted(PROJECTS_DIR.glob(f"*/{session_id}.jsonl"))
    if not matches:
        die(f"no transcript for session {session_id} under {PROJECTS_DIR}")
    if len(matches) > 1:
        die(f"session {session_id} exists in several projects: {matches}")
    return matches[0]


def load_entries(transcript: Path) -> list[dict]:
    """Parse the transcript, skipping anything unreadable — the file is being
    appended to while this runs, so its last line can be half-written."""
    entries = []
    dropped = 0
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            dropped += 1
    if dropped:
        print(f"  skipped {dropped} unparsable line(s)")
    return entries


def trim_to_balanced(entries: list[dict]) -> list[dict]:
    """Cut the transcript back to the last point where every tool call already
    has its result.

    An assistant message is written to disk before its tool actually runs, so a
    live transcript ends on a tool call with nothing answering it. A conversation
    that contains such a call is rejected when it is sent back to the API, which
    would make the copy impossible to continue.
    """
    open_tool_calls: set[str] = set()
    last_balanced = -1
    for index, entry in enumerate(entries):
        message = entry.get("message")
        blocks = message.get("content") if isinstance(message, dict) else None
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    open_tool_calls.add(block.get("id"))
                elif block.get("type") == "tool_result":
                    open_tool_calls.discard(block.get("tool_use_id"))
        if not open_tool_calls:
            last_balanced = index
    if last_balanced < 0:
        die("transcript has no point where all tool calls are answered")
    return entries[: last_balanced + 1]


def last_of_type(entries: list[dict], entry_type: str) -> dict | None:
    for entry in reversed(entries):
        if entry.get("type") == entry_type:
            return entry
    return None


def rewrite(entry: dict, session_id: str, cwd: str, git_branch: str) -> dict:
    entry = dict(entry)
    if "sessionId" in entry:
        entry["sessionId"] = session_id
    if "cwd" in entry:
        entry["cwd"] = cwd
    if "gitBranch" in entry:
        entry["gitBranch"] = git_branch
    return entry


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def replace_dir(source: Path, target: Path) -> bool:
    if not source.is_dir():
        return False
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", help="worktree directory to copy the session into")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the copy even if it has grown past the original",
    )
    args = parser.parse_args()

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session_id:
        die("CLAUDE_CODE_SESSION_ID is not set — run this from inside a Claude Code session")

    worktree = Path(args.worktree).resolve()
    if not worktree.is_dir():
        die(f"{worktree} is not a directory")

    meta = read_meta(worktree)
    repo_root = meta.get("REPO_ROOT")
    if not repo_root:
        die(f"REPO_ROOT missing from {worktree / META_FILENAME}")
    temp_branch = meta.get("TEMP_BRANCH", "")

    source = locate_source(session_id)
    source_dir = source.parent
    entries = load_entries(source)
    if not entries:
        die(f"{source} is empty")

    source_cwd = next((e["cwd"] for e in entries if e.get("cwd")), None)
    if not source_cwd:
        die("transcript records no cwd, cannot work out where to copy it")
    if project_dir_name(source_cwd) != source_dir.name:
        die(
            f"{source_cwd} encodes to {project_dir_name(source_cwd)} but the transcript "
            f"lives in {source_dir.name} — the naming rule this script assumes no longer holds"
        )

    # The session may have been started in a subdirectory of the repo; land it in
    # the matching subdirectory of the worktree so both sides see the same tree.
    relative_cwd = os.path.relpath(source_cwd, os.path.realpath(repo_root))
    if relative_cwd.split(os.sep)[0] == os.pardir:
        die(f"session was started in {source_cwd}, which is outside the repo at {repo_root}")
    target_cwd = str(worktree if relative_cwd == "." else worktree / relative_cwd)

    target_session_id = meta.get("COPIED_SESSION_ID") or str(uuid.uuid4())
    target_dir = PROJECTS_DIR / project_dir_name(target_cwd)
    target = target_dir / f"{target_session_id}.jsonl"

    kept = trim_to_balanced(entries)
    kept_uuids = {e["uuid"] for e in kept if e.get("uuid")}

    # The title and the last-prompt marker sit at the very end of the transcript,
    # so the trim above usually takes them with it. Put them back, with the marker
    # pointing at whatever message survived, so the copy still shows up named in
    # the session picker and resumes from its real tail.
    title = last_of_type(entries, "ai-title")
    if title and title not in kept:
        kept.append(title)
    last_prompt = last_of_type(entries, "last-prompt")
    if last_prompt and last_prompt not in kept:
        last_prompt = dict(last_prompt)
        tail_uuid = next((e["uuid"] for e in reversed(kept) if e.get("uuid")), None)
        if tail_uuid:
            last_prompt["leafUuid"] = tail_uuid
            kept.append(last_prompt)
    elif last_prompt and last_prompt.get("leafUuid") not in kept_uuids:
        kept = [e for e in kept if e is not last_prompt]

    existing_lines = count_lines(target)
    if existing_lines > len(kept) and not args.force:
        die(
            f"{target} already holds {existing_lines} entries, more than the {len(kept)} "
            f"being copied — the conversation was continued in the worktree. Pass --force to overwrite it."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for entry in kept:
            out.write(json.dumps(rewrite(entry, target_session_id, target_cwd, temp_branch), ensure_ascii=False))
            out.write("\n")

    copied_sidecar = replace_dir(source_dir / session_id, target_dir / target_session_id)
    copied_history = replace_dir(FILE_HISTORY_DIR / session_id, FILE_HISTORY_DIR / target_session_id)

    write_meta_key(worktree, "COPIED_SESSION_ID", target_session_id)

    print(f"  from:    {source}")
    print(f"  to:      {target}")
    print(f"  entries: {len(kept)} of {len(entries)} (trailing unanswered tool call trimmed)")
    print(f"  extras:  subagents/tool-results={'yes' if copied_sidecar else 'none'}, "
          f"file-history={'yes' if copied_history else 'none'}")


if __name__ == "__main__":
    main()
