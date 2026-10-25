from time import perf_counter

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from tech_translator.config import Settings
from tech_translator.llm.client import create_client
from tech_translator.utils.errors import diagnostic, response_text


class APIHealthResult(BaseModel):
    connected: bool = False
    model_available: bool | None = None
    generation_success: bool = False
    response_time_ms: float | None = None
    test_response: str | None = None
    error: str | None = None


def check_api(settings: Settings, *, llm=None, http_client=None) -> APIHealthResult:
    result = APIHealthResult()
    client = http_client or httpx.Client(timeout=settings.llm.timeout)
    try:
        try:
            response = client.get(f"{settings.llm.base_url}/models", headers={
                "Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"})
            result.connected = True
            if response.is_success:
                payload = response.json()
                models = payload.get("data") if isinstance(payload, dict) else None
                if isinstance(models, list) and all(isinstance(m, dict) and isinstance(m.get("id"), str) for m in models):
                    result.model_available = any(m["id"] == settings.llm.model for m in models)
            # Listing is advisory; generation is authoritative even for stale catalogs.
        except (httpx.HTTPError, ValueError):
            pass
        started = perf_counter()
        try:
            model = llm if llm is not None else create_client(settings)
            message = model.invoke([
                SystemMessage(content="Translate the following text into Russian.\nReturn only the translation."),
                HumanMessage(content="The server is running successfully."),
            ])
            result.connected = True
            try:
                result.test_response = response_text(message)
            except ValueError as error:
                result.error = str(error)
                return result
            result.generation_success = True
        except Exception as error:
            status = getattr(error, "status_code", None)
            if status is not None:
                result.connected = True
            result.error = diagnostic(error)
        finally:
            result.response_time_ms = round((perf_counter() - started) * 1000, 2)
    finally:
        if http_client is None:
            client.close()
    return result
