#!/usr/bin/env python3
"""Check UI code against the "Never" list in a design rulebook.

The slop scanner asks whether a page carries defaults nobody chose. This
asks a narrower question: does the code contain something this rulebook
says never to ship. The bans are read from the rulebook's "Never"
section, one bullet each, and are never invented here. Each ban whose
wording names a shape this tool can see in source (a gradient, a large
card corner, a blur orb, an italic wordmark, a dark data grid, quoted
words in copy) becomes a deterministic check; every other ban is printed
as needing a person, so nothing on the list is silently dropped.

A hit can be let through on purpose with a comment on its line or the
line above: `never-allow: <rule> <reason>`. It is printed with its
reason and never changes the exit code.

Exit codes: 0 = no ban broken, 1 = a ban broken, 2 = usage or IO error.
"""

__version__ = "1.2.0"

import argparse
import json
import os
import re
import sys
from typing import Callable, Dict, List, Optional, Tuple

UI_EXT = {".css", ".scss", ".less", ".sass", ".tsx", ".jsx", ".ts", ".js", ".mjs",
          ".cjs", ".html", ".htm", ".svelte", ".vue", ".astro"}
SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".git", "vendor", "coverage"}

Statement = Dict[str, object]  # {"line": int, "text": str, "end": str}
Span = Tuple[int, str]          # (line, copy text)
Hit = Tuple[int, str]           # (line, snippet)


class UsageError(Exception):
    """Anything that stops the check from running at all: exit 2."""


# ---------------------------------------------------------------- the rulebook

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)")


def read_bans(path: str) -> List[str]:
    """Every bullet in the rulebook's Never section.

    The section is the heading whose text is just "Never" (a leading number
    such as "8." is ignored), or failing that the first heading containing
    the word. It runs to the next heading of the same or a higher level, so
    sub-headings that group the bans stay inside it."""
    try:
        # Read like the scanned files: a stray Latin-1 byte in a heading is
        # not a reason to refuse the whole rulebook.
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise UsageError(f"cannot read {path}: {exc.strerror}")
    headings = [(i, len(m.group(1)), m.group(2)) for i, line in enumerate(lines)
                for m in [HEADING.match(line)] if m]
    exact = [h for h in headings if re.fullmatch(r"(?:\d+[.)]?\s*)?never", h[2], re.I)]
    loose = [h for h in headings if re.search(r"\bnever\b", h[2], re.I)]
    if not (exact or loose):
        raise UsageError(f"no 'Never' section in {path}")
    start, level, _ = (exact or loose)[0]
    stop = next((i for i, lvl, _ in headings if i > start and lvl <= level), len(lines))
    bans: List[str] = []
    for line in lines[start + 1:stop]:
        if HEADING.match(line):
            continue
        bullet = BULLET.match(line)
        if bullet:
            bans.append(bullet.group(1))
        elif line.strip() and bans and line.startswith((" ", "\t")):
            bans[-1] += " " + line.strip()  # a bullet wrapped onto the next line
    if not bans:
        raise UsageError(f"the 'Never' section in {path} lists no bans (one per bullet)")
    return bans


# ---------------------------------------------------------------- reading source
# Matching runs on statements, not lines: a gradient wrapped over four lines
# is one declaration, and a line-by-line scan never sees it whole. Copy
# checks run on text nodes and string literals only, so a banned word in a
# class name or a comment is not a word anyone reads.

HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
PURPLE_WORD = re.compile(r"\b(purple|violet|indigo|fuchsia|magenta)\b", re.I)
# v3 spells a gradient bg-gradient-to-r; v4 spells it bg-linear-to-r,
# bg-linear-45, bg-radial or bg-conic.
TW_GRADIENT = re.compile(r"\b(?:bg-)?gradient-to-[a-z]+\b|\bbg-(?:linear|radial|conic)\b")
TW_PURPLE_STOP = re.compile(r"\b(?:from|via|to)-(?:purple|violet|indigo|fuchsia)-\d{2,3}\b")
CSS_GRADIENT = re.compile(r"\b(?:linear|radial|conic)-gradient\s*\(", re.I)
STRING_LIT = re.compile(r"\"[^\"\\\n]*(?:\\.[^\"\\\n]*)*\""
                        r"|'[^'\\\n]*(?:\\.[^'\\\n]*)*'"
                        r"|`[^`\\]*(?:\\.[^`\\]*)*`", re.S)
HTML_TEXT = re.compile(r">([^<>]*)<", re.S)
# Attributes whose value is an identifier, a URL or a class list. alt,
# title, placeholder and aria-label are copy and stay in scope.
NON_COPY_ATTR = re.compile(r"\b(?:class|className|id|href|src|srcSet|rel|type|name|key|role|"
                           r"for|htmlFor|style|data-[\w-]+)\s*=\s*$")
