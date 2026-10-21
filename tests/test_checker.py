import tempfile
import unittest
from pathlib import Path

from memo.checker import Config, check

SUBJECT = """# {name}

About {name}.

## Current state
- fine

## Open items / next
- nothing

## History
- 2026-01-01: started, with enough words here to not count as a stub file at all.
"""


class CheckerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def note(self, name: str, text: str | None = None) -> None:
        path = self.vault / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text is not None else SUBJECT.format(name=name), encoding="utf-8")

    def codes(self, **cfg) -> list[str]:
        return [f.code for f in check(self.vault, Config(**cfg)).findings]

    def tidy_vault(self):
        self.note("Website")
        self.note("Last Session", "# Last Session\n\n" + "Worked on [[Website]] today. " * 6)

    def test_tidy_vault_has_no_findings(self):
        self.tidy_vault()
        report = check(self.vault)
        self.assertEqual(report.findings, [])
        self.assertEqual(report.mood, "tidy")
        self.assertEqual(report.notes, 2)

    def test_missing_vault(self):
        report = check(self.vault / "nope")
        self.assertEqual([f.code for f in report.findings], ["no-vault"])

    def test_dated_and_stub_files_are_problems(self):
        self.tidy_vault()
        self.note("sessions/2026-01-02_website", "# 2026-01-02\n" + "did things " * 40)
        self.note("Empty", "nothing")
        report = check(self.vault)
        self.assertEqual(sorted(f.code for f in report.findings), ["dated-file", "stub-file"])
        self.assertEqual(report.mood, "bloated")

    def test_oversize_and_broken_link_are_warnings(self):
        self.tidy_vault()
        self.note("Big", SUBJECT.format(name="Big") + "word " * 700 + "see [[Ghost|alias]] and [[Website#History]]")
        report = check(self.vault)
        self.assertEqual(sorted(f.code for f in report.findings), ["broken-link", "oversize-note"])
        self.assertEqual(report.mood, "worried")

    def test_links_inside_code_are_ignored(self):
        self.tidy_vault()
        self.note("Docs", SUBJECT.format(name="Docs") + "Write links as `[[Name]]`.\n```\n[[Other]]\n```\n")
        self.assertEqual(self.codes(), [])

    def test_too_many_notes_per_subject(self):
        self.tidy_vault()
        self.note("Website - Archive")
        self.assertEqual(self.codes(), [])
        self.assertEqual(self.codes(max_notes_per_subject=1), ["too-many-notes"])

    def test_missing_last_session_and_sections(self):
        self.note("Website", "# Website\n\n" + "Just prose with no headings. " * 10)
        self.assertEqual(self.codes(), ["no-last-session", "missing-section"])

    def test_obsidian_folder_is_ignored(self):
        self.tidy_vault()
        self.note(".obsidian/2026-01-01", "x")
        self.assertEqual(self.codes(), [])


if __name__ == "__main__":
    unittest.main()
