#!/usr/bin/env python3
"""Lint a design DNA rulebook before anyone builds against it.

A rulebook is the build-first half of the design bar system: the file a
builder must read before writing a line of UI. This linter checks the
file has the anatomy that makes that reading worth anything - the seven
sections, a named reference with proof, provenance on the values, and a
dated decision log. It does not judge taste; it judges whether taste was
written down properly.

Exit codes: 0 = rulebook complete, 1 = gaps found, 2 = usage or IO error.
"""

import re
import sys

REQUIRED_SECTIONS = [
    ("reference", r"reference"),
    ("color tokens", r"color"),
    ("type scale", r"type"),
    ("spacing and shape", r"spacing|shape"),
    ("component anatomy", r"component"),
    ("motion", r"motion"),
    ("hygiene", r"hygiene|accessibility|performance"),
    ("decision log", r"decision log"),
]

# Sections that must carry at least one provenance marker: a value is
# either measured from the reference, a recorded ruling, or an honest
# DEEPEN gap. An untagged section is taste guessing in disguise.
PROVENANCE_SECTIONS = [
    "color tokens",
    "type scale",
    "spacing and shape",
    "component anatomy",
    "motion",
    "hygiene",
]
PROVENANCE = re.compile(r"\bmeasured\b|\bruling\b|\bDEEPEN\b", re.IGNORECASE)

DATED_ENTRY = re.compile(r"^\s*[-*]\s*20\d\d-\d\d-\d\d\b")
URL = re.compile(
    r"https?://\S+|\b[a-z0-9-]+\.(?:com|org|net|dev|io|app|example)\b"
)


def read_rulebook(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}")
        sys.exit(2)


def split_sections(text):
    """Return {section title lower: body} for every markdown heading."""
    sections = {}
    title = "_preamble"
    body = []
    for line in text.splitlines():
        match = re.match(r"^#{1,3}\s+(.*)", line)
        if match:
            sections[title] = "\n".join(body)
            title = match.group(1).strip().lower()
            body = []
        else:
            body.append(line)
    sections[title] = "\n".join(body)
    return sections


def find_section(sections, pattern):
    regex = re.compile(pattern, re.IGNORECASE)
    for title, body in sections.items():
        if regex.search(title):
            return title, body
    return None, None


def check_front_matter(text, findings):
    if not text.startswith("---"):
        findings.append("no front-matter block (--- at line 1)")
        return
    head = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    if not re.search(r"^version:", head, re.MULTILINE):
        findings.append("front-matter has no version: line")


def check_sections(sections, findings):
    for name, pattern in REQUIRED_SECTIONS:
        title, _ = find_section(sections, pattern)
        if title is None:
            findings.append(f"missing section: {name}")


def check_reference(sections, findings):
    _, body = find_section(sections, r"reference")
    if body is None:
        return
    if not URL.search(body):
        findings.append(
            "reference section names no source (no URL or domain found)"
        )
    if not re.search(r"proof", body, re.IGNORECASE):
        findings.append(
            "reference section has no proof line (why this reference earns "
            "the job: traffic, revenue, ratings, a date)"
        )


def check_provenance(sections, findings, deepen_count):
    for name in PROVENANCE_SECTIONS:
        pattern = dict(REQUIRED_SECTIONS)[name]
        title, body = find_section(sections, pattern)
        if body is None:
            continue
        if not PROVENANCE.search(body):
            findings.append(
                f"section '{title}' has no provenance marker - tag values "
                "with (measured ...), (ruling ...), or an explicit DEEPEN gap"
            )
        deepen_count[0] += len(re.findall(r"\bDEEPEN\b", body))


def check_decision_log(sections, findings):
    title, body = find_section(sections, r"decision log")
    if body is None:
        return
    if not any(DATED_ENTRY.match(line) for line in body.splitlines()):
        findings.append(
            "decision log has no dated entry (every ruling lands here as "
            "'- YYYY-MM-DD (who): what was decided')"
        )


def main(argv):
    if len(argv) != 2:
        print("usage: dna_lint.py <rulebook.md>")
        return 2
    path = argv[1]
    text = read_rulebook(path)
    sections = split_sections(text)

    findings = []
    deepen_count = [0]
    check_front_matter(text, findings)
    check_sections(sections, findings)
    check_reference(sections, findings)
    check_provenance(sections, findings, deepen_count)
    check_decision_log(sections, findings)

    print("dna-lint report")
    print(f"rulebook: {path}")
    print()
    if findings:
        print(f"INCOMPLETE - {len(findings)} gap(s):")
        for finding in findings:
            print(f"  - {finding}")
        print()
        print("An incomplete rulebook is a taste guess waiting to happen.")
        print("Close the gaps before anyone builds against it.")
        return 1
    note = ""
    if deepen_count[0]:
        note = f" ({deepen_count[0]} DEEPEN gap(s) named - honest, allowed)"
    print(f"COMPLETE - all sections present, provenance tagged{note}.")
    print("Builders read this file in full before building.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