# Expressions whose every string is a class name: className={...} and the
# usual class-joining helpers.
NON_COPY_REGION = re.compile(r"\b(?:className|class)\s*=\s*\{"
                             r"|\b(?:clsx|cn|classnames|classNames|twMerge|cva)\s*\(")
ALLOW = re.compile(r"never-allow:[ \t]*([\w-]+)[ \t]+(.*)$")


def strip_comments(text: str) -> str:
    """Comments blanked with newlines kept, so line numbers stay the file's own."""
    def blank(m: "re.Match[str]") -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    return re.sub(r"(?m)^[ \t]*//.*$", blank, text)


def statements(text: str) -> List[Statement]:
    """Whitespace-normalised units cut at ; { } and at the > that closes a
    markup tag, each carrying the line it starts on. A > anywhere else (a
    child selector, an arrow function inside a JSX attribute) is part of
    the statement, so a selector or a tag is never cut in half."""
    out: List[Statement] = []
    buf: List[str] = []
    start: Optional[int] = None
    line = 1
    src = strip_comments(text)
    in_tag = False
    depth = 0  # braces inside a tag, as in className={...}
    for i, ch in enumerate(src):
        if ch == "\n":
            line += 1
            buf.append(" ")
            continue
        if start is None and not ch.isspace():
            start = line
        buf.append(ch)
        if ch == "<" and re.match(r"[A-Za-z/!]", src[i + 1:i + 2]):
            in_tag, depth = True, 0
            continue
        if in_tag:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
            elif ch == ">" and depth == 0:
                in_tag = False
                out.append({"line": start or line, "text": " ".join("".join(buf).split()), "end": ch})
                buf, start = [], None
            continue
        if ch in ";{}":
            out.append({"line": start or line, "text": " ".join("".join(buf).split()), "end": ch})
            buf, start = [], None
    tail = " ".join("".join(buf).split())
    if tail:
        out.append({"line": start or line, "text": tail, "end": ""})
    return [s for s in out if s["text"]]


def _closing(src: str, pos: int) -> int:
    """Index just past the bracket matching the one at pos, skipping string contents."""
    opener = src[pos]
    closer = {"{": "}", "(": ")"}[opener]
    depth, i = 0, pos
    while i < len(src):
        c = src[i]
        if c in "\"'`":
            j = i + 1
            while j < len(src) and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(src)


def copy_spans(text: str) -> List[Span]:
    """(line, text) for the two places readable copy ships: a markup text node and a string literal."""
    src = strip_comments(text)
    regions = [(m.end() - 1, _closing(src, m.end() - 1)) for m in NON_COPY_REGION.finditer(src)]

    def in_class_list(pos: int) -> bool:
        return any(a <= pos < b for a, b in regions)

    spans: List[Span] = []
    for m in HTML_TEXT.finditer(src):
        if not in_class_list(m.start(1)):
            spans.append((src.count("\n", 0, m.start(1)) + 1, m.group(1)))
    for m in STRING_LIT.finditer(src):
        if in_class_list(m.start()) or NON_COPY_ATTR.search(src[max(0, m.start() - 40):m.start()]):
            continue
        spans.append((src.count("\n", 0, m.start()) + 1, m.group(0)[1:-1]))
    return spans


def allow_reason(lines: List[str], line_no: int, rule: str) -> Optional[str]:
    """The reason of a never-allow comment for this rule on the hit's own line.
    Same line only: a trailing comment on one line must not reach the next."""
    if 0 < line_no <= len(lines):
        m = ALLOW.search(lines[line_no - 1])
        if m and m.group(1) == rule:
            reason = re.sub(r"\s*(\*/\s*\}?|-->)\s*$", "", m.group(2)).strip()
            if reason:
                return reason
    return None


def hue_chroma_lightness(hexstr: str) -> Tuple[float, float, float]:
    """(hue in degrees, chroma 0-1, lightness 0-1) of a hex color."""
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hi, lo = max(r, g, b), min(r, g, b)
    d = hi - lo
    if d == 0:
        hue = 0.0
    elif hi == r:
        hue = (60 * ((g - b) / d)) % 360
    elif hi == g:
        hue = 60 * ((b - r) / d) + 120
    else:
        hue = 60 * ((r - g) / d) + 240
    return hue, d, (hi + lo) / 2


def is_purple(text: str) -> bool:
    """A purple word, a Tailwind purple stop, or a hex between violet-blue and magenta."""
    if PURPLE_WORD.search(text) or TW_PURPLE_STOP.search(text):
        return True
    for m in HEX.finditer(text):
        hue, chroma, _ = hue_chroma_lightness(m.group(0))
        if 235 <= hue <= 310 and chroma >= 0.15:
            return True
    return False


# ---------------------------------------------------------------- the rules
# Each takes (statements, copy spans, the ban's own words) and returns hits.

