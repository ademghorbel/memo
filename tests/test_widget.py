import tkinter as tk
import unittest

from memo.checker import Finding, Report
from memo.widget import face
from memo.widget.text import details, summarize


def report(*findings):
    return Report(vault="v", notes=3, words=900, findings=list(findings))


class TextTests(unittest.TestCase):
    def test_tidy(self):
        text = summarize(report())
        self.assertIn("All tidy", text)
        self.assertIn("3 notes, 900 words", text)
        self.assertEqual(details(report()), "Nothing to tidy.")

    def test_counts_and_plurals(self):
        r = report(
            Finding("warning", "oversize-note", "700 words", "a.md"),
            Finding("warning", "oversize-note", "650 words", "b.md"),
            Finding("info", "missing-section", "No section: History.", "c.md"),
        )
        text = summarize(r)
        self.assertIn("2 notes over the word limit", text)
        self.assertIn("1 note missing a section", text)
        self.assertIn("a.md: 700 words", details(r))

    def test_details_limit(self):
        r = report(*[Finding("warning", "broken-link", "x", f"{i}.md") for i in range(10)])
        self.assertIn("...and 2 more", details(r, limit=8))


class FaceTests(unittest.TestCase):
    def test_every_state_draws(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            c = tk.Canvas(root, width=face.SIZE, height=face.SIZE)
            for state in face.STATES:
                for t in (0.0, 0.07, 1.3, 2.9):
                    face.draw(c, state, t, 1.5)
                    self.assertTrue(c.find_all(), state)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
