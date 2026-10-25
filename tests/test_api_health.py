from unittest.mock import Mock

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage
from typer.testing import CliRunner

from tech_translator.cli import app
from tech_translator.config import Settings
from tech_translator.llm.api_health import check_api


def http_client(status=200, payload=None):
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        status, json=payload if payload is not None else {"data": [{"id": "local-model"}]})))


def run_health(*, error=None, content="Сервер успешно работает.", status=200, payload=None):
    llm = Mock()
    llm.invoke = Mock(side_effect=error, return_value=AIMessage(content=content))
    with http_client(status, payload) as client:
        return check_api(Settings(), llm=llm, http_client=client)


def test_success():
    result = run_health()
    assert result.connected and result.model_available and result.generation_success
    assert result.response_time_ms >= 0
    assert result.test_response == "Сервер успешно работает."


@pytest.mark.parametrize("error, phrase", [
    (ConnectionError("secret"), "Cannot connect"),
    (TimeoutError("secret"), "timed out"),
])
def test_network_failures(error, phrase):
    result = run_health(error=error)
    assert not result.generation_success and phrase in result.error
    assert "secret" not in result.model_dump_json()


def test_unreachable_server():
    def fail(request):
        raise httpx.ConnectError("secret")
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        result = check_api(Settings(), llm=Mock(invoke=Mock(side_effect=ConnectionError())), http_client=client)
    assert not result.connected


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 502, 503])
def test_http_errors(status):
    response = httpx.Response(status, request=httpx.Request("POST", "http://localhost/v1/chat/completions"))
    error = openai.APIStatusError("secret", response=response, body={"secret": "hidden"})
    result = run_health(error=error, status=status)
    assert result.connected and not result.generation_success
    assert str(status) in result.error
    assert "secret" not in result.model_dump_json()


def test_missing_model():
    response = httpx.Response(404, request=httpx.Request("POST", "http://localhost"))
    result = run_health(payload={"data": []}, error=openai.NotFoundError("model missing", response=response, body=None))
    assert result.model_available is False
    assert not result.generation_success


@pytest.mark.parametrize("status,payload", [(404, {}), (405, {}), (501, {}), (200, {"invalid": []})])
def test_generation_without_models(status, payload):
    result = run_health(status=status, payload=payload)
    assert result.model_available is None
    assert result.generation_success


def test_empty_response():
    result = run_health(content="  ")
    assert not result.generation_success and "Empty" in result.error


def test_malformed_response():
    with http_client() as client:
        result = check_api(Settings(), llm=Mock(invoke=Mock(return_value={"bad": "format"})), http_client=client)
    assert not result.generation_success and "format" in result.error


def test_cli_json(monkeypatch):
    import tech_translator.cli as cli
    monkeypatch.setattr(cli, "check_api", lambda settings: run_health())
    result = CliRunner().invoke(app, ["test-api", "--json", "--model", "test"])
    assert result.exit_code == 0
    import json
    assert json.loads(result.stdout)["generation_success"] is True


def test_cli_failure(monkeypatch):
    import tech_translator.cli as cli
    monkeypatch.setattr(cli, "check_api", lambda settings: run_health(content=""))
    result = CliRunner().invoke(app, ["test-api", "--json"])
    assert result.exit_code == 1


@pytest.mark.integration
def test_live_api():
    import os
    if os.getenv("RUN_LLM_INTEGRATION") != "1":
        pytest.skip("Set RUN_LLM_INTEGRATION=1 to test a running local API")
    from tech_translator.config import load_config
    from pathlib import Path
    result = check_api(load_config(Path(os.getenv("LLM_CONFIG", "configs/default.yaml"))))
    assert result.generation_success, result.error
