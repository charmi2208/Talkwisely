"""
Render saved reports as PDF, Markdown or CSV downloads.

PDFs use fpdf2's built-in Helvetica, which only covers Latin-1, so common Unicode
punctuation from AI text is mapped to ASCII first and anything else is replaced.
"""

import csv
import io
from datetime import datetime
from typing import Any

from fpdf import FPDF

_ASCII = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    "…": "...", "•": "-", " ": " ", "→": "->", "≤": "<=", "≥": ">=",
})


def _latin1(text: str) -> str:
    return text.translate(_ASCII).encode("latin-1", "replace").decode("latin-1")


def report_pdf(title: str, markdown: str, generated_at: datetime | None = None) -> bytes:
    """A simple PDF from the report's Markdown (headings, bullets and paragraphs)."""
    pdf = FPDF(format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_title(_latin1(title))

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    stamp = (generated_at or datetime.utcnow()).strftime("%d %b %Y %H:%M UTC")
    pdf.cell(0, 6, _latin1(f"TalkWiseAI  |  Generated {stamp}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_text_color(20, 20, 20)

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            pdf.ln(2)
        elif line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 8, _latin1(line[2:]), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, _latin1(line[3:]), new_x="LMARGIN", new_y="NEXT")
        elif line.lstrip().startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 10)
            text = line.lstrip()[2:]
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(0, 5.5, _latin1(f"-  {text}"), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.5, _latin1(line.replace("**", "")), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _flatten(prefix: str, value: Any, rows: list[tuple[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), sub, rows)
    elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
        for i, sub in enumerate(value):
            _flatten(f"{prefix}[{i}]", sub, rows)
    elif isinstance(value, list):
        rows.append((prefix, "; ".join(str(v) for v in value)))
    else:
        rows.append((prefix, value))


def report_csv(title: str, metrics: dict[str, Any], sections: dict[str, list[str]]) -> str:
    """Metrics as metric/value rows, followed by the report's written sections."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Report", title])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    rows: list[tuple[str, Any]] = []
    _flatten("", metrics, rows)
    writer.writerows(rows)
    for heading, items in sections.items():
        if items:
            writer.writerow([])
            writer.writerow([heading])
            writer.writerows([[item] for item in items])
    return buffer.getvalue()
