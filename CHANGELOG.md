# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Install with `pipx install git+https://github.com/eliferres/design-bar` and run `dna-lint`, `slop-scan` and `shot-guard` as commands from any directory, each answering `--version`.

### Fixed
- The demo transcript now carries the full output and real exit code of every walkthrough command, recorded from a real run and held there by a test that replays them; the terminal picture shows the first of those commands complete.

## [1.1.0](https://github.com/eliferres/design-bar/releases/tag/v1.1.0) - 2026-09-03

### Changed
- Added stdlib-only, Python 3.9-compatible type hints to every function in dna_lint.py, shot_guard.py, and slop_scan.py, with no behavior change.

### Added
- Added one in-memory PNG test per filter type (0 through 4), plus a truncated-file case, for shot_guard's PNG decoder.
- Added macos-latest to the CI matrix alongside ubuntu-latest.

## [1.0.0](https://github.com/eliferres/design-bar/releases/tag/v1.0.0) - 2026-08-31

First public release.
