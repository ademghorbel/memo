# Memo: plan

Memo is a small desktop character that looks after a folder of markdown memory
notes (the kind an AI coding assistant keeps between sessions). Its face shows
the state of the notes at a glance. One click checks everything, tidies what is
safe to tidy, and tells you what it did.

Working name: **Memo** (an emo that minds your memory). Rename freely before
publishing.

## Why it exists

Session notes rot quietly: dated files pile up, the same subject gets split
across several notes, finished to-dos stay listed, links break. Cleaning that by
hand is a chore nobody does until it hurts. Memo makes the state visible and the
fix one click.

## Principles

- **Nothing is lost.** Every removal goes to the Recycle Bin or a backup zip.
  Text is never rewritten without an explicit confirm.
- **Works without AI.** Checking and the safe fixes are plain Python. An AI
  engine is optional and only used for the part that needs judgment.
- **Zero install pain.** Standard library only for the core and the widget
  (`tkinter`). No packages to install.
- **Not tied to one person's setup.** Vault path and every threshold are
  configurable. No personal paths or note names in the code.

## Architecture

```
memo/
  checker.py     reads the vault, returns a Report (findings + stats + mood)   M1
  fixer.py       applies the safe fixes a Report allows                        M2
  engine/        optional "compact" engines behind one interface               M4
    claude.py    calls `claude -p` with the vault rules
  widget/        tkinter window, face drawing, animation states, bubble        M3
  __main__.py    CLI: check | fix | compact | widget
```

The checker is the heart. The CLI, the widget and any future front end (tray
icon, Obsidian button) all consume the same `Report`, so the face can never
disagree with the facts.

### Mood

| Mood | Meaning | Face |
|---|---|---|
| `tidy` | no findings | slow breathing, occasional blink |
| `worried` | warnings only | sweat drop, glancing sideways |
| `bloated` | at least one problem | puffed cheeks, heavy eyelids |
| working | a fix or compact is running | eyes scanning, munching |
| done | finished | small smile, speech bubble with the summary |
| error | something failed | x_x, bubble says what broke |

### Checks (M1)

| Code | Level | What |
|---|---|---|
| `dated-file` | problem | `YYYY-MM-DD*.md` files, the per-session clutter |
| `stub-file` | problem | notes with almost no content |
| `too-many-notes` | problem | more than N notes for one subject |
| `oversize-note` | warning | a note over the word limit |
| `broken-link` | warning | `[[link]]` to a note that does not exist |
| `no-last-session` | warning | the rolling "last session" note is missing |
| `missing-section` | info | a subject note without the expected headings |

### Safe fixes (M2), no AI

- recycle stub files and empty folders
- move the oldest history lines of an oversize note into `<Subject> - Archive.md`
- report, but do not touch, anything that needs a rewrite

### Compact (M4), optional AI

Merging notes, condensing history and dropping finished open items need
judgment. The engine gets the notes plus the vault rules, proposes a diff, and
Memo shows the summary and asks before writing. First engine: Claude Code
headless (`claude -p`). The interface stays small so other engines can be added.

## Milestones

- [x] **M0** Project scaffold, this plan.
- [x] **M1** Checker + `memo check` CLI + tests. Useful on its own.
- [x] **M2** Safe fixes + `memo fix`, with a dry run and an undo log.
- [x] **M3** Widget: frameless always-on-top window, the face, idle / worried /
      bloated states driven by the checker, click to run, summary bubble,
      drag to move, right-click menu.
- [ ] **M4** Compact engine (Claude), confirm step, before/after summary.
- [ ] **M5** Polish: start with Windows, config file, remembered position,
      a second skin.
- [ ] **M6** Publish: licence, screenshots or a GIF in the README, a demo vault
      for people to try it on, first release.

## Decisions so far

- Desktop character first (tkinter). Tray icon and Obsidian button are later
  front ends over the same checker, not the starting point.
- Python 3.11+ (uses only the standard library).
- The face is drawn with canvas shapes, not image files, so there are no assets
  to ship and skins are just code.

## Open questions

- Name: keep "Memo"?
- Licence: MIT like the other repos?
- Windows only at first, or keep macOS/Linux working from day one? (The core is
  portable; Recycle Bin support and start-on-login are the per-OS parts.)
- Should the widget re-check on a timer, or only when the vault folder changes?
  (M3 uses a 10-minute timer, `--every` to change it.)

## Before publishing

- Scrub: no personal paths, note names or vault contents in the repo or its
  history. Tests use a generated demo vault.
- Set the repo-local git identity before the first commit.
- Add the licence file.
