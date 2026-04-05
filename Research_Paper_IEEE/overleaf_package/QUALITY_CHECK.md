# Quality Check (Figures + Tables + Manuscript)

Date: 2026-04-05
Scope: Overleaf package assets and paper consistency

## 1) Figure quality check
Measured from the packaged PNGs:

- `fig_architecture.png`: 1825x814 px, ~220 DPI
- `fig_case_layouts.png`: 2598x891 px, ~220 DPI
- `fig_density.png`: 1120x1007 px, ~220 DPI
- `fig_floorplan.png`: 937x988 px, ~220 DPI
- `fig_pipeline.png`: 1974x506 px, ~220 DPI
- `fig_simulation.png`: 2579x891 px, ~220 DPI

Assessment:
- All figures are usable for Overleaf compilation.
- Effective print resolution is acceptable for two-column IEEE usage.
- Main risk is label readability in short-height images (`fig_pipeline.png`, `fig_architecture.png`) when scaled to single-column width.

Recommended action before submission:
- If any text in those figures looks small in the PDF, regenerate with larger font labels.

## 2) Table/data consistency check
Checked values in `main.tex` against `paper_case_studies.csv/json`:

- Table metrics rows (A/B/C scenarios) match.
- Relative deltas (+69.1%, -1.5%, +22.5%, +49.9%) match.
- Exit distribution + imbalance values (0.282, 0.227, 0.306, 0.172) match.

Assessment:
- No table-data mismatches found.

## 3) Manuscript polish applied
Changes made in `main.tex`:

- Added configurable metadata macros for author block:
  - `\PaperAuthorName`
  - `\PaperAuthorAffiliation`
  - `\PaperAuthorCityCountry`
  - `\PaperAuthorEmail`
- Replaced hard-coded placeholder author lines with the macros.
- Tightened abstract wording for submission readability while preserving reported results and claims.

## Final remaining manual step
- Replace author metadata macro values with the real camera-ready details.
