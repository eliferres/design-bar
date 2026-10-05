# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-10-04

### Added
- Install with `pipx install git+https://github.com/eliferres/design-bar` and run `dna-lint`, `slop-scan`, `shot-guard` and `never-list` as commands from any directory, each answering `--version`.
- A receipt beside the demo screenshot records the exact shot file and the test count printed on the page it was taken from, and a test in the suite fails when the picture, the page's number and the real size of the suite stop agreeing. The page and its screenshot carry the real size of the suite.

- `never-list` checks code against the "Never" section of a rulebook. Bans it can read (gradients, large card corners, blur orbs, quoted words in copy, an italic wordmark, a dark data grid) become checks; the rest are listed for a person. A `never-allow: <rule> <reason>` comment keeps one hit on purpose. The template and the example rulebook gain a "Never" section.

### Changed
- README headings now say what they hold: "Quick start" reads "Install" and moves above the demo screenshot, so the install command is on the first screen, "The system, in four parts" reads "What's inside", and "The walkthrough" reads "A full pass on the demo pages". The text under them is unchanged.

### Fixed
- The demo transcript now carries the full output and real exit code of every walkthrough command, recorded from a real run and held there by a test that replays them; the terminal picture shows the first of those commands complete.
- The demo page's test-count claim had drifted from the real size of the suite, and nothing caught it when the suite changed. The page and its re-captured screenshot now carry the real number.
- The demo picture no longer cuts its long lines off at the right edge: rows wider than the box ran past it mid-word with no ellipsis. Only the drawing changed; the recorded session is untouched, and the demo page's screenshot was re-captured so page and picture agree.
- `never-list` no longer reads a trailing `//` comment as copy, and a comment opener inside a string (`content: "/*"`, `"https://x"`) no longer hides the code after it.
- `never-list` reads page text only between real tags, so a comparison in script (`if (count > 0) unlock(); if (y < 3) go();`) is not copy.
- `never-list` lets Tailwind's `backdrop-blur-2xl` pass as frosted glass, as the README says; `blur-2xl` and a variant such as `md:blur-2xl` are still checked.
- `never-list` catches `rounded-4xl` and up as a large corner, matching the README's "rounded-2xl and up".
- The `never-list` docstring said an allow comment on the line above a hit lets it through; it covers its own line only, as the README says.

## [1.1.0](https://github.com/eliferres/design-bar/releases/tag/v1.1.0) - 2026-09-03

### Changed
- Added stdlib-only, Python 3.9-compatible type hints to every function in dna_lint.py, shot_guard.py, and slop_scan.py, with no behavior change.

### Added
- Added one in-memory PNG test per filter type (0 through 4), plus a truncated-file case, for shot_guard's PNG decoder.
- Added macos-latest to the CI matrix alongside ubuntu-latest.

## [1.0.0](https://github.com/eliferres/design-bar/releases/tag/v1.0.0) - 2026-08-31

First public release.
