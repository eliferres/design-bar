"""Tests for never_list.py, the rulebook's "never" list checked against code.

Each test writes a small rulebook and a small UI file into a temp
directory and runs the tool the way a user would, asserting on the exit
code and the printed report. The last tests run it on the shipped
example rulebook and demo pages.
"""

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEVER_LIST = ROOT / "tools" / "never_list.py"


def rulebook(*bans):
    lines = "\n".join(f"- {ban}" for ban in bans)
    return f"# Rulebook\n\n## Spacing\n\n- 8px grid.\n\n## Never\n\n{lines}\n\n## Decision log\n\n- 2026-01-01 (x): y\n"


class NeverListCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, body):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def check(self, bans, files, *extra):
        self.write("rulebook.md", rulebook(*bans))
        for name, body in files.items():
            self.write(name, body)
        return subprocess.run(
            [sys.executable, str(NEVER_LIST), "rulebook.md", *files, *extra],
            capture_output=True, text=True, cwd=self.dir,
        )


class TestRules(NeverListCase):
    def test_a_purple_gradient_ban_catches_a_gradient_wrapped_over_lines(self):
        result = self.check(
            ["Purple-to-blue gradients behind hero text."],
            {"page.css": """\
                .hero {
                  background: linear-gradient(
                    135deg, #667eea 0%,
                    #764ba2 100%);
                }
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("[gradient] page.css:2", result.stdout)

    def test_a_purple_gradient_ban_lets_a_warm_gradient_through(self):
        result = self.check(
            ["Purple-to-blue gradients behind hero text."],
            {"page.css": ".hero { background: linear-gradient(#f6d365, #fda085); }\n"},
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_plain_gradient_ban_catches_any_gradient(self):
        result = self.check(
            ["Gradients of any kind."],
            {"page.css": ".hero { background: linear-gradient(#f6d365, #fda085); }\n"},
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_banned_words_are_caught_in_copy_and_not_in_class_names(self):
        result = self.check(
            ['Headline copy that says "seamless" or "unlock".'],
            {"page.html": """\
                <div class="seamless-grid">
                  <h1>Unlock your team</h1>
                </div>
                <!-- seamless is banned -->
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("[banned-words] page.html:2", result.stdout)
        self.assertNotIn("page.html:1", result.stdout)
        self.assertNotIn("page.html:4", result.stdout)

    def test_banned_words_reach_string_literals_but_not_class_helpers(self):
        result = self.check(
            ['Copy that says "seamless".'],
            {"Hero.tsx": """\
                export const Hero = () => (
                  <h1 className={cn("seamless", big && "seamless-xl")}>{title}</h1>
                );
                const title = "A seamless start";
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Hero.tsx:4", result.stdout)
        self.assertNotIn("Hero.tsx:2", result.stdout)

    def test_large_radius_and_blur_orb_rules(self):
        result = self.check(
            ["Rounded-2xl cards.", "Decorative blur orbs behind content."],
            {"page.html": """\
                <div class="rounded-2xl p-6">card</div>
                <style>.pill { border-radius: 999px; } .orb { filter: blur(60px); } .soft { filter: blur(4px); }</style>
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("[large-radius] page.html:1", result.stdout)
        self.assertIn("[blur-orb] page.html:2", result.stdout)
        self.assertNotIn("[large-radius] page.html:2", result.stdout)

    def test_italic_wordmark_and_dark_grid_rules(self):
        result = self.check(
            ["An italic wordmark.", "A dark data grid."],
            {"page.css": """\
                .wordmark { font-style: italic; }
                .data-grid { background: #111111; }
                .card { background: #111111; }
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("[italic-wordmark] page.css:1", result.stdout)
        self.assertIn("[dark-grid] page.css:2", result.stdout)
        self.assertNotIn("page.css:3", result.stdout)


class TestHumanChecks(NeverListCase):
    def test_a_ban_no_rule_can_read_is_named_for_a_person_and_does_not_fail(self):
        result = self.check(
            ["Stock photos of people pointing at laptops."],
            {"page.css": ".a { color: red; }\n"},
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Stock photos of people pointing at laptops.", result.stdout)
        self.assertIn("needs a person", result.stdout)


class TestAllowComment(NeverListCase):
    def test_an_allow_comment_with_a_reason_on_the_line_or_above_lets_the_hit_through(self):
        result = self.check(
            ["Gradients of any kind."],
            {"page.css": """\
                /* never-allow: gradient the brand's own hero, signed off */
                .hero { background: linear-gradient(#f6d365, #fda085); }
                .foot { background: linear-gradient(#000, #333); } /* never-allow: gradient print-only footer */
                """},
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("the brand's own hero, signed off", result.stdout)
        self.assertIn("2 allowed", result.stdout)

    def test_an_allow_comment_without_a_reason_or_for_another_rule_lets_nothing_through(self):
        result = self.check(
            ["Gradients of any kind."],
            {"page.css": """\
                .a { background: linear-gradient(#f6d365, #fda085); } /* never-allow: gradient */
                .b { background: linear-gradient(#f6d365, #fda085); } /* never-allow: blur-orb soft */
                """},
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("page.css:1", result.stdout)
        self.assertIn("page.css:2", result.stdout)


class TestContract(NeverListCase):
    def test_json_carries_findings_human_checks_and_allowed(self):
        result = self.check(
            ["Gradients of any kind.", "No clip art."],
            {"page.css": ".a { background: linear-gradient(#000, #333); }\n"},
            "--json",
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["findings"][0]["rule"], "gradient")
        self.assertEqual(report["findings"][0]["line"], 1)
        self.assertEqual(report["needs_a_person"][0]["ban"], "No clip art.")
        self.assertEqual(report["allowed"], [])

    def test_a_rulebook_without_a_never_section_is_a_usage_error(self):
        book = self.write("rulebook.md", "# Rulebook\n\n## Spacing\n\n- 8px.\n")
        page = self.write("page.css", ".a {}\n")
        result = subprocess.run([sys.executable, str(NEVER_LIST), str(book), str(page)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no 'Never' section", result.stderr)
        self.assertEqual(result.stderr.count("\n"), 1)

    def test_a_missing_target_is_a_usage_error(self):
        result = self.check(["Gradients."], {}, "nowhere.css")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nowhere.css", result.stderr)

    def test_version(self):
        result = subprocess.run([sys.executable, str(NEVER_LIST), "--version"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout, r"^never_list\.py \d+\.\d+\.\d+$")

    def test_directories_are_walked_and_vendor_code_skipped(self):
        self.write("site/node_modules/pkg/x.css", ".a { background: linear-gradient(#000, #333); }\n")
        self.write("site/src/ok.css", ".a { color: red; }\n")
        book = self.write("rulebook.md", rulebook("Gradients of any kind."))
        result = subprocess.run([sys.executable, str(NEVER_LIST), str(book), str(self.dir / "site")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


class TestShippedExample(unittest.TestCase):
    def run_on(self, page):
        return subprocess.run(
            [sys.executable, str(NEVER_LIST), "rulebook/example-dna.md", page],
            capture_output=True, text=True, cwd=ROOT,
        )

    def test_the_clean_demo_page_honors_the_example_never_list(self):
        result = self.run_on("demo/clean-page.html")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_the_slop_demo_page_breaks_it(self):
        result = self.run_on("demo/slop-page.html")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("[gradient] demo/slop-page.html:13", result.stdout)
        self.assertIn("[banned-words] demo/slop-page.html:28", result.stdout)


if __name__ == "__main__":
    unittest.main()
