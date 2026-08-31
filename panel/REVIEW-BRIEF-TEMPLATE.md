# Review brief — TEMPLATE

The third leg of the system: a reviewer who did not build the page
judges the rendered surface. Fill the brackets, hand this to a fresh
agent (or a fresh human), and give them the screenshots and this brief -
never the builder's chat, notes, or reasoning. Fresh eyes are the whole
point; contaminated eyes agree with the builder.

---

ROUND: [N] of 3
DIMENSIONS THIS ROUND: [e.g. layout, type hierarchy, copy, accessibility]

THE ASK (what the surface is for, in the owner's words):
[one paragraph - the audience, the single job of the page]

RULEBOOK: [path to the design DNA file the build was governed by]

RENDERS (all four, captured with tools/capture.sh):
- [dir]/shot-320.png
- [dir]/shot-375.png
- [dir]/shot-768.png
- [dir]/shot-1280.png

MACHINE RECEIPTS (data, not conclusions - verify anything you doubt):
- checker: [PASS/FAIL, tool, config, file sha]
- slop scan: [PASS/FAIL, tells config, file sha]

CLAIMS TO VERIFY (round 2+: what the builder says was fixed; check each
adversarially on the renders):
1. [claim]
2. [claim]

VERDICT FORMAT (required):
- SHIP or DO NOT SHIP, score X/10
- Blockers: each with the exact location (width, region, line)
- Nice-to-haves: clearly separated from blockers

---

## The round cap

Three rounds. Round 1 finds, round 2 confirms fixes, round 3 is the
last full pass. If the surface still cannot ship after round 3, the loop
stops and a human decides: ship with named defects, grant a dated round
4 in writing, or kill it. Endless polish is how deadlines die; the cap
is what makes the panel a tool instead of a treadmill.

## Rules that make the review worth having

- The reviewer never reviews their own build, and never sees the
  builder's reasoning - only the ask, the rulebook, and the renders.
- Every finding names its evidence: width, region, the exact text or
  measurement. "Feels off" is not a finding.
- Machine receipts are inputs, not verdicts. The reviewer re-derives
  anything load-bearing.
- Blockers and nice-to-haves never mix. A blocker blocks; everything
  else is logged and batched.
- The score is measured craft only. Whether the thing is desirable is
  the owner's call, not the reviewer's.
