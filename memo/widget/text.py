"""Turns a checker Report into the short sentences shown in Memo's bubble."""

from __future__ import annotations

from collections import Counter

from ..checker import Report
from ..fixer import FixResult

LABELS = {
    "no-vault": ("vault folder not found", "vault folders not found"),
    "dated-file": ("per-session file to merge", "per-session files to merge"),
    "stub-file": ("almost empty note", "almost empty notes"),
    "too-many-notes": ("subject split over too many notes", "subjects split over too many notes"),
    "oversize-note": ("note over the word limit", "notes over the word limit"),
    "broken-link": ("broken link", "broken links"),
    "no-last-session": ("missing 'last session' note", "missing 'last session' notes"),
    "missing-section": ("note missing a section", "notes missing a section"),
}
HEADERS = {"tidy": "All tidy!", "worried": "Hmm, a few things...", "bloated": "Ugh, I feel bloated."}


def summarize(report: Report) -> str:
    lines = [HEADERS[report.mood]]
    for code, n in Counter(f.code for f in report.findings).items():
        one, many = LABELS.get(code, (code, code))
        lines.append(f"• {n} {one if n == 1 else many}")
    lines.append(f"{report.notes} notes, {report.words} words")
    if report.findings:
        lines.append("Right click → What's wrong? for details")
    return "\n".join(lines)


def details(report: Report, limit: int = 8) -> str:
    if not report.findings:
        return "Nothing to tidy."
    lines = [f"• {f.path + ': ' if f.path else ''}{f.message}" for f in report.findings[:limit]]
    if len(report.findings) > limit:
        lines.append(f"...and {len(report.findings) - limit} more")
    return "\n".join(lines)


def tidied(result: FixResult, limit: int = 5) -> str | None:
    """What a tidy did, or None when there was nothing safe to do."""
    if not result.done:
        return None
    lines = ["Tidied up:"] + [f"• {l}" for l in result.done[:limit]]
    if len(result.done) > limit:
        lines.append(f"...and {len(result.done) - limit} more")
    lines.append("(Right click → Undo last tidy to put it back)")
    return "\n".join(lines)
