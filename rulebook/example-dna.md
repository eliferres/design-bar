---
type: design-dna
bar: marketing landing pages (the North Star example bar)
version: 1 (2026-08-30)
---
# Design DNA — the North Star example bar

Read this file in full before building any landing page it governs. The
values are illustrative: they demonstrate the anatomy with numbers that
hang together, and they match `config/example-bar.json` in the
[website-bar](https://github.com/eliferres/website-bar) checker, so the
same taste is written once and enforced twice — before the build here,
after the build there. Replace every value with habits you measured on
the reference you actually want to be graded against.

## 1. Reference

- Reference: your best-in-class example, e.g. a site at northstar.example
  (proof: REPLACE with why it earns the job — revenue, traffic, ratings,
  and the date you measured them. A reference without proof is a mood.)

## 2. Color tokens, by job

- Jobs: `ground` (page), `ink` (text), `muted` (secondary text),
  `accent` (the one action color). (ruling 2026-08-30: example values)
- Budget: 4 core colors plus tints; a page quantizing to more than 12 is
  over budget. (ruling 2026-08-30: matches the checker's max_colors)

## 3. Type scale

- Families: at most 2. (ruling 2026-08-30: matches max_font_families)
- Scale: 13px label (uppercase, tracked) · 16px body · 21px third-level
  heading · 34px section heading (26px on phones) · 68px display,
  stepping to 48px on tablets and 34px on phones; weights 400
  throughout - emphasis comes from size and family, not boldness.
  Adjacent roles stay at least 3px apart at rendered size, so no two
  are sub-perceptual twins.
  (ruling 2026-08-30: the North Star example page's rendered scale)
- Headline: at most 7 words for an h1, 10 for an h2, sentence case,
  banned openers include "Welcome to" and "Unlock".
  (ruling 2026-08-30: matches headline_economy)
- Body: floor 16px, line-height 1.3 to 1.75, measure 45 to 75
  characters, counted as rendered characters per line, not CSS ch
  units. The measure rule binds body prose; single-line labels,
  captions, and figures ride the label role instead.
  (ruling 2026-08-30: example values; character count and label
  exemption ruling 2026-08-31)
- Heading leading: 1.08 for the display size, 1.15 to 1.25 for every
  other heading; the body band above never applies to headings.
  (ruling 2026-08-31: added after review round 2 caught an inherited
  body leading on a section heading)

## 4. Spacing and shape

- Base grid 4px; section padding steps from a single scale.
  (ruling 2026-08-30: example values)
- Radii: at most 3 distinct non-pill values; reuse, never invent
  per-component. (ruling 2026-08-30: example values)

## 5. Component anatomy

- Primary action: one per view, repeated down the page rather than
  competing with siblings; minimum touch height 44px.
  (ruling 2026-08-30: example values)
- DEEPEN: nav, cards, form fields, footer — specify before building
  pages that carry them.

## 6. Motion

- Durations: 150 to 400ms, hard ceiling 700ms. The band binds every
  shipped asset, embedded SVG included.
  (ruling 2026-08-30: matches motion_durations; SVG clause 2026-08-31)
- Honor prefers-reduced-motion on every animated surface.
  (ruling 2026-08-30: matches require_reduced_motion)

## 7. Hygiene

- Every image carries real alt text; every page carries a viewport meta
  tag; every text pair clears WCAG AA contrast.
  (ruling 2026-08-30: first two match craft_basics; contrast rides the
  review panel because it needs rendering)

## 8. Decision log

- 2026-08-30 (author): example bar created to demonstrate the anatomy;
  every value marked as a ruling until someone measures a real
  reference and replaces them.
- 2026-08-31 (review round 2): heading-leading band added; measure
  defined in rendered characters with a label exemption; the motion
  band extended to every shipped asset, SVG included.
