#!/usr/bin/env python3
"""Strip Claude Code session JSONL down to signal-only conversation text.

Raw session JSONL is dominated by tool_use blocks, tool_result payloads,
thinking blocks and file-history-snapshot entries. Measured across this
vault's history: 99.3% of bytes are noise (272 MB -> 1.9 MB).

Writes one compact JSON file per session to ~/.claude/extracted/, in the
schema claude-history-ingest expects:

    {"session_id", "project", "cwd", "start_ts", "end_ts",
     "n_turns", "n_user_words", "turns": [{"role", "text"}, ...]}

Re-runs are incremental: a session is re-extracted only when its JSONL is
newer than the extracted output (override with --force).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_HISTORY = Path.home() / ".claude"
DEFAULT_OUT = DEFAULT_HISTORY / "extracted"


def iter_records(path):
    """Yield parsed JSON objects from a JSONL file, skipping unparseable lines."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def record_text(record):
    """Return the human-readable text of a record, or '' if it carries none.

    Only `text` blocks survive. tool_use, tool_result, thinking and image
    blocks are the noise this script exists to remove.
    """
    message = record.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p).strip()


def record_role(record):
    """Resolve a record to 'user'/'assistant', or None if it is not a turn."""
    kind = record.get("type")
    if kind in ("user", "assistant"):
        return kind
    message = record.get("message")
    if isinstance(message, dict) and message.get("role") in ("user", "assistant"):
        return message["role"]
    return None


def extract_session(jsonl_path, project):
    """Build the extracted-session dict, or None if the session has no text."""
    turns = []
    cwd = None
    session_id = None
    timestamps = []

    for record in iter_records(jsonl_path):
        # Sidechains are subagent transcripts; the skill ingests those separately.
        if record.get("isSidechain"):
            continue
        cwd = cwd or record.get("cwd")
        session_id = session_id or record.get("sessionId")
        role = record_role(record)
        if not role:
            continue
        text = record_text(record)
        if not text:
            continue
        timestamp = record.get("timestamp")
        if timestamp:
            timestamps.append(timestamp)
        # Consecutive same-role records are one turn split across lines.
        if turns and turns[-1]["role"] == role:
            turns[-1]["text"] += "\n" + text
        else:
            turns.append({"role": role, "text": text})

    if not turns:
        return None

    timestamps.sort()
    user_words = sum(len(t["text"].split()) for t in turns if t["role"] == "user")
    return {
        "session_id": session_id or jsonl_path.stem,
        "project": project,
        "cwd": cwd,
        "start_ts": timestamps[0] if timestamps else None,
        "end_ts": timestamps[-1] if timestamps else None,
        "n_turns": len(turns),
        "n_user_words": user_words,
        "turns": turns,
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY,
                        help="Claude history root (default: ~/.claude)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output directory (default: ~/.claude/extracted)")
    parser.add_argument("--skip", default="",
                        help="comma-separated substrings; matching projects are excluded")
    parser.add_argument("--since",
                        help="only sessions modified on or after this date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true",
                        help="re-extract even when the output is already up to date")
    parser.add_argument("--quiet", action="store_true", help="suppress per-file output")
    args = parser.parse_args()

    projects_dir = args.history / "projects"
    if not projects_dir.is_dir():
        sys.exit(f"no projects directory at {projects_dir}")

    skips = [s.strip() for s in args.skip.split(",") if s.strip()]
    since = None
    if args.since:
        try:
            since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            sys.exit(f"--since must be YYYY-MM-DD, got {args.since!r}")

    raw_bytes = out_bytes = 0
    written = skipped_cache = skipped_filter = empty = 0

    for jsonl_path in sorted(projects_dir.rglob("*.jsonl")):
        project = jsonl_path.parent.name
        # subagents/ holds child-agent transcripts, not conversations.
        if "subagents" in jsonl_path.parts:
            skipped_filter += 1
            continue
        if any(s in project for s in skips):
            skipped_filter += 1
            continue

        stat = jsonl_path.stat()
        if since and datetime.fromtimestamp(stat.st_mtime, timezone.utc) < since:
            skipped_filter += 1
            continue

        out_path = args.out / project / f"{jsonl_path.stem}.json"
        if (not args.force and out_path.exists()
                and out_path.stat().st_mtime >= stat.st_mtime):
            skipped_cache += 1
            continue

        session = extract_session(jsonl_path, project)
        if session is None:
            empty += 1
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(session, ensure_ascii=False, indent=1)
        out_path.write_text(payload, encoding="utf-8")

        raw_bytes += stat.st_size
        out_bytes += len(payload.encode("utf-8"))
        written += 1
        if not args.quiet:
            print(f"{project}/{jsonl_path.name}  "
                  f"{stat.st_size / 1e6:.1f}MB -> {len(payload) / 1e3:.0f}KB  "
                  f"({session['n_turns']} turns)")

    print(f"\nextracted {written} session(s) to {args.out}")
    if skipped_cache:
        print(f"  {skipped_cache} already up to date")
    if skipped_filter:
        print(f"  {skipped_filter} excluded by --skip/--since/subagents")
    if empty:
        print(f"  {empty} had no conversation text")
    if raw_bytes:
        print(f"  {raw_bytes / 1e6:.1f}MB -> {out_bytes / 1e6:.2f}MB "
              f"({raw_bytes / max(out_bytes, 1):.0f}x reduction)")


if __name__ == "__main__":
    main()
