"""Dependency-free PDF reports for conversations and chart summaries."""
from __future__ import annotations

from datetime import datetime
from textwrap import wrap


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")


def _pdf(title: str, sections: list[tuple[str, list[str]]]) -> bytes:
    pages, lines = [], []
    def flush():
        nonlocal lines
        if lines:
            pages.append(lines); lines = []
    lines.extend([(title, 18), (f"Generated {datetime.now():%Y-%m-%d %H:%M}", 9), ("", 10)])
    for heading, paragraphs in sections:
        if len(lines) > 42: flush()
        lines.append((heading, 14))
        for paragraph in paragraphs:
            for line in wrap(str(paragraph), 92) or [""]:
                if len(lines) >= 48: flush()
                lines.append((line, 10))
        lines.append(("", 8))
    flush()
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for index, page in enumerate(pages):
        content_id = 4 + index * 2
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {3 + len(pages)*2} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        commands = ["BT", "/F1 10 Tf", "50 750 Td"]
        previous = 10
        for text, size in page:
            commands.extend([f"/F1 {size} Tf", f"0 -{max(13, previous + 3)} Td", f"({_escape(text)}) Tj"])
            previous = size
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)


def project_report(chat: dict) -> bytes:
    questions = [m["content"] for m in chat["messages"] if m["role"] == "user"]
    answers = [m["content"] for m in chat["messages"] if m["role"] == "assistant"]
    sections = [
        ("Project Overview", ["BSDI Project AI Agent analyses the Government of Balochistan development portfolio with data-grounded AI assistance."]),
        ("Objective", ["Support transparent project analysis, prioritisation, delivery review, and equitable funding decisions."]),
        ("Features & Technologies", ["Persistent AI chat, multi-agent review, interactive Plotly charts, pandas data analysis, Streamlit, Hugging Face/xAI integration, and downloadable reports."]),
        ("Questions Asked", questions or ["No questions in this conversation."]),
        ("AI Responses and Key Findings", answers or ["No responses in this conversation."]),
        ("Generated Charts", [f"{c['title']} — prompted by: {c['question']}" for c in chat.get("charts", [])] or ["No charts generated."]),
        ("Conclusion", ["This report reflects the live conversation and generated analytical outputs."]),
    ]
    return _pdf("BSDI Project AI Agent — Project Report", sections)


def charts_report(chat: dict) -> bytes:
    sections = []
    for chart in chat.get("charts", []):
        values = [float(row.get(chart["y"], 0) or 0) for row in chart["data"]]
        peak = max(values, default=1) or 1
        rows = [
            f"{row.get(chart['x'])}: {row.get(chart['y'])}  "
            f"{'#' * max(1, round(float(row.get(chart['y'], 0) or 0) / peak * 28))}"
            for row in chart["data"]
        ]
        sections.append((chart["title"], [f"Question: {chart['question']}", f"Axes: {chart['x_label']} / {chart['y_label']}", *rows]))
    return _pdf("BSDI Project AI Agent — Charts Report", sections or [("Charts", ["No charts generated in this conversation."])])
