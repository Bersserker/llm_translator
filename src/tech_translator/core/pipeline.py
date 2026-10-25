import logging
import re
from pathlib import Path

from tech_translator.config import Settings
from tech_translator.core.glossary import load_glossary
from tech_translator.core.segmenter import segment
from tech_translator.exporters.atomic import save_document
from tech_translator.llm.prompts import PROMPT
from tech_translator.llm.translator import LangChainTranslator
from tech_translator.parsers import load_document


def translate_document(source: Path, output: Path, settings: Settings, *, force=False, translator=None):
    if source.resolve() == output.resolve():
        raise ValueError("Input and output must be different files")
    if output.exists() and not force:
        raise FileExistsError("Output already exists; use --force to replace it")
    extensions = lambda path: ".md" if path.suffix.lower() == ".markdown" else path.suffix.lower()
    if extensions(source) != extensions(output):
        raise ValueError("Input and output must use the same document format")
    document = load_document(source)
    glossary = load_glossary(settings.translation.glossary_path)
    translator = translator if translator is not None else LangChainTranslator(settings)
    translation = settings.translation
    prompt_bytes = len(PROMPT.invoke(dict(source=translation.source_language, target=translation.target_language,
        glossary="\n".join(f"{k}: {v}" for k, v in glossary.items()), context="", text="")).to_string().encode("utf-8"))
    budget = translation.context_window - settings.llm.max_tokens - 256 - prompt_bytes
    if budget < 4:
        raise ValueError("Glossary and instructions exceed the configured context window")
    history = []

    def translate_text(text: str) -> str:
        pieces = []
        for chunk in segment(text, translation.chunk_size, max_bytes=budget):
            match = re.fullmatch(r"(\s*)(.*?)(\s*)", chunk, flags=re.DOTALL)
            leading, body, trailing = match.groups()
            if not body or not any(char.isalpha() for char in body):
                pieces.append(chunk)
                continue
            translated = translator.translate(body, context="\n".join(history), glossary=glossary).strip()
            if not translated:
                raise ValueError("Empty translation")
            pieces.append(leading + translated + trailing)
            history.append(f"{body}\n{translated}")
            # Bound memory independently of document size.
            history[:] = history[-2:]
        return "".join(pieces)

    document.transform(translate_text)
    save_document(document, output, force=force)
    logging.getLogger("tech_translator").debug("Document translation completed")
