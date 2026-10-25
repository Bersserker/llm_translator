from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field, ValidationError, field_validator
from openai import BadRequestError

from tech_translator.config import Settings
from tech_translator.llm.client import create_client
from tech_translator.llm.prompts import PROMPT
from tech_translator.utils.errors import response_text


class TranslationResult(BaseModel):
    translation: str = Field(description="Translated text, without commentary")

    @field_validator("translation")
    @classmethod
    def nonempty(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("Empty translation")
        return text


class LangChainTranslator:
    def __init__(self, settings: Settings, *, llm=None):
        self.settings = settings
        self.llm = llm if llm is not None else create_client(settings)
        self.plain_chain = PROMPT | self.llm
        self.structured_chain = None
        if settings.llm.structured_output != "off":
            try:
                self.structured_chain = PROMPT | self.llm.with_structured_output(
                    TranslationResult, method="json_schema")
            except (NotImplementedError, ValueError):
                if settings.llm.structured_output == "on":
                    raise

    def translate(self, text: str, *, context: str = "", glossary: dict | None = None) -> str:
        if not text.strip():
            return text
        config = self.settings.translation
        values = dict(source=config.source_language, target=config.target_language,
                      glossary="\n".join(f"{k}: {v}" for k, v in (glossary or {}).items()),
                      context=context, text=text)
        # UTF-8 bytes give a conservative token estimate for local tokenizers.
        budget = config.context_window - self.settings.llm.max_tokens - 256
        while len(PROMPT.invoke(values).to_string().encode("utf-8")) > budget and values["context"]:
            values["context"] = values["context"][len(values["context"]) // 2 + 1:]
        if len(PROMPT.invoke(values).to_string().encode("utf-8")) > budget:
            raise ValueError("Segment and glossary exceed the configured context window")
        if self.structured_chain is not None:
            try:
                result = self.structured_chain.invoke(values)
                return TranslationResult.model_validate(result).translation
            except (BadRequestError, NotImplementedError, ValidationError, OutputParserException) as error:
                # Do not retry authentication, rate limits, or server outages as plain text.
                if isinstance(error, BadRequestError):
                    body = str(error).lower()
                    if not any(word in body for word in ("response_format", "json_schema", "structured")):
                        raise
                if self.settings.llm.structured_output == "on":
                    raise
                self.structured_chain = None
        message = self.plain_chain.invoke(values)
        if getattr(message, "response_metadata", {}).get("finish_reason") == "length":
            raise ValueError("Translation truncated: increase max_tokens or reduce chunk_size")
        return TranslationResult(translation=response_text(message)).translation
