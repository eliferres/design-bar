# Contributing

Small, focused changes travel best here.

- New slop tells: open a tell proposal issue first (the template asks
  the three questions that decide it).
- Tool changes ship with a test in `tests/` that fails without them.
- Everything stays zero-dependency: stdlib Python and plain bash only.
- Run `python3 -m unittest discover -s tests` before opening a PR; CI
  runs the same suite plus the shipped rulebooks and the clean page.
