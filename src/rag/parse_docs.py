import os
import json
import re

import pdfplumber
from docx import Document
from pptx import Presentation
import openpyxl


SRC_DIR = "knowledge/4lapy_docs"
OUT_FILE = "src/rag/raw_docs.json"


# =====================================
# CLEANING
# =====================================

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7Eа-яА-ЯёЁ]", " ", text)
    return text.strip()


# =====================================
# EXTRACTORS
# =====================================

def extract_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    return clean_text(text)


def extract_docx(path):
    doc = Document(path)
    return clean_text("\n".join(p.text for p in doc.paragraphs))


def extract_pptx(path):
    prs = Presentation(path)
    txt = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                txt += shape.text + "\n"
    return clean_text(txt)


def extract_xlsx(path):
    wb = openpyxl.load_workbook(path)
    txt = ""

    for sheet in wb:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value:
                    txt += str(cell.value) + " "
            txt += "\n"

    return clean_text(txt)


def extract_txt(path):
    with open(path, encoding="utf8", errors="ignore") as f:
        return clean_text(f.read())


HANDLERS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".xlsx": extract_xlsx,
    ".txt": extract_txt,
}

# =====================================
# MAIN PIPELINE
# =====================================

def main():
    docs = []

    for root, _, files in os.walk(SRC_DIR):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()

            if ext not in HANDLERS:
                continue

            path = os.path.join(root, filename)

            try:
                text = HANDLERS[ext](path)

                if len(text) < 300:
                    continue

                docs.append({
                    "source": path.replace("\\", "/"),
                    "text": text
                })

                print("OK:", path)

            except Exception as e:
                print("SKIP:", path, "->", e)

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved RAW docs: {len(docs)} → {OUT_FILE}")


if __name__ == "__main__":
    main()
