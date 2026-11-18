import tempfile
import unittest
from pathlib import Path

from memo.checker import Config, check
from memo.fixer import fix, undo

FILLER = " ".join(["word"] * 40)


def subject(name: str, history: list[str], extra: str = "") -> str:
    return (f"# {name}\n\nAbout {name}. {extra}\n\n## Current state\n- fine\n\n"
            f"## Open items / next\n- nothing\n\n## History\n" + "\n".join(history) + "\n")


class FixerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.cfg = Config(max_words=300)
        (self.vault / "Last Session.md").write_text("# Last Session\n\n" + FILLER + "\n", encoding="utf-8")

    def write(self, name, text):
        (self.vault / f"{name}.md").write_text(text, encoding="utf-8")

    def read(self, name):
        return (self.vault / f"{name}.md").read_text(encoding="utf-8")

    def test_oversize_note_moves_oldest_history_to_new_archive(self):
        history = [f"- 2026-01-{d:02d}: {FILLER}" for d in range(20, 0, -1)]  # newest first
        self.write("Big", subject("Big", history))
        result = fix(self.vault, self.cfg)

        big, archive = self.read("Big"), self.read("Big - Archive")
        self.assertLessEqual(len(big.split()), 300)
        self.assertIn("2026-01-20", big)  # newest stays
        self.assertNotIn("2026-01-01", big)  # oldest moved
        self.assertIn("2026-01-01", archive)
        self.assertIn("[[Big - Archive]]", big)  # pointer added
        self.assertIn("[[Big]]", archive)
        self.assertEqual(check(self.vault, self.cfg).mood, "tidy")
        self.assertTrue(result.backup)

    def test_existing_archive_and_pointer_are_reused(self):
        history = [f"- 2026-02-{d:02d}: {FILLER}" for d in range(9, 0, -1)]
        self.write("Big", subject("Big", history + ["- Older history: [[Big - Archive]]"]))
        self.write("Big - Archive", "# Big - Archive\n\nOlder lines from [[Big]].\n\n"
                                    "## History\n- 2025-12-01: very old entry.\n")
        fix(self.vault, self.cfg)
        big, archive = self.read("Big"), self.read("Big - Archive")
        self.assertEqual(big.count("Older history"), 1)
        self.assertTrue(big.rstrip().endswith("- Older history: [[Big - Archive]]"))
        lines = archive.splitlines()
        self.assertLess(lines.index(next(l for l in lines if "2026-02-01" in l)),
                        lines.index("- 2025-12-01: very old entry."))  # moved lines go on top

    def test_missing_section_stub_and_empty_dir(self):
        text = subject("Gear", ["- x"], FILLER).replace("## History\n- x\n", "")
        self.write("Gear", text)
        self.write("Tiny", "# Tiny\n")
        (self.vault / "empty").mkdir()
        fix(self.vault, self.cfg)
        self.assertIn("## History", self.read("Gear"))
        self.assertFalse((self.vault / "Tiny.md").exists())
        self.assertFalse((self.vault / "empty").exists())

    def test_dry_run_changes_nothing(self):
        self.write("Tiny", "# Tiny\n")
        result = fix(self.vault, self.cfg, dry_run=True)
        self.assertTrue(result.done)
        self.assertTrue((self.vault / "Tiny.md").exists())
        self.assertFalse((self.vault / ".memo").exists())

    def test_undo_restores_everything(self):
        history = [f"- 2026-03-{d:02d}: {FILLER}" for d in range(15, 0, -1)]
        original = subject("Big", history)
        self.write("Big", original)
        self.write("Tiny", "# Tiny\n")
        fix(self.vault, self.cfg)
        undo(self.vault)
        self.assertEqual(self.read("Big"), original)
        self.assertEqual(self.read("Tiny"), "# Tiny\n")
        self.assertFalse((self.vault / "Big - Archive.md").exists())
        self.assertEqual(undo(self.vault), ["Nothing to undo."])

    def test_things_needing_judgment_are_left_alone(self):
        self.write("2026-01-05 notes", "# x\n\n" + FILLER)
        before = self.read("2026-01-05 notes")
        result = fix(self.vault, self.cfg)
        self.assertEqual(self.read("2026-01-05 notes"), before)
        self.assertTrue(any("Per-session" in l for l in result.left))

    def test_links_to_deleted_notes_are_unlinked(self):
        self.write("Gone", subject("Gone", ["- 2026-01-01: x"]))
        self.write("Kept", subject("Kept", ["- 2026-01-02: see [[Gone]]", "- Older history: [[Kept - Archive]]"],
                                   extra="Related: [[Gone|the old one]], [[Last Session]], `[[Gone]]`."))
        (self.vault / "Gone.md").unlink()
        result = fix(self.vault, self.cfg)
        kept = self.read("Kept")
        self.assertIn("see Gone", kept)
        self.assertIn("Related: the old one, [[Last Session]], `[[Gone]]`.", kept)
        self.assertNotIn("Older history", kept)
        self.assertEqual(check(self.vault, self.cfg).mood, "tidy")
        undo(self.vault)
        self.assertIn("[[Gone|the old one]]", self.read("Kept"))


if __name__ == "__main__":
    unittest.main()
