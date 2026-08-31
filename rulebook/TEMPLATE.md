---
type: design-dna
bar: NAME THE SURFACE (which kind of page this governs)
version: 0 (unstarted)
---
# Design DNA — TEMPLATE

Read this file in full before building any surface it governs. That
sentence is the whole trick: the rulebook is a build-first document, not
a review checklist. Checkers and reviewers catch drift after the fact;
this file exists so the build starts right.

Three provenance tags, and every value carries one:

- `(measured YYYY-MM-DD source)` — you measured it on the reference.
- `(ruling YYYY-MM-DD who)` — a human decided it; the decision log has the why.
- `DEEPEN` — an honest hole you have named but not yet filled.

An untagged number is a taste guess in disguise. The linter
(`tools/dna_lint.py`) refuses a rulebook whose sections carry no tags.

## 1. Reference

Name the one best-in-class site or app this bar copies, with proof it
earns the job (traffic, revenue, ratings, a date — not vibes). One
reference, studied deeply, beats five referenced vaguely.

- Reference: example.com (proof: REPLACE — why this one, measured when)

## 2. Color tokens, by job

Name tokens by the job they do, never by their hue. Set a budget.

- Jobs: `ground`, `ink`, `muted`, `accent`. Budget: N core + tints. (measured ...)

## 3. Type scale

- Families: at most N. (measured ...)
- Headline: size / weight / max words / max measure. (measured ...)
- Body: size floor / line-height band / measure. (measured ...)
- Mobile floors. (measured ...)

## 4. Spacing and shape

- Base grid, section padding, card gaps. (measured ...)
- Radii: at most N distinct values; reuse, never invent per-component.
  (measured ...)

## 5. Component anatomy

The depth that separates a rulebook from a mood board: exact anatomy for
each repeated component. Primary action, card, nav, form field, footer.

- Primary action: height, radius, one per view or repeated N times. (measured ...)
- DEEPEN: components you have not yet specified — name them here.

## 6. Motion

- Durations: at most N distinct, ceiling in ms. (measured ...)
- Easings: at most N. Honor prefers-reduced-motion. (ruling ...)

## 7. Hygiene

- Contrast floor, load budget, alt text, viewport. (ruling ...)

## 8. Decision log

Append-only. Every taste ruling lands here with a date and a why, and is
never re-litigated. The log is what makes the rulebook a memory instead
of an opinion.

- 2026-01-01 (template): replace this line with your first real ruling,
  dated, with the why. The template ships linting complete so you start
  from green, not from a scold.
