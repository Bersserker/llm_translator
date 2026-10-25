import re
from pathlib import Path

from markdown_it import MarkdownIt


class TextDocument:
    def __init__(self, path: Path):
        # newline='' preserves CRLF and a possible UTF-8 BOM.
        with path.open(encoding="utf-8", newline="") as stream:
            self.text = stream.read()
        self.bom = self.text.startswith("\ufeff")
        if self.bom:
            self.text = self.text[1:]

    def transform(self, translate):
        self.text = "".join(translate(line) for line in self.text.splitlines(keepends=True))

    def save(self, path: Path):
        with path.open("w", encoding="utf-8", newline="") as stream:
            stream.write(("\ufeff" if self.bom else "") + self.text)


# Protect inline code, link targets (including balanced parentheses), reference
# labels, HTML, escapes, entities, URLs, and Markdown punctuation in source form.
INLINE_PROTECTED = re.compile(
    r"(?P<ticks>`+)[\s\S]*?(?P=ticks)"
    r"|\]\((?:[^()\r\n]|\([^()\r\n]*\))*\)"
    r"|\]\[[^\]\r\n]*\]"
    r"|<[^>\r\n]*>"
    r"|\\[^\r\n]"
    r"|&(?:#\d+|#x[\da-fA-F]+|\w+);"
    r"|https?://[^\s<>]+"
    r"|\[[ xX]\](?=\s)"
    r"|[*_~\[\]`|#]+"
)
PREFIX = re.compile(r"^[ \t]*(?:(?:>[ \t]*)+)?(?:(?:#{1,6}|[-+*]|\d+[.)])[ \t]+)?")


class MarkdownDocument(TextDocument):
    def transform(self, translate):
        lines = self.text.splitlines(keepends=True)
        environment = {}
        tokens = MarkdownIt("commonmark", {"html": True}).enable("table").parse(self.text, environment)
        protected = set()
        for token in tokens:
            if token.type in {"fence", "code_block", "html_block", "hr"} and token.map:
                protected.update(range(*token.map))
        for reference in environment.get("references", {}).values():
            protected.update(range(*reference["map"]))
        if lines and lines[0].strip() == "---":
            for index in range(1, len(lines)):
                if lines[index].strip() in {"---", "..."}:
                    protected.update(range(index + 1))
                    break
        # Setext heading markers and table separator lines carry no prose.
        for index, line in enumerate(lines):
            if index in protected or re.fullmatch(r"[ \t|:=\-]+(?:\r?\n)?", line):
                continue
            prefix = PREFIX.match(line).end()
            body = line[prefix:]
            # Shortcut/collapsed reference labels also serve as lookup keys.
            reference_labels = environment.get("references", {})
            shortcuts = []
            for match in re.finditer(r"\[([^\]\r\n]+)\](?:\[\])?(?![\[(])", body):
                key = " ".join(match[1].split()).upper()
                if key in reference_labels:
                    shortcuts.append((match.start(), match.end()))
            pieces = [line[:prefix]]
            cursor = 0
            spans = sorted(shortcuts + [(match.start(), match.end()) for match in INLINE_PROTECTED.finditer(body)])
            merged = []
            for start, end in spans:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                else:
                    merged.append((start, end))
            for start, end in merged:
                pieces.extend((translate(body[cursor:start]), body[start:end]))
                cursor = end
            pieces.append(translate(body[cursor:]))
            lines[index] = "".join(pieces)
        self.text = "".join(lines)
