"""Safe fixes for a vault: only changes that need no judgment.

- Oversize note: move its oldest `## History` lines into `<Subject> - Archive.md`.
- Missing section: add the empty heading at the end of the note.
- Stub note (almost empty): remove it. Empty folders: remove them.
- Link to a note that was deleted: keep the words, drop the brackets
  (a `- Older history: [[X - Archive]]` line whose archive is gone is removed).

Everything else (merging notes, rewriting text) is reported, never touched.
Before anything is written, the files about to change go into a backup zip in
`<vault>/.memo/backups/`; `undo()` restores the latest one.
"""

from __future__ import annotations

import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .checker import ARCHIVE_SUFFIX, CODE, IGNORED_DIRS, Config, check

MEMO_DIR = ".memo"
KEEP_BACKUPS = 20
HEADING = re.compile(r"^#{1,6}\s")
HISTORY = re.compile(r"^##\s+history\s*$", re.I)
BULLET = re.compile(r"^\s{0,1}[-*]\s")
POINTER = re.compile(r"older history|\[\[[^\]]*" + re.escape(ARCHIVE_SUFFIX) + r"\]\]", re.I)
HEADROOM = 0.85  # trim to 85 % of the limit so the next session doesn't tip it over again


@dataclass
class FixResult:
    done: list[str] = field(default_factory=list)  # what was (or would be) changed
    left: list[str] = field(default_factory=list)  # what needs a human or the AI engine
    backup: str = ""
    dry_run: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.done)


def words(text: str) -> int:
    return len(text.split())


# --- history surgery ---------------------------------------------------------
def _history(lines: list[str]) -> tuple[int, int, list[list[str]]] | None:
    """Locate `## History`: returns (start, end, entries) where entries are bullets
    (with their continuation lines) between line start+1 and end."""
    start = next((i for i, l in enumerate(lines) if HISTORY.match(l.strip())), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if HEADING.match(lines[i])), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    entries: list[list[str]] = []
    for line in lines[start + 1:end]:
        if BULLET.match(line) or not entries:
            entries.append([line])
        else:
            entries[-1].append(line)
    entries = [e for e in entries if "".join(e).strip()]
    return start, end, entries


def trim_history(text: str, max_words: int, archive_name: str) -> tuple[str, list[str]]:
    """Move the oldest history entries out until the note fits. Returns the new
    text and the moved lines (oldest last, same order as in the note)."""
    lines = text.splitlines()
    found = _history(lines)
    if not found:
        return text, []
    start, end, entries = found
    pinned = [e for e in entries if POINTER.search(" ".join(e))]
    movable = [e for e in entries if e not in pinned]
    if not pinned:
        pinned = [[f"- Older history: [[{archive_name}]]"]]

    def build(keep):
        body = [l for e in keep + pinned for l in e]
        return "\n".join(lines[:start + 1] + body + lines[end:]) + ("\n" if text.endswith("\n") else "")

    target = int(max_words * HEADROOM)
    keep, moved = list(movable), []
    while len(keep) > 1 and words(build(keep)) > target:
        moved.insert(0, keep.pop())
    if not moved:
        return text, []
    return build(keep), [l for e in moved for l in e]


def add_to_archive(existing: str | None, subject: str, moved: list[str]) -> str:
    if existing is None:
        return (f"# {subject}{ARCHIVE_SUFFIX}\n\n"
                f"Older history lines moved out of [[{subject}]] to keep that note short. Newest first.\n\n"
                "## History\n" + "\n".join(moved) + "\n")
    lines = existing.splitlines()
    at = next((i + 1 for i, l in enumerate(lines) if HISTORY.match(l.strip())), None)
    if at is None:
        at = next((i for i, l in enumerate(lines) if BULLET.match(l)), None)
    if at is None:
        lines += ["", "## History"]
        at = len(lines)
    return "\n".join(lines[:at] + moved + lines[at:]) + "\n"


# --- dead links ----------------------------------------------------------------
LINK = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]*))?\]\]")


def unlink(text: str, dead: set[str]) -> str:
    """Turn [[Dead]] into Dead (or its alias), outside code. Pointer-only bullets to a
    dead archive are dropped, since they would point at nothing."""
    def outside_code(chunk: str) -> str:
        return LINK.sub(lambda m: (m[3] or m[1]).strip() if m[1].strip() in dead else m[0], chunk)

    kept = []
    for line in text.splitlines(keepends=True):
        m = LINK.search(line)
        if (m and m[1].strip() in dead and m[1].strip().endswith(ARCHIVE_SUFFIX)
                and BULLET.match(line) and POINTER.search(line) and len(line.split()) <= 4 + len(m[0].split())):
            continue
        kept.append(line)
    text, out, i = "".join(kept), [], 0
    for m in CODE.finditer(text):
        out += [outside_code(text[i:m.start()]), m[0]]
        i = m.end()
    return "".join(out) + outside_code(text[i:])


