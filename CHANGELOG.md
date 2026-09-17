# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Install with `pipx install git+https://github.com/eliferres/design-bar` and run `dna-lint`, `slop-scan` and `shot-guard` as commands from any directory, each answering `--version`.
- A receipt beside the demo screenshot records the exact shot file and the test count printed on the page it was taken from, and a test in the suite fails when the picture, the page's number and the real size of the suite stop agreeing. The page and its screenshot now read 29/29, the size of the suite with that test in it.

### Changed
- README headings now say what they hold: "Quick start" reads "Try it", "The system, in four parts" reads "What's inside", and "The walkthrough" reads "A full pass on the demo pages". The text under them is unchanged.

### Fixed
- The demo transcript now carries the full output and real exit code of every walkthrough command, recorded from a real run and held there by a test that replays them; the terminal picture shows the first of those commands complete.
- The demo page's test-count claim reads 27/27, the real size of the suite, and its screenshot was re-captured from the fixed page.
- The demo page's test-count claim follows the suite again: the two picture tests became one stricter walk, so the number reads 26/26 and the screenshot was re-captured from the changed page.
- The demo picture no longer cuts its long lines off at the right edge: rows wider than the box ran past it mid-word with no ellipsis. Only the drawing changed; the recorded session is untouched, and the demo page's screenshot was re-captured so page and picture agree.

## [1.1.0](https://github.com/eliferres/design-bar/releases/tag/v1.1.0) - 2026-09-03

### Changed
- Added stdlib-only, Python 3.9-compatible type hints to every function in dna_lint.py, shot_guard.py, and slop_scan.py, with no behavior change.

### Added
- Added one in-memory PNG test per filter type (0 through 4), plus a truncated-file case, for shot_guard's PNG decoder.
- Added macos-latest to the CI matrix alongside ubuntu-latest.

## [1.0.0](https://github.com/eliferres/design-bar/releases/tag/v1.0.0) - 2026-08-31

First public release.
