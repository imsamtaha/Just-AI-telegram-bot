import asyncio

import pytest


pytest.importorskip("aiohttp")
fastapi = pytest.importorskip("fastapi")
fastapi_security = pytest.importorskip("fastapi.security")
web_app = pytest.importorskip("web_app")

HTTPException = fastapi.HTTPException
HTTPAuthorizationCredentials = fastapi_security.HTTPAuthorizationCredentials


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_status_allows_optional_web_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "model")
    monkeypatch.delenv("WEB_API_KEY", raising=False)

    response = asyncio.run(web_app.status())

    assert response.configured
    assert response.missing == []
    assert not response.web_chat_auth_configured


def test_authorize_chat_enforces_rate_limit(monkeypatch):
    monkeypatch.setenv("WEB_API_KEY", "secret")
    monkeypatch.setenv("WEB_RATE_LIMIT_REQUESTS", "1")
    web_app.request_times.clear()

    principal = asyncio.run(web_app.authorize_chat(bearer("secret")))

    assert principal
    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app.authorize_chat(bearer("secret")))
    assert error.value.status_code == 429


def test_authorize_chat_allows_anonymous_access_when_key_is_unset(monkeypatch):
    monkeypatch.delenv("WEB_API_KEY", raising=False)
    monkeypatch.setenv("WEB_RATE_LIMIT_REQUESTS", "10")
    web_app.request_times.clear()

    principal = asyncio.run(web_app.authorize_chat(None))

    assert principal == "anonymous"


def test_authorize_chat_requires_token_when_key_is_configured(monkeypatch):
    monkeypatch.setenv("WEB_API_KEY", "secret")

    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app.authorize_chat(None))

    assert error.value.status_code == 401


def test_authorize_chat_reports_invalid_rate_limit_configuration(monkeypatch):
    monkeypatch.setenv("WEB_API_KEY", "secret")
    monkeypatch.setenv("WEB_RATE_LIMIT_REQUESTS", "invalid")

    with pytest.raises(HTTPException) as error:
        asyncio.run(web_app.authorize_chat(bearer("secret")))

    assert error.value.status_code == 503
    assert error.value.detail == "WEB_RATE_LIMIT_REQUESTS must be a positive integer"
