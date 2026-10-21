"""Read a vault of markdown memory notes and report what needs tidying.

Read-only: nothing here writes, moves or deletes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

DATED = re.compile(r"^\d{4}-\d{2}-\d{2}")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
ARCHIVE_SUFFIX = " - Archive"
IGNORED_DIRS = {".obsidian", ".git", ".trash", ".memo"}

LEVELS = ("info", "warning", "problem")


@dataclass
class Config:
    max_notes_per_subject: int = 2
    max_words: int = 600
    stub_words: int = 25
    last_session: str = "Last Session"
    sections: tuple[str, ...] = ("Current state", "Open items", "History")


@dataclass
class Finding:
    level: str  # one of LEVELS
    code: str
    message: str
    path: str = ""


@dataclass
class Report:
    vault: str
    notes: int = 0
    words: int = 0
    bytes: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def mood(self) -> str:
        levels = {f.level for f in self.findings}
        if "problem" in levels:
            return "bloated"
        if "warning" in levels:
            return "worried"
        return "tidy"

    def to_dict(self) -> dict:
        return {**asdict(self), "mood": self.mood}


def subject_of(stem: str) -> str:
    return stem.removesuffix(ARCHIVE_SUFFIX)


def check(vault: Path | str, config: Config | None = None) -> Report:
    vault = Path(vault)
    cfg = config or Config()
    report = Report(vault=str(vault))
    if not vault.is_dir():
        report.findings.append(Finding("problem", "no-vault", "Vault folder not found.", str(vault)))
        return report

    notes = sorted(
        p for p in vault.rglob("*.md") if not IGNORED_DIRS & set(p.relative_to(vault).parts)
    )
    names = {p.stem for p in notes}
    by_subject: dict[str, list[Path]] = defaultdict(list)
    add = report.findings.append

    for path in notes:
        rel = str(path.relative_to(vault))
        text = path.read_text(encoding="utf-8", errors="replace")
        words = len(text.split())
        report.notes += 1
        report.words += words
        report.bytes += path.stat().st_size

        if DATED.match(path.stem):
            add(Finding("problem", "dated-file", "Per-session file; merge it into its subject note.", rel))
            continue
        is_archive = path.stem.endswith(ARCHIVE_SUFFIX)  # archives may be tiny or long
        if words < cfg.stub_words and not is_archive:
            add(Finding("problem", "stub-file", f"Almost empty ({words} words).", rel))
            continue

        by_subject[subject_of(path.stem)].append(path)
        if words > cfg.max_words and not is_archive:
            add(Finding("warning", "oversize-note", f"{words} words, limit is {cfg.max_words}.", rel))
        for target in sorted({t.strip() for t in WIKILINK.findall(CODE.sub("", text))} - names):
            add(Finding("warning", "broken-link", f"Links to [[{target}]], which does not exist.", rel))

        is_subject = path.stem != cfg.last_session and not is_archive
        missing = [s for s in cfg.sections if f"## {s}".lower() not in text.lower()]
        if is_subject and missing:
            add(Finding("info", "missing-section", "No section: " + ", ".join(missing) + ".", rel))

    for subject, paths in by_subject.items():
        if len(paths) > cfg.max_notes_per_subject:
            add(Finding(
                "problem", "too-many-notes",
                f"{len(paths)} notes for this subject, limit is {cfg.max_notes_per_subject}.", subject,
            ))
    if notes and cfg.last_session not in names:
        add(Finding("warning", "no-last-session", f"No '{cfg.last_session}.md' note."))

    report.findings.sort(key=lambda f: (-LEVELS.index(f.level), f.code, f.path))
    return report
