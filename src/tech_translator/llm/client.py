from langchain_openai import ChatOpenAI

from tech_translator.config import Settings


def create_client(settings: Settings) -> ChatOpenAI:
    config = settings.llm
    return ChatOpenAI(
        model=config.model, base_url=config.base_url,
        api_key=settings.llm_api_key.get_secret_value(), temperature=config.temperature,
        max_tokens=config.max_tokens, timeout=config.timeout,
        max_retries=config.max_retries, use_responses_api=False,
    )
