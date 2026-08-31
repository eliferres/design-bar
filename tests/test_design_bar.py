"""Hermetic tests for the design bar tools.

Every test shells out to the tool exactly as a user would and asserts on
the bare exit code and the printed report. No fixtures are generated -
the shipped rulebooks and demo pages ARE the fixtures, so a drift
between docs and behavior fails here first.
"""

import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DNA_LINT = ROOT / "tools" / "dna_lint.py"
SLOP_SCAN = ROOT / "tools" / "slop_scan.py"
CAPTURE = ROOT / "tools" / "capture.sh"
SHOT_GUARD = ROOT / "tools" / "shot_guard.py"
TELLS = ROOT / "config" / "tells.json"


def run(*args, env=None):
    return subprocess.run(
        list(args), capture_output=True, text=True, env=env, cwd=ROOT
    )


def lint(path):
    return run(sys.executable, str(DNA_LINT), str(path))


def scan(page, tells=TELLS):
    return run(sys.executable, str(SLOP_SCAN), str(page), "--tells", str(tells))


class TestDnaLint(unittest.TestCase):
    def test_example_rulebook_lints_complete(self):
        result = lint(ROOT / "rulebook" / "example-dna.md")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("COMPLETE", result.stdout)

    def test_template_lints_complete(self):
        result = lint(ROOT / "rulebook" / "TEMPLATE.md")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("DEEPEN gap", result.stdout)

    def test_broken_rulebook_fails_with_named_gaps(self):
        result = lint(ROOT / "demo" / "broken-rulebook.md")
        self.assertEqual(result.returncode, 1, result.stdout)
        for gap in (
            "no front-matter",
            "missing section: reference",
            "missing section: type scale",
            "no provenance marker",
            "no dated entry",
        ):
            self.assertIn(gap, result.stdout)

    def test_missing_file_exits_2(self):
        result = lint(ROOT / "rulebook" / "does-not-exist.md")
        self.assertEqual(result.returncode, 2)

    def test_usage_error_exits_2(self):
        result = run(sys.executable, str(DNA_LINT))
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stdout)


class TestSlopScan(unittest.TestCase):
    def test_clean_page_passes(self):
        result = scan(ROOT / "demo" / "clean-page.html")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("CLEAN", result.stdout)

    def test_slop_page_fails(self):
        result = scan(ROOT / "demo" / "slop-page.html")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("SLOP", result.stdout)

    def test_slop_page_names_each_tell_class(self):
        out = scan(ROOT / "demo" / "slop-page.html").stdout
        for tell in (
            "banned phrase",
            "lorem ipsum",
            "emoji",
            "placeholder alt",
            "without alt text",
            "gradient",
            "box-shadow",
            "stock call-to-action",
        ):
            self.assertIn(tell, out)

    def test_usage_error_exits_2(self):
        result = run(sys.executable, str(SLOP_SCAN), "page.html")
        self.assertEqual(result.returncode, 2)

    def test_bad_config_exits_2(self):
        result = scan(ROOT / "demo" / "clean-page.html",
                      tells=ROOT / "demo" / "broken-rulebook.md")
        self.assertEqual(result.returncode, 2)


class TestCapture(unittest.TestCase):
    def test_usage_error_exits_2(self):
        result = run("bash", str(CAPTURE))
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stdout)

    def test_missing_page_exits_2(self):
        result = run("bash", str(CAPTURE), "no-such-page.html", "/tmp/out")
        self.assertEqual(result.returncode, 2)

    def test_broken_browser_trusts_the_png(self):
        env = dict(os.environ, DESIGN_BAR_BROWSER="/no/such/browser")
        out_dir = ROOT / "tests" / ".capture-scratch"
        result = run("bash", str(CAPTURE),
                     str(ROOT / "demo" / "clean-page.html"),
                     str(out_dir), env=env)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("FAILED", result.stdout)
        self.assertIn("no file written", result.stdout)


def make_png(rows):
    """Build a minimal 8-bit RGB PNG from rows of (r, g, b) pixel tuples."""
    height, width = len(rows), len(rows[0])
    raw = b"".join(
        b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in rows
    )

    def chunk(ctype, body):
        payload = ctype + body
        return struct.pack(">I", len(body)) + payload + struct.pack(
            ">I", zlib.crc32(payload)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class TestShotGuard(unittest.TestCase):
    def guard(self, rows, *flags, keep=None):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            fh.write(make_png(rows))
            path = fh.name
        try:
            result = run(sys.executable, str(SHOT_GUARD), *flags, path)
            if keep is not None:
                keep.append(Path(path).read_bytes())
            return result
        finally:
            os.unlink(path)

    def test_blank_bottom_row_passes(self):
        ink, paper = (33, 29, 25), (250, 249, 247)
        rows = [[ink] * 8] * 4 + [[paper] * 8] * 4
        result = self.guard(rows)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("uniform", result.stdout)

    def test_content_on_bottom_row_fails(self):
        ink, paper = (33, 29, 25), (250, 249, 247)
        rows = [[paper] * 8] * 7 + [[paper] * 4 + [ink] * 4]
        result = self.guard(rows)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("truncated", result.stdout)

    def test_trim_cuts_dead_canvas_to_a_48px_pad(self):
        ink, paper = (33, 29, 25), (250, 249, 247)
        rows = [[ink] * 8] * 2 + [[paper] * 8] * 200
        written = []
        result = self.guard(rows, "--trim", keep=written)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("trimmed", result.stdout)
        height = struct.unpack(">I", written[0][20:24])[0]
        self.assertEqual(height, 50)


class TestDemoHygiene(unittest.TestCase):
    def test_both_demo_pages_carry_viewport_meta(self):
        for name in ("clean-page.html", "slop-page.html"):
            text = (ROOT / "demo" / name).read_text(encoding="utf-8")
            self.assertIn('name="viewport"', text, name)


if __name__ == "__main__":
    unittest.main()
