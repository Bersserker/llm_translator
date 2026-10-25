import httpx
import openai


def diagnostic(error: Exception) -> str:
    """Return bounded diagnostics without server bodies, headers, or credentials."""
    if isinstance(error, (openai.APITimeoutError, httpx.TimeoutException, TimeoutError)):
        return "Request timed out. Check the server and configured timeout."
    if isinstance(error, (openai.APIConnectionError, httpx.ConnectError, ConnectionError)):
        return "Cannot connect to the API server. Check the endpoint and server."
    status = getattr(error, "status_code", None)
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
    return {
        400: "HTTP 400: invalid request or unsupported model/options.",
        401: "HTTP 401: invalid or missing API key.",
        403: "HTTP 403: access denied.",
        404: "HTTP 404: endpoint or selected model not found.",
        429: "HTTP 429: rate limit exceeded.",
        500: "HTTP 500: API server error.",
        502: "HTTP 502: API gateway error.",
        503: "HTTP 503: API server unavailable.",
    }.get(status, "Invalid response or request failure. Check server configuration.")


def response_text(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        text = content
    elif isinstance(content, list) and all(isinstance(item, dict) for item in content):
        text = "".join(item.get("text", "") for item in content
                       if item.get("type") == "text" and isinstance(item.get("text"), str))
    else:
        raise ValueError("Invalid response format: expected text content.")
    if not text.strip():
        raise ValueError("Empty text response from API.")
    return text
