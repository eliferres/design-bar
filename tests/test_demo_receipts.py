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


def rejoin(chunks):
    """Undo the drawing's wrapping: a wrapped row ends in " \\" and the chunks
    rejoin with the one space the break ate."""
    return " ".join(c[:-2] if c.endswith(" \\") else c for c in chunks)


def shows_whole(drawn, line):
    """A row is the output line itself, or that line cut once at the end."""
    if drawn == line:
        return True
    head = drawn[: -len(ELLIPSIS)]
    return (
        drawn.endswith(ELLIPSIS)
        and drawn.count(ELLIPSIS) == 1
        and len(head) < len(line)
        and line.startswith(head)
    )


class TestPicture(unittest.TestCase):
    """The picture shows whole entries: nothing invented, nothing left out.

    It fits as many whole commands as it can and may stop before the last
    entry, but only between commands, and every output line of an entry it
    does show is drawn, in order.
    """

    @classmethod
    def setUpClass(cls):
        cls.transcript = load_transcript()
        cls.rows = picture_rows()

    def test_the_picture_shows_whole_entries_in_order(self):
        self.assertTrue(self.rows, "the picture has no session rows")
        index = 0
        for entry in self.transcript:
            if index == len(self.rows):
                break  # the picture stopped at a command boundary
            kind, drawn = self.rows[index]
            self.assertEqual(kind, "cmd", f"row {index + 1} should open {entry['cmd']}")
            chunks = [drawn]
            index += 1
            while index < len(self.rows) and self.rows[index][0] == "cont":
                chunks.append(self.rows[index][1][4:])
                index += 1
            self.assertEqual(
                rejoin(chunks), entry["cmd"],
                "the command rows do not rebuild the recorded command",
            )
            for line in [l for l in entry["out"].splitlines() if l.strip()]:
                self.assertLess(
                    index, len(self.rows),
                    f"the picture stops inside {entry['cmd']}, before {line!r}",
                )
                kind, drawn = self.rows[index]
                self.assertEqual(
                    kind, "out", f"row {index + 1} should be output line {line!r}"
                )
                self.assertTrue(
                    shows_whole(drawn, line),
                    f"row {index + 1} is {drawn!r}, expected {line!r} whole or "
                    "end-trimmed with one ellipsis",
                )
                index += 1
        self.assertEqual(
            index, len(self.rows),
            f"{len(self.rows) - index} drawn row(s) the transcript does not account for",
        )


if __name__ == "__main__":
    unittest.main()
