---
name: xlsx
description: Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file; create a new spreadsheet from scratch; or convert between tabular file formats. Also trigger for cleaning or restructuring messy tabular data into proper spreadsheets. The deliverable must be a spreadsheet file.
---

# XLSX Creation, Editing, and Analysis

## Overview

Create, read, edit, or analyze .xlsx, .xlsm, .csv, and .tsv files. Use pandas for data analysis and openpyxl for formulas and formatting.

## Quick Start

### Read Excel File

```python
import pandas as pd

df = pd.read_excel('file.xlsx')
print(df.head())

# Read all sheets
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)
```

### Create New Spreadsheet

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
sheet = wb.active

sheet['A1'] = 'Hello'
sheet['B1'] = '=SUM(A2:A10)'
sheet['A1'].font = Font(bold=True)
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')

wb.save('output.xlsx')
```

### Edit Existing File

```python
from openpyxl import load_workbook

wb = load_workbook('existing.xlsx')
sheet = wb.active

sheet['A1'] = 'New Value'
sheet.insert_rows(2)
sheet.delete_cols(3)

wb.save('modified.xlsx')
```

## Reading and Analyzing Data

### Analyze with Pandas

```python
import pandas as pd

df = pd.read_excel('file.xlsx')
print(df.info())          # Column info
print(df.describe())      # Statistics
print(df['column'].sum()) # Aggregate
```

### Handle Specific Data Types

```python
df = pd.read_excel('file.xlsx', dtype={'id': str})
df = pd.read_excel('file.xlsx', usecols=['A', 'C', 'E'])
df = pd.read_excel('file.xlsx', parse_dates=['date_column'])
```

## CRITICAL: Use Formulas, Not Hardcoded Values

**ALWAYS use Excel formulas instead of calculating values in Python and hardcoding them.**

```python
# ✅ CORRECT - Use Excel formulas
sheet['B10'] = '=SUM(B2:B9)'
sheet['C5'] = '=(C4-C2)/C2'
sheet['D20'] = '=AVERAGE(D2:D19)'

# ❌ WRONG - Never hardcode calculated values
sheet['B10'] = 5000          # Hardcoded
sheet['C5'] = 0.15           # Hardcoded
```

This ensures spreadsheets are dynamic and updateable when source data changes.

## Financial Model Standards

### Color Coding (Industry Standard)

- **Blue text (RGB: 0,0,255)**: User inputs, changeable values
- **Black text (RGB: 0,0,0)**: Formulas and calculations
- **Green text (RGB: 0,128,0)**: Links from other worksheets
- **Red text (RGB: 255,0,0)**: External file links
- **Yellow background (RGB: 255,255,0)**: Key assumptions needing attention

### Number Formatting

- **Currency**: `$#,##0` format
- **Percentages**: `0.0%` format (default one decimal)
- **Zeros**: Display as "-" instead of 0
- **Years**: Format as text strings ("2024" not "2,024")
- **Negative numbers**: Use parentheses (123) not -123

### Formula Best Practices

```python
# Place assumptions in separate cells
sheet['B5'] = 0.05  # Growth rate assumption

# Use cell references, not hardcoded values
sheet['C2'] = '=B2*(1+$B$5)'  # Good: references assumption

# Document hardcoded values with source
# Format: "Source: [System], [Date], [Reference]"
```

## Recalculating Formulas

After creating or modifying Excel files with openpyxl, recalculate formulas:

```bash
python scripts/recalc.py output.xlsx
```

The script:
- Recalculates all formulas in all sheets
- Scans for Excel errors (#REF!, #DIV/0!, #VALUE!, #N/A)
- Returns detailed error locations

## Key Workflows

### Data Analysis Workflow
1. Load data with pandas
2. Analyze and transform
3. Export to Excel: `df.to_excel('output.xlsx', index=False)`

### Formula-Based Model Workflow
1. Create workbook with openpyxl
2. Add formulas (not hardcoded values)
3. Format cells (colors, number formats)
4. Run `recalc.py` to calculate formulas
5. Verify no errors (#REF!, #DIV/0!, etc.)

### Editing Existing File Workflow
1. Load: `load_workbook('file.xlsx')`
2. Modify cells and formulas
3. Preserve existing formatting
4. Save and recalculate

## Formula Verification Checklist

- [ ] **Test 2-3 samples**: Verify correct values before building full model
- [ ] **Column mapping**: Confirm Excel columns match data sources
- [ ] **Row offset**: Remember Excel is 1-indexed (row 5 in DataFrame = row 6 in Excel)
- [ ] **NaN handling**: Check for null values with `pd.notna()`
- [ ] **Division by zero**: Verify denominators before using `/` operator
- [ ] **Cell references**: Ensure all references point to intended cells
- [ ] **Cross-sheet links**: Use correct format (Sheet1!A1) for linking sheets

## Requirements for All Excel Files

### Professional Font
- Use consistent professional font (Arial, Times New Roman) for all deliverables

### Zero Formula Errors  
- Every Excel file delivered with ZERO formula errors (#REF!, #DIV/0!, #VALUE!, #N/A)

### Preserve Templates
- When updating existing files, match existing format and conventions
- Never impose standardized formatting on files with established patterns

## Common Pitfalls

- ❌ Calculating in Python and hardcoding results → ✅ Use Excel formulas
- ❌ Forgetting to recalculate formulas → ✅ Always run recalc.py
- ❌ Unverified formula errors shipped → ✅ Check script output for errors
- ❌ Inconsistent formatting across sheets → ✅ Use style standards
- ❌ Hardcoded values without documentation → ✅ Document all hardcodes with sources

## Tool Selection

| Task | Best Tool |
|------|-----------|
| Data analysis, transformation | pandas |
| Formulas, formatting, complex layout | openpyxl |
| Quick CSV/TSV conversion | pandas |
| Multi-sheet manipulation | openpyxl |
| Large file processing | pandas |

## When to Use This Skill

Use this skill when:
- User wants to create, edit, or analyze .xlsx/.xlsm/.csv/.tsv files
- Need to add formulas or complex formatting
- Extract, transform, or analyze tabular data
- Merge or split spreadsheets
- Create financial models or data dashboards
- The primary deliverable is a spreadsheet file
