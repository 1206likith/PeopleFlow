# PeopleFlow Paper: Final Overleaf + Submission Checklist

Date: 2026-04-05

## A) Overleaf project setup

1. Create a blank Overleaf project.
2. Upload all files from this folder into the project root:
   - main.tex
   - references.bib
   - fig_pipeline.png
   - fig_floorplan.png
   - fig_architecture.png
   - fig_case_layouts.png
   - fig_simulation.png
   - fig_density.png
3. Set `main.tex` as the Main file.
4. Compiler: pdfLaTeX.
5. Recompile twice.

Expected outcome:
- No missing-file errors.
- IEEE-style numbered citations render.
- References list appears.

## B) Title block check

Open `main.tex` and verify metadata macros:
- \PaperAuthorName
- \PaperAuthorAffiliation
- \PaperAuthorCityCountry
- \PaperAuthorEmail

Current values are already filled. Confirm exact spelling and spacing before submission.

## C) Technical compile checks

1. No undefined citations in Overleaf logs.
2. No missing figure warnings.
3. No overfull hbox warnings that break readability in two-column format.
4. All tables and figure captions stay within page margins.

## D) Content integrity checks

1. Numbers in tables match case-study data.
2. Relative deltas in the discussion match table values.
3. Claims stay in decision-support language (no absolute safety claims).
4. Limitations section is present and explicit.

## E) Figure quality checks

Measured figure quality:
- fig_architecture.png: 1825x814, ~220 DPI
- fig_case_layouts.png: 2598x891, ~220 DPI
- fig_density.png: 1120x1007, ~220 DPI
- fig_floorplan.png: 937x988, ~220 DPI
- fig_pipeline.png: 1974x506, ~220 DPI
- fig_simulation.png: 2579x891, ~220 DPI

Action:
- In final PDF, zoom to 150-200% and verify small labels are readable, especially in fig_pipeline and fig_architecture.

## F) IEEE readiness checks

1. Title in Title Case.
2. Abstract concise and evidence-grounded.
3. Keywords present.
4. Equations numbered and referenced.
5. All figures/tables referenced in text.
6. References formatted with IEEEtran style.
7. Final page balancing enabled (already present via \balance).

## G) Submission export

1. Download source ZIP from Overleaf.
2. Download final PDF from Overleaf.
3. Keep both under a dated folder for record:
   - peopleflow_paper_source_YYYYMMDD.zip
   - peopleflow_paper_pdf_YYYYMMDD.pdf

## H) Nice-to-have before final upload

1. Run one grammar pass only (avoid changing technical numbers).
2. Ask one peer to scan figures + captions only.
3. Verify corresponding author email once more.
