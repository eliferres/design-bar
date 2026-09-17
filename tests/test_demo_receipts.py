"""Hold demo/transcript.json and demo/terminal.svg to a real run.

The README walkthrough, the transcript and the terminal picture all
claim the same session. This replays every transcript command inside a
throwaway copy of the checkout and demands the recorded output and exit
code byte for byte, then checks that every row drawn in the picture
traces back to that transcript.

Regenerate the transcript from a real run with
UPDATE_DEMO_TRANSCRIPT=1 python -m unittest tests.test_demo_receipts
and never by hand.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "demo" / "transcript.json"
TERMINAL = ROOT / "demo" / "terminal.svg"
CHECKOUT_PLACEHOLDER = "/path/to/checkout"
SVG = "{http://www.w3.org/2000/svg}"
ELLIPSIS = "…"
SKIP = shutil.ignore_patterns(
    ".git", "__pycache__", ".pytest_cache", ".DS_Store", "shots", "build", "dist"
)


def load_transcript():
    return json.loads(TRANSCRIPT.read_text(encoding="utf-8"))


def replay(entries):
    """Run every command in a copy of the checkout; return new entries."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "checkout"
        shutil.copytree(ROOT, copy, ignore=SKIP)
        # macOS resolves /var to /private/var, so a command that prints the
        # directory it ran in can show either spelling of the same path.
        roots = {str(copy), str(copy.resolve())}
        fresh = []
        for entry in entries:
            proc = subprocess.run(
                ["bash", "-c", entry["cmd"]],
                cwd=copy,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            out = proc.stdout
            for root in roots:
                out = out.replace(root, CHECKOUT_PLACEHOLDER)
            fresh.append(
                {"cmd": entry["cmd"], "out": out.rstrip("\n"), "status": proc.returncode}
            )
    return fresh


def picture_rows():
    """Every drawn row of the terminal picture, in order, as (kind, text).

    kind is "cmd" for the prompted first row of a command, "cont" for a
    backslash continuation row, and "out" for an output row. The title bar
    label is chrome, not session text: it is the only row carrying its own
    font-size, and it is skipped.
    """
    rows = []
    for text in ET.parse(TERMINAL).getroot().iter(f"{SVG}text"):
        if text.get("font-size"):
            continue
        drawn = "".join(text.itertext())
        classes = [text.get("class")] + [t.get("class") for t in text]
        if "p" in classes:
            rows.append(("cmd", drawn[1:]))
        elif text.get("class") == "cmd":
            rows.append(("cont", drawn))
        else:
            rows.append(("out", drawn))
    return rows


if os.environ.get("UPDATE_DEMO_TRANSCRIPT") == "1":
    TRANSCRIPT.write_text(
        json.dumps(replay(load_transcript()), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"rewrote {TRANSCRIPT} from a real run")


class TestTranscript(unittest.TestCase):
    def test_every_entry_replays_to_its_recorded_output(self):
        recorded = load_transcript()
        fresh = replay(recorded)
        for old, new in zip(recorded, fresh):
            self.assertEqual(
                new["out"], old["out"], f"output drifted for: {old['cmd']}"
            )
            self.assertEqual(
                new["status"], old["status"], f"exit code drifted for: {old['cmd']}"
            )


class TestPicture(unittest.TestCase):
    """Nothing is drawn in the picture that the transcript cannot account for."""

    @classmethod
    def setUpClass(cls):
        cls.transcript = load_transcript()
        cls.rows = picture_rows()

    def test_commands_rebuild_the_transcript_commands_in_order(self):
        rebuilt = []
        for kind, drawn in self.rows:
            if kind == "cmd":
                rebuilt.append([drawn])
            elif kind == "cont":
                rebuilt[-1].append(drawn[4:])
        # A wrapped command breaks at a space and marks the break with " \".
        joined = [" ".join(c[:-2] if c.endswith(" \\") else c for c in chunks)
                  for chunks in rebuilt]
        expected = [entry["cmd"] for entry in self.transcript]
        self.assertEqual(joined, expected[: len(joined)])

    def test_every_output_row_is_a_prefix_of_a_recorded_line(self):
        real = [
            line
            for entry in self.transcript
            for line in entry["out"].splitlines()
            if line.strip()
        ]
        for kind, drawn in self.rows:
            if kind != "out":
                continue
            head = drawn[: -len(ELLIPSIS)] if drawn.endswith(ELLIPSIS) else drawn
            self.assertTrue(
                any(line == drawn or line.startswith(head) for line in real),
                f"picture row not in the transcript: {drawn!r}",
            )


if __name__ == "__main__":
    unittest.main()
