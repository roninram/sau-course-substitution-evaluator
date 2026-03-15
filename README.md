# SAU Course Substitution Evaluator

Batch evaluator for SAU Graduate Course Substitution Request PDFs.

## What it does
- Iterates over all PDF files in a folder
- Extracts: Name, Email, Required Course, Substitution Course, Institution
- Prompts for an APPROVED / DENIED decision (Y/N)
- On denial, optionally accepts a comment
- Writes results to both `EVAL.txt` and `EVAL.csv` after every decision

## Usage
```bash
python ext_course_full_.py /path/to/pdf/folder
```

## Requirements
```bash
pip install pdfplumber
```
