# Layout-Only Stabilization Changelog (2026-04-05)

Scope: `research_paper.tex` layout and float behavior only.

## What changed

1. Preamble float spacing was mildly rebalanced:
- `\textfloatsep`: `11pt` -> `12pt`
- `\floatsep`: `10pt` -> `11pt`
- `\intextsep`: `10pt` -> `11pt`
- `\dbltextfloatsep`: `11pt` -> `12pt`

2. High-risk results/validation floats were given safer placement windows:
- Selected environments changed from `[t]` to `[!tb]` around method-comparison, blocked-exit, supplementary cohort, sensitivity, occupancy, and quantitative-validation tables.
- The sensitivity heatmap figure was changed to `[!tb]`.

3. Table geometry was stabilized for dense headers/cells without changing data:
- `tabcolsep`, per-column widths, and alignment specs updated in:
  - Ablation table
  - Method summary table
  - Tool-comparison table (early related-work section), including a final micro-pass to rebalance column widths and use compact table font for row-fit stability
  - Baseline-assumption comparison table
  - Desired-speed sensitivity table
  - Occupancy-scaling table
  - Quantitative-agreement table

4. Float alignment for the isolated variability plot was corrected:
- Converted the run-to-run variability figure to a full-width float so the page renders centered rather than left-weighted.
- Header wrapping (`\shortstack`) and selective `\allowbreak` were added only to prevent header/token overflow.

5. End-page control was adjusted:
- Removed final `\clearpage` and `\balance` calls before bibliography to avoid output-stage overfull-vbox behavior from forced balancing.

## Verification performed

1. Full compile cycle executed:
- `pdflatex -> bibtex -> pdflatex -> pdflatex`

2. Log checks:
- No `Overfull \vbox` warnings remain.
- No `Overfull \hbox` warnings remain.
- Former mid-paper and early-table overfull hotspots tied to targeted table headers/geometry were removed.

3. Visual QA:
- Re-rendered all pages to `page_renders/`.
- Focused checks on pages 8-10 and end pages found no overlaps, clipped captions, stray line fragments, or cross-column intrusions.

4. Content integrity:
- Baseline vs updated `.tex` diff confirms edits are structural/layout directives only (float specifiers, spacing, table geometry).
- No prose/metric value changes introduced.

5. Packaging sync:
- Rebuilt `Research_Paper_IEEE.zip` from corrected source/assets.
- SHA-256 verification confirms packaged `research_paper.pdf` is byte-identical to local `research_paper.pdf`.
