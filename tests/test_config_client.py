import httpx
import pytest

from tech_translator.config import Settings, load_config
from tech_translator.llm.client import create_client


def test_environment_overrides_yaml(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("llm:\n  model: yaml-model\ntranslation:\n  glossary_path: glossary.yaml\n")
    monkeypatch.setenv("LLM__MODEL", "env-model")
    monkeypatch.setenv("LLM_API_KEY", "very-secret")
    settings = load_config(config)
    assert settings.llm.model == "env-model"
    assert settings.translation.glossary_path == tmp_path / "glossary.yaml"
    assert "very-secret" not in repr(settings)
    assert load_config(config, "cli-model").llm.model == "cli-model"


def test_reject_yaml_secret(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("llm_api_key: secret")
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        load_config(config)


def test_local_defaults_and_chat_completions():
    settings = Settings()
    client = create_client(settings)
    assert str(client.openai_api_base) == "http://localhost:1234/v1"
    assert client.use_responses_api is False
    assert client.max_tokens == 2048
    assert client.openai_api_key.get_secret_value() == "local"


def test_real_langchain_protocol_without_network():
    from langchain_core.messages import HumanMessage
    from tech_translator.llm.api_health import check_api
    requests = []
    def serve(request):
        requests.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(404, json={"error": "unsupported"})
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "local-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Сервер работает."}, "finish_reason": "stop"}],
        })
    with httpx.Client(transport=httpx.MockTransport(serve)) as transport:
        model = create_client(Settings()).model_copy(update={"http_client": transport})
        # Inject the transport at the OpenAI SDK layer used by the actual LangChain client.
        import openai
        sdk = openai.OpenAI(base_url="http://localhost:1234/v1", api_key="local", http_client=transport)
        model.client = sdk.chat.completions
        result = check_api(Settings(), llm=model, http_client=transport)
    assert result.generation_success and result.model_available is None
    assert requests[-1].url.path == "/v1/chat/completions"
