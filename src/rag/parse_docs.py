import os
import json
import fitz
from docx import Document
from pptx import Presentation
import openpyxl

SRC_DIR = "knowledge/4lapy_docs"
OUT_FILE = "src/rag/docs.json"


def extract_pdf(path):
    txt = ""
    doc = fitz.open(path)
    for page in doc:
        txt += page.get_text()
    return txt


def extract_docx(path):
    d = Document(path)
    return "\n".join(p.text for p in d.paragraphs)


def extract_pptx(path):
    prs = Presentation(path)
    txt = ""
    for s in prs.slides:
        for sh in s.shapes:
            if hasattr(sh, "text"):
                txt += sh.text + "\n"
    return txt


def extract_xlsx(path):
    wb = openpyxl.load_workbook(path)
    txt = ""
    for sh in wb:
        for row in sh.iter_rows():
            for cell in row:
                if cell.value:
                    txt += str(cell.value) + " "
            txt += "\n"
    return txt


HANDLERS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".xlsx": extract_xlsx,
}


def main():

    docs = []

    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in HANDLERS:
                continue

            path = os.path.join(root, f)

            try:
                text = HANDLERS[ext](path).strip()

                if len(text) < 300:
                    continue

                docs.append({
                    "source": path.replace("\\", "/"),
                    "text": text
                })

                print(f"OK: {f}")

            except Exception as e:
                print(f"SKIP: {f} -> {e}")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print(f"\n✅ SAVED {len(docs)} documents into {OUT_FILE}")


if __name__ == "__main__":
    main()
