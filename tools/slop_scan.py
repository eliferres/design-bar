#!/usr/bin/env python3
"""Scan a rendered HTML page for structural AI-slop tells.

Copy slop is a phrase problem; structural slop is a markup problem - the
default gradient nobody chose, the same shadow on every box, headings
that open with emoji, alt text that says "image". Each tell here is a
deterministic string or pattern check driven by a config file, so the
list is yours to tune: these defaults are tells we kept meeting, not a
theory of bad design.

Exit codes: 0 = clean, 1 = tells found, 2 = usage or IO error.
"""

import json
import re
import sys
from html.parser import HTMLParser

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
CTA_TAGS = {"a", "button"}
EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff]"
)
SHADOW = re.compile(r"box-shadow\s*:\s*([^;}]+)", re.IGNORECASE)


class PageReader(HTMLParser):
    """Collect headings, CTA texts, images, and visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.headings = []
        self.ctas = []
        self.images = []
        self.text = []
        self._bucket = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if tag in HEADINGS or tag in CTA_TAGS:
            self._bucket = []
        if tag == "img":
            self.images.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack.reverse()
            self.stack.remove(tag)
            self.stack.reverse()
        if self._bucket is not None and (tag in HEADINGS or tag in CTA_TAGS):
            joined = " ".join(self._bucket).split()
            record = (tag, " ".join(joined))
            if tag in HEADINGS:
                self.headings.append(record)
            else:
                self.ctas.append(record)
            self._bucket = None

    def handle_data(self, data):
        if "style" in self.stack or "script" in self.stack:
            return
        if self._bucket is not None:
            self._bucket.append(data)
        self.text.append(data)


def load(path, reader):
    try:
        with open(path, encoding="utf-8") as fh:
            return reader(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}")
        sys.exit(2)


def check_phrases(cfg, text, findings):
    lowered = text.lower()
    for phrase in cfg.get("banned_phrases", []):
        if phrase.lower() in lowered:
            findings.append(f'banned phrase present: "{phrase}"')


def check_lorem(cfg, text, findings):
    if cfg.get("flag_lorem", True) and "lorem ipsum" in text.lower():
        findings.append("placeholder copy: lorem ipsum shipped to a reader")


def check_emoji_headings(cfg, headings, findings):
    limit = cfg.get("max_emoji_headings", 0)
    hits = [t for tag, t in headings if t and EMOJI.match(t)]
    if len(hits) > limit:
        findings.append(
            f'{len(hits)} heading(s) open with emoji (limit {limit}): '
            f'first is "{hits[0]}"'
        )


def check_alt_text(cfg, images, findings):
    placeholders = {p.lower() for p in cfg.get("placeholder_alts", [])}
    for img in images:
        alt = img.get("alt")
        src = img.get("src", "?")
        if alt is None:
            findings.append(f"image without alt text: {src}")
        elif alt.strip().lower() in placeholders:
            findings.append(f'placeholder alt text "{alt}" on {src}')


def check_gradients(cfg, html, findings):
    lowered = html.lower()
    for pair in cfg.get("default_gradient_pairs", []):
        if all(c.lower() in lowered for c in pair):
            findings.append(
                "framework-default gradient nobody chose: "
                + " + ".join(pair)
            )


def check_shadow_soup(cfg, html, findings):
    limit = cfg.get("max_repeated_shadow", 3)
    counts = {}
    for match in SHADOW.finditer(html):
        value = " ".join(match.group(1).split())
        counts[value] = counts.get(value, 0) + 1
    for value, count in counts.items():
        if count > limit:
            findings.append(
                f"the same box-shadow appears {count} times (limit {limit}): "
                f"{value} - one elevation for everything is a tell, "
                "not a system"
            )


def check_stock_ctas(cfg, ctas, findings):
    stock = {s.lower() for s in cfg.get("stock_cta_texts", [])}
    limit = cfg.get("max_stock_ctas", 0)
    hits = [t for _, t in ctas if t.strip().lower() in stock]
    if len(hits) > limit:
        findings.append(
            f'{len(hits)} stock call-to-action(s) (limit {limit}): '
            + ", ".join(f'"{h}"' for h in sorted(set(hits)))
        )


def main(argv):
    if len(argv) != 4 or argv[2] != "--tells":
        print("usage: slop_scan.py <page.html> --tells <tells.json>")
        return 2
    html = load(argv[1], lambda fh: fh.read())
    cfg = load(argv[3], json.load)

    reader = PageReader()
    reader.feed(html)
    text = " ".join(" ".join(reader.text).split())

    findings = []
    check_phrases(cfg, text, findings)
    check_lorem(cfg, text, findings)
    check_emoji_headings(cfg, reader.headings, findings)
    check_alt_text(cfg, reader.images, findings)
    check_gradients(cfg, html, findings)
    check_shadow_soup(cfg, html, findings)
    check_stock_ctas(cfg, reader.ctas, findings)

    print("slop-scan report")
    print(f"page:  {argv[1]}")
    print(f"tells: {argv[3]}")
    print()
    if findings:
        print(f"SLOP - {len(findings)} tell(s):")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("CLEAN - none of the configured tells present.")
    print("That clears the floor, not the bar: a page can pass every")
    print("mechanical tell and still be dull. The review panel judges that.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
