from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
import pytest

from tech_translator.config import Settings
from tech_translator.llm.translator import LangChainTranslator, TranslationResult


class FakeLLM(RunnableLambda):
    def with_structured_output(self, *args, **kwargs):
        return RunnableLambda(lambda _: TranslationResult(translation="Привет"))


def test_translation():
    translator = LangChainTranslator(Settings(), llm=FakeLLM(lambda _: AIMessage(content="Привет")))
    assert translator.translate("Hello", glossary={"Hello": "Привет"}) == "Привет"


def test_plain_output_and_context():
    config = Settings(llm={"structured_output": "off"})
    calls = []
    def invoke(prompt):
        calls.append(prompt.to_string())
        return AIMessage(content="Перевод")
    translator = LangChainTranslator(config, llm=RunnableLambda(invoke))
    assert translator.translate("Text", context="Previous", glossary={"server": "сервер"}) == "Перевод"
    assert "Previous" in calls[0] and "server: сервер" in calls[0]


def test_fallback():
    class Unsupported(FakeLLM):
        def with_structured_output(self, *args, **kwargs):
            def fail(_):
                raise NotImplementedError()
            return RunnableLambda(fail)
    translator = LangChainTranslator(Settings(), llm=Unsupported(lambda _: AIMessage(content="Текст")))
    assert translator.translate("Text") == "Текст"
    assert translator.structured_chain is None


@pytest.mark.parametrize("content", ["", "   "])
def test_empty_translation(content):
    translator = LangChainTranslator(Settings(llm={"structured_output": "off"}),
                                     llm=RunnableLambda(lambda _: AIMessage(content=content)))
    with pytest.raises(ValueError):
        translator.translate("Text")
