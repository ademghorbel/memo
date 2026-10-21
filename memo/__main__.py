"""Command line: python -m memo check|fix|undo|widget [--vault PATH]"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .checker import Config, check
from .fixer import fix, undo

FACES = {"tidy": "( -_-)", "worried": "( o_o;)", "bloated": "( >_<)"}


def default_vault() -> Path:
    return Path(os.environ.get("MEMO_VAULT") or Path.home() / "ClaudeVault")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memo", description="Look after a vault of memory notes.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", type=Path, default=None, help="vault folder (default: $MEMO_VAULT or ~/ClaudeVault)")
    common.add_argument("--max-words", type=int, default=Config.max_words)
    common.add_argument("--max-notes", type=int, default=Config.max_notes_per_subject)
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", parents=[common], help="report what needs tidying (read-only)")
    p_check.add_argument("--json", action="store_true", help="machine-readable output")
    p_fix = sub.add_parser("fix", parents=[common], help="apply the safe fixes (backup first)")
    p_fix.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    sub.add_parser("undo", parents=[common], help="restore the vault from the last fix's backup")
    p_widget = sub.add_parser("widget", parents=[common], help="show Memo on the desktop")
    p_widget.add_argument("--every", type=float, default=10, help="re-check every N minutes (0 = only on click)")
    args = parser.parse_args(argv)
    config = Config(max_words=args.max_words, max_notes_per_subject=args.max_notes)

    vault = args.vault or default_vault()
    if args.command == "fix":
        result = fix(vault, config, dry_run=args.dry_run)
        print("Would do:" if args.dry_run else "Done:" if result.changed else "Nothing safe to fix.")
        for line in result.done:
            print(f"  + {line}")
        if result.left:
            print("Left for you:")
            for line in result.left:
                print(f"  - {line}")
        if result.backup:
            print(f"Backup: {result.backup}  (undo with: memo undo)")
        return 0
    if args.command == "undo":
        for line in undo(vault):
            print(line)
        return 0
    if args.command == "widget":
        from .widget import run
        run(args.vault or default_vault(), config, args.every)
        return 0

    report = check(args.vault or default_vault(), config)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"{FACES[report.mood]}  {report.mood}")
        print(f"{report.notes} notes, {report.words} words, {report.bytes / 1024:.1f} KB  ({report.vault})")
        for f in report.findings:
            where = f"  {f.path}" if f.path else ""
            print(f"  [{f.level}] {f.code}{where}: {f.message}")
        if not report.findings:
            print("  Nothing to tidy.")
    return 1 if report.mood == "bloated" else 0


if __name__ == "__main__":
    sys.exit(main())
