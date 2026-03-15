"""
SAU Graduate Course Substitution Request — Batch Evaluator
===========================================================
Iterates over every PDF in a given folder, displays extracted fields for
each file, prompts for an APPROVE / DENY decision (Y / N), and writes all
decisions to EVAL.txt in the same folder.

Usage:
    python extract_course_substitution.py <folder_path>
    python extract_course_substitution.py          # uses current directory

Output:
    <folder>/EVAL.txt  — one line per PDF:
        APPROVED | filename.pdf | Name | Email | Required Course | Sub Course | Institution
        DENIED   | filename.pdf | ...

Requirements:
    pip install pdfplumber
"""

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber


# ── developer banner ─────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║     SAU Graduate Course Substitution — Batch Evaluator       ║
║                                                              ║
║  Developer : Dr. Rami                                        ║
║  Title     : Associate Prof. of Computer Science             ║
║  GitHub    : github.com/roninram                             ║
║  Version   : 1.0                                             ║
╚══════════════════════════════════════════════════════════════╝
"""


# ── text helpers ──────────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> str:
    """Return all text from every page of the PDF, joined by newlines."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)


def find_field(text: str, label: str, stop_labels=None) -> str:
    """
    Return the value that follows *label* in *text*.
    Searches for the label line, then collects the next non-empty line(s)
    until a stop-label is encountered.
    """
    lines = text.splitlines()
    label_lower = label.lower()
    label_idx = next(
        (i for i, ln in enumerate(lines) if label_lower in ln.lower()), None
    )
    if label_idx is None:
        return "NOT FOUND"

    value_lines = []
    stop_lower = [s.lower() for s in (stop_labels or [])]

    for line in lines[label_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if value_lines and any(s in stripped.lower() for s in stop_lower):
            break
        value_lines.append(stripped)
        if len(value_lines) == 1 and not stripped.endswith(","):
            break

    return " ".join(value_lines) if value_lines else "NOT FOUND"


# ── field extractor ───────────────────────────────────────────────────────────

def extract_substitution_info(pdf_path: Path) -> dict:
    """Parse one PDF and return a dict with the five required fields."""
    text = extract_text(pdf_path)

    # Name
    name = find_field(text, "Name", ["Student ID", "Email", "Substitution"])

    # Email — anchor to form body to skip forwarded-email header addresses
    form_start = text.find("I have read and understand")
    form_text = text[form_start:] if form_start != -1 else text
    email = find_field(form_text, "Email", ["Substitution", "Required Course", "Student ID"])
    if "@" not in email:
        m = re.search(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}", form_text)
        email = m.group(0) if m else "NOT FOUND"

    # Required course on SAU degree plan
    required_course = find_field(
        text,
        "Required Course listed on SAU degree plan",
        ["Course to be considered", "Institution", "Course description"],
    )

    # Course proposed for substitution
    substitution_course = find_field(
        text,
        "Course to be considered for substitution",
        ["Institution", "Course description", "Include web"],
    )

    # Institution
    institution = find_field(
        text,
        "Institution where course was taken",
        ["Course description", "Include web", "SAU Graduate"],
    )

    return {
        "Name": name,
        "Email": email,
        "Required Course (SAU degree plan)": required_course,
        "Course Proposed for Substitution": substitution_course,
        "Institution": institution,
    }


# ── display ───────────────────────────────────────────────────────────────────

def display_fields(pdf_name: str, fields: dict, index: int, total: int) -> None:
    """Pretty-print extracted fields for one PDF."""
    bar = "=" * 62
    print(f"\n{bar}")
    print(f"  File {index}/{total}: {pdf_name}")
    print(bar)
    print(f"  {'Name':<38} {fields['Name']}")
    print(f"  {'Email':<38} {fields['Email']}")
    print(f"  {'Required Course (SAU)':<38} {fields['Required Course (SAU degree plan)']}")
    print(f"  {'Substitution Course':<38} {fields['Course Proposed for Substitution']}")
    print(f"  {'Institution':<38} {fields['Institution']}")
    print(bar)


# ── decision prompt ───────────────────────────────────────────────────────────

def prompt_decision() -> tuple:
    """
    Ask the user Y/N.
    On denial, optionally prompt for a comment.
    Returns (decision, comment) where comment may be an empty string.
    """
    while True:
        answer = input("  Decision — Approve this substitution? [Y/N]: ").strip().upper()
        if answer in ("Y", "YES"):
            return "APPROVED", ""
        if answer in ("N", "NO"):
            comment = input("  Comment (press Enter to skip): ").strip()
            return "DENIED", comment
        print("  Please enter Y or N.")


# ── EVAL.txt writer ───────────────────────────────────────────────────────────

def write_eval(eval_path: Path, entries: list) -> None:
    """
    Write / overwrite EVAL.txt with all decisions collected so far.
    Format (pipe-delimited):
        DECISION | filename | Name | Email | Required Course | Sub Course | Institution | Comment
    """
    col = {
        "decision": 10, "file": 45, "name": 22,
        "email": 40, "req": 30, "sub": 45,
    }
    header = (
        f"# SAU Course Substitution Evaluation Log\n"
        f"# Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"# {'DECISION':{col['decision']}} | {'File':{col['file']}} | "
        f"{'Name':{col['name']}} | {'Email':{col['email']}} | "
        f"{'Required Course':{col['req']}} | {'Sub Course':{col['sub']}} | "
        f"Institution | Comment\n"
        f"# {'-' * 260}\n"
    )
    lines = [header]
    for e in entries:
        f = e["fields"]
        comment = e.get("comment", "")
        line = (
            f"  {e['decision']:{col['decision']}} | {e['filename']:{col['file']}} | "
            f"{f['Name']:{col['name']}} | {f['Email']:{col['email']}} | "
            f"{f['Required Course (SAU degree plan)']:{col['req']}} | "
            f"{f['Course Proposed for Substitution']:{col['sub']}} | "
            f"{f['Institution']} | {comment}\n"
        )
        lines.append(line)

    with open(eval_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)



def write_eval_csv(csv_path: Path, entries: list) -> None:
    """Write / overwrite EVAL.csv with all decisions collected so far."""
    fieldnames = [
        "Decision", "File", "Name", "Email",
        "Required Course (SAU degree plan)",
        "Course Proposed for Substitution",
        "Institution", "Comment",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for e in entries:
            f = e["fields"]
            writer.writerow({
                "Decision":                           e["decision"],
                "File":                               e["filename"],
                "Name":                               f["Name"],
                "Email":                              f["Email"],
                "Required Course (SAU degree plan)":  f["Required Course (SAU degree plan)"],
                "Course Proposed for Substitution":   f["Course Proposed for Substitution"],
                "Institution":                        f["Institution"],
                "Comment":                            e.get("comment", ""),
            })

# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(BANNER)
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    if not folder.is_dir():
        print(f"[ERROR] Not a directory: {folder}")
        sys.exit(1)

    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"[INFO] No PDF files found in: {folder.resolve()}")
        sys.exit(0)

    eval_path = folder / "EVAL.txt"
    csv_path  = folder / "EVAL.csv"
    entries = []
    total = len(pdf_files)

    print(f"\n  Found {total} PDF file(s) in: {folder.resolve()}")
    print(f"  Decisions will be saved to : {eval_path.resolve()}")
    print(f"                               {csv_path.resolve()}\n")

    for idx, pdf_path in enumerate(pdf_files, start=1):
        try:
            fields = extract_substitution_info(pdf_path)
        except Exception as exc:
            print(f"\n[SKIP] Could not process {pdf_path.name}: {exc}")
            continue

        display_fields(pdf_path.name, fields, idx, total)
        decision, comment = prompt_decision()

        entries.append({
            "filename": pdf_path.name,
            "decision": decision,
            "comment": comment,
            "fields": fields,
        })

        # Write after every decision so progress is never lost
        write_eval(eval_path, entries)
        write_eval_csv(csv_path, entries)

        icon = "✅" if decision == "APPROVED" else "❌"
        note = f" — {comment}" if comment else ""
        print(f"  {icon}  {decision}{note} — logged to EVAL.txt & EVAL.csv\n")

    # ── summary ───────────────────────────────────────────────────────────────
    approved = sum(1 for e in entries if e["decision"] == "APPROVED")
    denied = len(entries) - approved

    print("\n" + "=" * 62)
    print(f"  SESSION SUMMARY  —  {len(entries)} file(s) reviewed")
    print(f"  ✅  Approved : {approved}")
    print(f"  ❌  Denied   : {denied}")
    print(f"  📄  Log file : {eval_path.resolve()}")
    print(f"  📄  CSV file : {csv_path.resolve()}")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
