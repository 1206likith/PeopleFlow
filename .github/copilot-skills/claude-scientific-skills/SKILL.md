---
name: claude-scientific-skills
version: 1.0.0
description: Access 134+ scientific and research skills for Claude, covering bioinformatics, drug discovery, cheminformatics, clinical research, machine learning, data visualization, and 100+ scientific databases with unified API access.
author: K-Dense Inc.
license: MIT
keywords:
  - scientific computing
  - bioinformatics
  - drug discovery
  - machine learning
  - data analysis
  - research
compatibility:
  - Claude Code
  - Cursor
  - Codex
  - Gemini CLI
allowed-tools:
  - python
  - shell
  - file-system
---

# Claude Scientific Skills

**134 ready-to-use scientific and research skills** for Claude, enabling seamless access to:
- **100+ scientific databases** (PubChem, ChEMBL, UniProt, KEGG, Reactome, ClinicalTrials.gov, FDA, and more)
- **70+ optimized Python packages** (RDKit, Scanpy, PyTorch Lightning, scikit-learn, BioPython, and more)
- **8+ scientific integration platforms** (Benchling, DNAnexus, LatchBio, OMERO, Protocols.io)

## Use When

The user wants to:
- Query scientific databases for drug discovery, genomics, or proteomics data
- Analyze bioinformatics data sets (RNA-seq, single-cell, variants, etc.)
- Run machine learning workflows on scientific data
- Perform multi-omics analysis or protein engineering
- Design laboratory experiments or automation workflows
- Create publication-quality scientific figures and reports

## Skills by Domain

### 🧬 Bioinformatics & Genomics (21+ skills)
- BioPython: DNA/RNA/protein sequence analysis
- Scanpy: Single-cell RNA-seq with cell-type identification
- Arboreto: Gene regulatory network inference
- Phylogenetics: MAFFT, IQ-TREE, FastTree for evolutionary analysis
- gget: 20+ genomics databases unified
- TileDB-VCF: Variant database management

### 🧪 Drug Discovery & Cheminformatics (10+ skills)
- RDKit: Molecular structure analysis and manipulation
- DiffDock: Molecular docking and scoring
- DeepChem: ADMET and Tox prediction
- MedChem: Drug-likeness and Lipinski evaluation

### 🏥 Clinical & Precision Medicine (8+ skills)
- Clinical Trials search integration
- Variant interpretation (ClinVar, COSMIC, ClinPGx)
- Disease databases and medical ontologies

### 🤖 Machine Learning (16+ skills)
- PyTorch Lightning: Deep learning workflows
- scikit-learn: Classical ML with auto-evaluation
- Transformers: Large language models for biotext
- TimesFM: Time-series forecasting (Google's foundation model)

### 📊 Data Analysis & Visualization (16+ skills)
- Matplotlib/Seaborn: Publication-quality figures
- GeoPandas: Geospatial and satellite imagery
- NetworkX: Network biology and visualization
- Document Skills: PDF/DOCX/XLSX/PPTX processing

### 📚 Scientific Communication (20+ skills)
- Literature review across 10+ academic databases
- Paper search with structured extraction (methods, sample sizes, quality scores)
- Citation management and zotero integration
- Scientific writing and peer review

## Core Database Access

**Database Lookup skill** provides unified REST API access to 78+ public databases:

| Category | Databases |
|----------|-----------|
| Chemistry | PubChem, ChEMBL, PDB, AlphaFold |
| Genomics | NCBI Gene, Ensembl, gget, UniProt |
| Pathways | KEGG, Reactome, STRING |
| Clinical | ClinicalTrials.gov, ClinVar, COSMIC, FDA |
| Patents | USPTO, PubChem Source |
| Economics | FRED, SEC EDGAR, Treasury Data |

Plus specialized skills for DepMap, Imaging Data Commons, PrimeKG, and more.

## Workflow Examples

### 🧬 Drug Discovery Pipeline
```
Query ChEMBL for EGFR inhibitors (IC50 < 50nM)
→ Analyze SAR with RDKit  
→ Generate analogs with datamol
→ Virtual screen with DiffDock
→ Check COSMIC for resistance mutations
→ Create publication visualizations
```

### 🔬 Single-Cell RNA-seq Analysis
```
Load 10X with Scanpy
→ Quality control & doublet removal
→ Integrate with Cellxgene Census
→ Identify cell types with NCBI Gene markers
→ Differential expression with PyDESeq2
→ Define therapeutic targets
```

### 🏥 Clinical Variant Interpretation
```
Parse VCF with pysam
→ Annotate with Ensembl VEP
→ Query ClinVar for pathogenicity
→ Check pharmacogenomics (ClinPGx)
→ Find matching clinical trials
```

## Installation

```bash
# Via npx skills (recommended)
npx skills add K-Dense-AI/claude-scientific-skills

# Or in Claude Code
/plugin marketplace add K-Dense-AI/claude-scientific-skills
/plugin install kd-scientific@K-Dense-AI/claude-scientific-skills
```

## Key Features

- **✅ 134 skills** covering all major scientific domains
- **✅ 100+ databases** unified with single interface
- **✅ Production-tested** on real research projects for 6+ months
- **✅ Maintained actively** by K-Dense team
- **✅ Community-driven** with external contributions
- **✅ Token-efficient** prompts and structured skills

## Security

All skills security-scanned with Cisco AI Defense Skill Scanner. Review each SKILL.md before installing. Read-only access to public databases—no modifications sent.

## Getting Started Prompt

```text
I need to analyze [genomic/chemical/clinical] data. 

Use available skills you have access to whenever possible.
[Describe your task in detail with data sources]

Generate working code with results, visualizations, and key findings.
```

## Related Skills

- `deep-research-enterprise-skill` - Multi-phase scientific research pipelines
- `notebooklm-skill` - Document-grounded research and source management

## Resources

- [Full documentation](https://github.com/K-Dense-AI/claude-scientific-skills)
- [Quick examples](https://github.com/K-Dense-AI/claude-scientific-skills/tree/main/docs/examples.md)
- [Troubleshooting](https://github.com/K-Dense-AI/claude-scientific-skills/issues)
