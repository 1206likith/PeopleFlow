# Overleaf Setup for PeopleFlow Paper

Files in this folder are ready to upload to Overleaf as a single project root.

## Main file
- `main.tex`

## Required assets
- `references.bib`
- `fig_pipeline.png`
- `fig_floorplan.png`
- `fig_architecture.png`
- `fig_case_layouts.png`
- `fig_simulation.png`
- `fig_density.png`

## Compile settings
- Compiler: `pdfLaTeX`
- Bibliography: `BibTeX`
- Run order: `pdfLaTeX` -> `BibTeX` -> `pdfLaTeX` -> `pdfLaTeX`

## Before submission
- Replace the placeholder author affiliation in `main.tex` with the real institution and contact details.
- Review the title page and abstract for any wording changes you want before final submission.
- Keep all image files in the same root folder as `main.tex` unless you also update the figure paths in the LaTeX source.

## Not needed for compilation
- `paper_case_studies.json`
- `paper_case_studies.csv`
- `policy_comparison.csv`

Those files are source data, not Overleaf dependencies.