# --- planning and applying ---------------------------------------------------
def plan(vault: Path, cfg: Config) -> tuple[dict[Path, str | None], list[Path], FixResult]:
    """Work out every change in memory. {path: new text, or None to remove}."""
    report = check(vault, cfg)
    changes: dict[Path, str | None] = {}
    result = FixResult()
    read = lambda p: changes[p] if p in changes else p.read_text(encoding="utf-8")  # noqa: E731

    for f in report.findings:
        path = vault / f.path if f.path else None
        if f.code == "oversize-note":
            stem = path.stem
            if stem == cfg.last_session or stem.endswith(ARCHIVE_SUFFIX):
                result.left.append(f"{f.path}: over the limit, needs condensing by hand.")
                continue
            new, moved = trim_history(read(path), cfg.max_words, stem + ARCHIVE_SUFFIX)
            if moved:
                archive = path.with_name(stem + ARCHIVE_SUFFIX + ".md")
                if archive in changes and changes[archive] is None:  # never delete what we write to
                    del changes[archive]
                    result.done = [d for d in result.done if not d.startswith(f"Removed {archive.name} ")]
                old_archive = read(archive) if archive.exists() or archive in changes else None
                changes[path] = new
                changes[archive] = add_to_archive(old_archive, stem, moved)
                n = sum(1 for l in moved if BULLET.match(l))
                result.done.append(f"Moved {n} old history line{'s' * (n != 1)} from {f.path} to {archive.name}.")
            if not moved or words(changes.get(path, "")) > cfg.max_words:
                result.left.append(f"{f.path}: still over {cfg.max_words} words, "
                                   "the Current state or Open items need condensing.")
        elif f.code == "missing-section":
            missing = [s for s in cfg.sections if f"## {s}".lower() not in read(path).lower()]
            text = read(path).rstrip("\n")
            changes[path] = text + "".join(f"\n\n## {s}\n" for s in missing).rstrip("\n") + "\n"
            result.done.append(f"Added section{'s' * (len(missing) != 1)} {', '.join(missing)} to {f.path}.")
        elif f.code == "broken-link":
            dead = f.message.split("[[", 1)[1].split("]]", 1)[0]
            changes[path] = unlink(read(path), {dead})
            result.done.append(f"Unlinked [[{dead}]] in {f.path} (that note is gone).")
        elif f.code == "stub-file":
            changes[path] = None
            result.done.append(f"Removed {f.path} ({f.message.lower().rstrip('.')}).")
        else:
            result.left.append(f"{f.path + ': ' if f.path else ''}{f.message}")

    empty_dirs = sorted(
        (d for d in vault.rglob("*") if d.is_dir() and not any(d.iterdir())
         and not IGNORED_DIRS & set(d.relative_to(vault).parts)
         and MEMO_DIR not in d.relative_to(vault).parts),
        key=lambda d: -len(d.parts),
    )
    for d in empty_dirs:
        result.done.append(f"Removed empty folder {d.relative_to(vault)}.")
    return changes, empty_dirs, result


def fix(vault: Path | str, config: Config | None = None, dry_run: bool = False) -> FixResult:
    vault, cfg = Path(vault), config or Config()
    changes, empty_dirs, result = plan(vault, cfg)
    result.dry_run = dry_run
    if dry_run or not (changes or empty_dirs):
        return result

    backups = vault / MEMO_DIR / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    zpath = backups / f"{stamp}.zip"
    i = 1
    while zpath.exists():
        zpath, i = backups / f"{stamp}-{i}.zip", i + 1
    rel = lambda p: p.relative_to(vault).as_posix()  # noqa: E731
    manifest = {"time": stamp, "created": [], "changed": [], "removed": [], "dirs": [rel(d) for d in empty_dirs]}
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for path, new in changes.items():
            if path.exists():
                z.write(path, "files/" + rel(path))
                manifest["removed" if new is None else "changed"].append(rel(path))
            else:
                manifest["created"].append(rel(path))
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

    for path, new in changes.items():
        if new is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(new, encoding="utf-8")
    for d in empty_dirs:
        try:
            d.rmdir()
        except OSError:
            pass
    for old in sorted(b for b in backups.glob("*.zip") if b.name[:1].isdigit())[:-KEEP_BACKUPS]:
        old.unlink()
    result.backup = str(zpath)
    return result


def undo(vault: Path | str) -> list[str]:
    """Restore the most recent backup, then mark it as used."""
    vault = Path(vault)
    backups = sorted((vault / MEMO_DIR / "backups").glob("*.zip"))
    backups = [b for b in backups if re.match(r"\d{8}-\d{6}(-\d+)?\.zip$", b.name)]  # Memo's own, not yet undone
    if not backups:
        return ["Nothing to undo."]
    zpath = backups[-1]
    out = []
    with zipfile.ZipFile(zpath) as z:
        m = json.loads(z.read("manifest.json"))
        for r in m["created"]:
            (vault / r).unlink(missing_ok=True)
            out.append(f"Removed {r}.")
        for d in m["dirs"]:
            (vault / d).mkdir(parents=True, exist_ok=True)
        for r in m["changed"] + m["removed"]:
            target = vault / r
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open("files/" + r) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out.append(f"Restored {r}.")
    zpath.rename(zpath.with_name(zpath.stem + ".undone.zip"))
    return out