def rule_gradient(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    """Any gradient; only purple ones when the ban names a purple hue."""
    purple_only = bool(PURPLE_WORD.search(ban))
    return [(s["line"], s["text"]) for s in stmts
            if (CSS_GRADIENT.search(s["text"]) or TW_GRADIENT.search(s["text"]))
            and (not purple_only or is_purple(s["text"]))]


LENGTH = re.compile(r"(?<![\w.#-])(\d*\.?\d+)(px|rem)\b")
CSS_RADIUS = re.compile(r"(?<![\w-])border(?:-[a-z]+)*-radius\s*:\s*([^;{}]+)", re.I)
TW_RADIUS = re.compile(r"\brounded(?:-[a-z]{1,2})?-(?:2xl|3xl|\[(\d*\.?\d+)(px|rem)\])")
JS_RADIUS = re.compile(r"\bborder(?:[A-Z][a-z]+)*Radius\s*:\s*(?:(\d+(?:\.\d+)?)\b|[\"']([^\"']*)[\"'])")


def _is_large(number: float, unit: str) -> bool:
    """16px (what rounded-2xl is) up to 99px; 1rem is 16px. A pill (999px,
    9999px, rounded-full) is its own shape, not a card corner."""
    px = number * 16 if unit == "rem" else number
    return 16 <= px < 100


def rule_large_radius(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    """A large card corner in CSS (any border-*-radius, px or rem), a
    Tailwind class (rounded-2xl and up, rounded-[24px]) or a React style
    (borderRadius: 24)."""
    out = []
    for s in stmts:
        t = s["text"]
        css = any(_is_large(float(n), u) for m in CSS_RADIUS.finditer(t) for n, u in LENGTH.findall(m.group(1)))
        tw = any(m.group(1) is None or _is_large(float(m.group(1)), m.group(2)) for m in TW_RADIUS.finditer(t))
        js = any(_is_large(float(m.group(1)), "px") if m.group(1)
                 else any(_is_large(float(n), u) for n, u in LENGTH.findall(m.group(2)))
                 for m in JS_RADIUS.finditer(t))
        if css or tw or js:
            out.append((s["line"], t))
    return out


def rule_blur_orb(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    """A heavy blur (Tailwind blur-2xl is 40px) on a positioned or round element."""
    out = []
    for s in stmts:
        t = s["text"]
        tw = re.search(r"\bblur-(?:2xl|3xl)\b", t) and re.search(r"\babsolute\b|\brounded-full\b", t)
        css = re.search(r"(?<![\w-])filter:\s*blur\(\s*(\d+)px", t)  # never backdrop-filter
        if tw or (css and int(css.group(1)) >= 40):
            out.append((s["line"], t))
    return out


def rule_banned_words(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    """The quoted words of the ban, as whole words in copy."""
    words = re.findall(r'"([^"]+)"', ban) or re.findall(r"“([^”]+)”", ban)
    if not words:
        return []
    pattern = re.compile("|".join(r"\b%s\b" % re.escape(w).replace(r"\ ", r"[\s-]") for w in words), re.I)
    return [(line, " ".join(text.split())) for line, text in spans if pattern.search(text)]


def _in_selector(stmts: List[Statement], selector_test: "re.Pattern[str]",
                 declaration_test: Callable[[str], bool]) -> List[Hit]:
    """Declarations matching declaration_test whose rule's selector, or the
    statement itself (a class list), matches selector_test."""
    out, selector = [], ""
    for s in stmts:
        if s["end"] == "{":
            selector = s["text"]
            continue
        # A rule's last declaration may omit its semicolon, so the statement
        # closing the block can still carry one: read it before resetting.
        text = s["text"][:-1].strip() if s["end"] == "}" else s["text"]
        if text and declaration_test(text) and selector_test.search(selector + " " + text):
            out.append((s["line"], text))
        if s["end"] == "}":
            selector = ""
    return out


WORDMARK = re.compile(r"logo|wordmark|brand", re.I)
# Table markup, or a class or selector naming a data grid or a row. A layout
# utility (flex-row, grid-cols-3, a bare Tailwind "grid") is not a data grid.
GRID_WORD = re.compile(r"\b(?:table|thead|tbody|tr|td|th)\b"
                       r"|(?<![\w-])(?:data-?grid|datagrid|table-row|row)(?![\w-])", re.I)
# A dark fill, but not one behind a dark: variant: that is a dark mode, not a
# dark grid on a light page.
DARK_TW = re.compile(r"(?<![\w:-])bg-(?:gray|zinc|slate|neutral|stone)-(?:800|900|950)\b|(?<![\w:-])bg-black\b")


def rule_italic_wordmark(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    return _in_selector(stmts, WORDMARK,
                        lambda t: bool(re.search(r"font-style:\s*italic|\bitalic\b", t)))


def _dark_fill(text: str) -> bool:
    if DARK_TW.search(text):
        return True
    for m in re.finditer(r"background(?:-color)?:\s*([^;]+)", text):
        if any(hue_chroma_lightness(h.group(0))[2] < 0.25 for h in HEX.finditer(m.group(1))):
            return True
    return False


def rule_dark_grid(stmts: List[Statement], spans: List[Span], ban: str) -> List[Hit]:
    return _in_selector(stmts, GRID_WORD, _dark_fill)


# (what the ban's words must contain, rule id, the check)
RULES = [
    (re.compile(r"\bgradients?\b", re.I), "gradient", rule_gradient),
    (re.compile(r"rounded-(?:2xl|3xl)|\blarge (?:corners?|radi(?:us|i))\b", re.I), "large-radius", rule_large_radius),
    (re.compile(r"\bblur(?:red)? (?:orbs?|blobs?)\b", re.I), "blur-orb", rule_blur_orb),
    (re.compile(r'"[^"]+"|“[^”]+”'), "banned-words", rule_banned_words),
    (re.compile(r"\bitalic\b.*\b(?:wordmark|logo)\b|\b(?:wordmark|logo)\b.*\bitalic\b", re.I),
     "italic-wordmark", rule_italic_wordmark),
    (re.compile(r"\bdark\b.*\b(?:grid|table)s?\b", re.I), "dark-grid", rule_dark_grid),
]


# ---------------------------------------------------------------- running it

def collect(targets: List[str]) -> List[str]:
    files = []
    for target in targets:
        if os.path.isdir(target):
            for root, dirs, names in os.walk(target):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                files += [os.path.join(root, n) for n in names if os.path.splitext(n)[1] in UI_EXT]
        elif os.path.isfile(target):
            files.append(target)
        else:
            raise UsageError(f"no such file or directory: {target}")
    return sorted(set(files))


def check(rulebook: str, targets: List[str]) -> dict:
    bans = read_bans(rulebook)
    files = collect(targets)
    if not files:
        raise UsageError(f"no UI files to check in {', '.join(targets)}")
    parsed = {}
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError as exc:
            raise UsageError(f"cannot read {path}: {exc.strerror}")
        parsed[path] = (raw.splitlines(), statements(raw), copy_spans(raw))
    findings, allowed, needs_a_person = [], [], []
    for ban in bans:
        matched = [(rid, rule) for signature, rid, rule in RULES if signature.search(ban)]
        if not matched:
            needs_a_person.append({"ban": ban})
            continue
        for rid, rule in matched:
            for path in files:
                lines, stmts, spans = parsed[path]
                for line_no, snippet in rule(stmts, spans, ban):
                    hit = {"rule": rid, "file": path, "line": line_no, "snippet": snippet[:160], "ban": ban}
                    reason = allow_reason(lines, line_no, rid)
                    if reason:
                        allowed.append(dict(hit, reason=reason))
                    else:
                        findings.append(hit)
    return {"rulebook": rulebook, "bans": len(bans), "files": len(files),
            "findings": findings, "allowed": allowed, "needs_a_person": needs_a_person}


def print_report(result: dict, targets: List[str]) -> None:
    print("never-list report")
    print(f"rulebook: {result['rulebook']} ({result['bans']} ban(s))")
    print(f"targets:  {', '.join(targets)} ({result['files']} file(s))")
    print()
    if result["findings"]:
        print(f"BROKEN - {len(result['findings'])} finding(s):")
        for f in result["findings"]:
            print(f"  - [{f['rule']}] {f['file']}:{f['line']}: {f['snippet']}")
    else:
        print("KEPT - no checkable ban is broken.")
    if result["allowed"]:
        print()
        print(f"{len(result['allowed'])} allowed by comment:")
        for a in result["allowed"]:
            print(f"  - [{a['rule']}] {a['file']}:{a['line']}: {a['reason']}")
    if result["needs_a_person"]:
        print()
        print("No rule can read these; each needs a person to look:")
        for item in result["needs_a_person"]:
            print(f"  - {item['ban']}")


def main(argv: Optional[List[str]] = None) -> int:
    # The console script calls main() with nothing; name the command the way
    # it was invoked, so an installed run never prints the source filename.
    argv = list(sys.argv) if argv is None else list(argv)
    prog = os.path.basename(argv[0]) or "never-list"
    parser = argparse.ArgumentParser(
        prog=prog, description="Check UI code against the Never list in a design rulebook.")
    parser.add_argument("rulebook", help="the rulebook markdown file")
    parser.add_argument("targets", nargs="+", help="UI files or directories to check")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--version", action="version", version=f"{prog} {__version__}")
    args = parser.parse_args(argv[1:])
    try:
        result = check(args.rulebook, args.targets)
    except UsageError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result, args.targets)
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
