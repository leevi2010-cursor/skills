#!/usr/bin/env python3
"""Build deterministic, whole-day windows for a wechat-cli Markdown export."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


MESSAGE_RE = re.compile(
    r"^- \[(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2})\] (?P<speaker>[^:]+):(?P<body>.*)$"
)
EXPECTED_RE = re.compile(r"^\*\*消息数量:\*\*\s*(?P<count>\d+)\s*$")
PLACEHOLDER_TYPES = {
    "[图片]": "image",
    "[语音]": "voice",
    "[视频]": "video",
    "[文件]": "file",
    "[链接/文件]": "link_or_file",
    "[通话]": "call",
    "[位置]": "location",
    "[名片]": "card",
    "[表情]": "emoji",
}


@dataclass(frozen=True)
class Message:
    line: int
    date: str
    time: str
    body: str


@dataclass
class Day:
    date: str
    start_line: int
    end_line: int
    messages: list[Message]


def classify(body: str) -> str:
    body = body.strip()
    for prefix, label in PLACEHOLDER_TYPES.items():
        if body.startswith(prefix):
            return label
    if body.startswith("[系统]") or body.startswith("[撤回]"):
        return "system"
    return "text"


def parse_source(source: Path) -> tuple[list[str], int | None, list[Message]]:
    lines = source.read_text(encoding="utf-8").splitlines()
    expected = None
    messages: list[Message] = []
    for line_number, line in enumerate(lines, start=1):
        expected_match = EXPECTED_RE.match(line)
        if expected_match:
            expected = int(expected_match.group("count"))
        message_match = MESSAGE_RE.match(line)
        if message_match:
            messages.append(
                Message(
                    line=line_number,
                    date=message_match.group("date"),
                    time=message_match.group("time"),
                    body=message_match.group("body"),
                )
            )
    return lines, expected, messages


def build_days(lines: list[str], messages: list[Message]) -> list[Day]:
    if not messages:
        return []
    days: list[Day] = []
    current: Day | None = None
    for message in messages:
        if current is None or current.date != message.date:
            if current is not None:
                current.end_line = message.line - 1
                days.append(current)
            current = Day(
                date=message.date,
                start_line=message.line,
                end_line=len(lines),
                messages=[],
            )
        current.messages.append(message)
    assert current is not None
    current.end_line = len(lines)
    days.append(current)
    return days


def build_windows(days: list[Day], max_messages: int) -> list[dict[str, object]]:
    windows: list[dict[str, object]] = []
    group: list[Day] = []
    group_count = 0

    def close_group() -> None:
        nonlocal group, group_count
        if not group:
            return
        all_messages = [message for day in group for message in day.messages]
        type_counts = Counter(classify(message.body) for message in all_messages)
        windows.append(
            {
                "window_index": len(windows) + 1,
                "start_date": group[0].date,
                "end_date": group[-1].date,
                "start_timestamp": f"{all_messages[0].date} {all_messages[0].time}",
                "end_timestamp": f"{all_messages[-1].date} {all_messages[-1].time}",
                "start_line": group[0].start_line,
                "end_line": group[-1].end_line,
                "messages": len(all_messages),
                "message_types": dict(sorted(type_counts.items())),
            }
        )
        group = []
        group_count = 0

    for day in days:
        day_count = len(day.messages)
        if group and group_count + day_count > max_messages:
            close_group()
        group.append(day)
        group_count += day_count
        if day_count > max_messages:
            close_group()
    close_group()
    return windows


def index_source(source: Path, max_messages: int) -> tuple[dict[str, object], bool]:
    lines, expected, messages = parse_source(source)
    days = build_days(lines, messages)
    windows = build_windows(days, max_messages)
    matches_header = expected is None or expected == len(messages)
    payload: dict[str, object] = {
        "status": "verified" if matches_header and messages else "partial",
        "source": str(source.resolve()),
        "expected_messages": expected,
        "parsed_messages": len(messages),
        "message_count_matches_header": matches_header,
        "first_timestamp": (
            f"{messages[0].date} {messages[0].time}" if messages else None
        ),
        "last_timestamp": (
            f"{messages[-1].date} {messages[-1].time}" if messages else None
        ),
        "max_messages_per_window": max_messages,
        "whole_day_boundary": True,
        "windows": windows,
    }
    return payload, bool(matches_header and messages)


def run_self_test() -> int:
    fixture = """# 聊天记录: 示例

**消息数量:** 5

---
- [2026-01-01 09:00] A: 第一条
- [2026-01-01 09:01] B: [图片]
- [2026-01-02 10:00] A: 第二天
  多行正文
- [2026-01-02 10:01] B: [语音]
- [2026-01-03 11:00] A: 第三天
"""
    with tempfile.TemporaryDirectory(prefix="wechat-windows-") as temp_dir:
        source = Path(temp_dir) / "fixture.md"
        source.write_text(fixture, encoding="utf-8")
        payload, ok = index_source(source, max_messages=3)
    windows = payload["windows"]
    checks = [
        ok,
        payload["parsed_messages"] == 5,
        len(windows) == 2,
        windows[0]["start_date"] == "2026-01-01",
        windows[0]["end_date"] == "2026-01-01",
        windows[1]["messages"] == 3,
        windows[1]["message_types"]["voice"] == 1,
    ]
    result = {
        "status": "passed" if all(checks) else "failed",
        "checks_passed": sum(checks),
        "checks_total": len(checks),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(checks) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index whole-day semantic windows in a wechat-cli Markdown export."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--source", type=Path, required=True)
    index_parser.add_argument("--max-messages", type=int, default=1000)
    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "self-test":
        return run_self_test()
    if args.max_messages < 1:
        raise SystemExit("--max-messages must be at least 1")
    if not args.source.is_file():
        raise SystemExit(f"source is not a file: {args.source}")
    payload, ok = index_source(args.source, args.max_messages)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
