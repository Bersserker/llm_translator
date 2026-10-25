from pathlib import Path

from tech_translator.parsers.docx import DocxDocument
from tech_translator.parsers.text import MarkdownDocument, TextDocument


def load_document(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return DocxDocument(path)
    if suffix in {".md", ".markdown"}:
        return MarkdownDocument(path)
    if suffix == ".txt":
        return TextDocument(path)
    raise ValueError("Supported document formats: .txt, .md, .markdown, .docx")
