from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


class DocxDocument:
    def __init__(self, path: Path):
        self.document = Document(path)

    def transform(self, translate):
        # Editing text nodes preserves runs, tables, links, fields, images,
        # paragraph styles and section structure. Header/footer parts are shared
        # between sections, so visit each package part exactly once.
        for part in self.document.part.package.parts:
            element = getattr(part, "element", None)
            if element is None:
                continue
            for node in element.iter(qn("w:t")):
                # Code-styled paragraphs/runs remain literal.
                styles = []
                for ancestor in node.iterancestors():
                    if ancestor.tag == qn("w:r"):
                        style = ancestor.find("./" + qn("w:rPr") + "/" + qn("w:rStyle"))
                    elif ancestor.tag == qn("w:p"):
                        style = ancestor.find("./" + qn("w:pPr") + "/" + qn("w:pStyle"))
                    else:
                        continue
                    if style is not None:
                        styles.append(style.get(qn("w:val"), ""))
                if any("code" in style.lower() for style in styles):
                    continue
                node.text = translate(node.text or "")
                node.set(qn("xml:space"), "preserve")

    def save(self, path: Path):
        self.document.save(path)
