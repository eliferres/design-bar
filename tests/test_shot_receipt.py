"""Hold demo/clean-page-1280.png to the number it shows.

The README calls that picture the repo graded by its own tools, and one
of the numbers on it is the test count. Nothing used to tie the picture
to that count, so a suite that grew left a picture claiming an old
number with no check to catch it.

demo/shot-receipt.json records the exact bytes and pixel size of the
committed shot together with the count the page claimed when the shot
was taken. The three tests below close the loop: the committed file is
the file the receipt records, the receipt's count is the count written
on the page, and that count is what running the suite really produces.
Change any one of them and this fails.

Regenerate after a real recapture (bash tools/capture.sh
demo/clean-page.html shots/ and copy shots/shot-1280.png over
demo/clean-page-1280.png) with
UPDATE_SHOT_RECEIPT=1 python -m unittest tests.test_shot_receipt
and never by hand.
"""

import hashlib
import importlib.util
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOT = ROOT / "demo" / "clean-page-1280.png"
PAGE = ROOT / "demo" / "clean-page.html"
RECEIPT = ROOT / "demo" / "shot-receipt.json"
SHOT_GUARD = ROOT / "tools" / "shot_guard.py"

PROOF_ROW = re.compile(
    r'<span class="proof-n display">([\d/]+)</span><span>tests pass'
)


def _load_module(name, path):
    """Import a tool module directly, the way the main suite does."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shot_guard = _load_module("shot_guard", SHOT_GUARD)


def page_count_claim():
    """The count the demo page prints on its own scorecard, as '26/26'."""
    match = PROOF_ROW.search(PAGE.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"no test-count row in {PAGE.name}")
    return match.group(1)


def suite_size():
    """How many tests the shipped suite really holds."""
    import unittest as ut

    return ut.defaultTestLoader.discover(str(ROOT / "tests")).countTestCases()


def measure_shot():
    data = SHOT.read_bytes()
    width, height, _channels, _raw, _chunks = shot_guard.read_png(str(SHOT))
    return {
        "shot": SHOT.relative_to(ROOT).as_posix(),
        "page": PAGE.relative_to(ROOT).as_posix(),
        "width": width,
        "height": height,
        "sha256": hashlib.sha256(data).hexdigest(),
        "tests_shown": page_count_claim(),
    }


if os.environ.get("UPDATE_SHOT_RECEIPT") == "1":
    RECEIPT.write_text(
        json.dumps(measure_shot(), indent=2) + "\n", encoding="utf-8"
    )
    print(f"rewrote {RECEIPT} from the committed shot and page")


class TestShotReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_the_committed_shot_is_the_one_the_receipt_records(self):
        width, height, _c, _raw, _chunks = shot_guard.read_png(str(SHOT))
        self.assertEqual(
            (width, height),
            (self.receipt["width"], self.receipt["height"]),
            "the committed shot is not the size the receipt records",
        )
        self.assertEqual(
            hashlib.sha256(SHOT.read_bytes()).hexdigest(),
            self.receipt["sha256"],
            f"{SHOT.name} changed since the receipt was written: recapture it "
            "and regenerate the receipt with UPDATE_SHOT_RECEIPT=1",
        )

    def test_the_receipt_shows_the_count_written_on_the_page(self):
        self.assertEqual(
            page_count_claim(),
            self.receipt["tests_shown"],
            "the page's test count moved after the shot was taken",
        )

    def test_the_count_on_the_page_is_the_real_suite_size(self):
        count = suite_size()
        self.assertEqual(
            page_count_claim(),
            f"{count}/{count}",
            "the page claims a test count the suite does not have",
        )


if __name__ == "__main__":
    unittest.main()
