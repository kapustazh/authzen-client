import importlib
from functools import partial

import httpx2
import pytest

from authzen_client import AuthZENClient, Context
from examples.stub_pdp import make_request


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("evaluate", "bob: access denied"),
        ("batch", "missing: decision=False"),
        ("search", "document: 789"),
    ],
)
def test_runnable_examples(
    name: str, expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    module = importlib.import_module(f"examples.{name}")
    module.main()
    assert expected in capsys.readouterr().out


@pytest.mark.anyio
async def test_async_example(capsys: pytest.CaptureFixture[str]) -> None:
    from examples.async_evaluate import main

    await main()
    assert "bob: decision=False" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["oauth", "async_oauth"])
@pytest.mark.anyio
async def test_configured_oauth_entry_points(
    name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = importlib.import_module(f"examples.{name}")
    for key, value in {
        "AUTHZEN_PDP_URL": "https://pdp.example.com",
        "AUTHZEN_TOKEN_URL": "https://issuer.example.com/token",
        "AUTHZEN_CLIENT_ID": "client",
        "AUTHZEN_CLIENT_SECRET": "secret",
    }.items():
        monkeypatch.setenv(key, value)

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "issuer.example.com":
            assert request.headers["authorization"] == "Basic Y2xpZW50OnNlY3JldA=="
            return httpx2.Response(
                200,
                json={
                    "access_token": "from-provider",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        assert request.headers["authorization"] == "Bearer from-provider"
        return httpx2.Response(200, json={"decision": True})

    constructor = "AsyncOAuth2Client" if name == "async_oauth" else "OAuth2Client"
    monkeypatch.setattr(
        module,
        constructor,
        partial(getattr(module, constructor), transport=httpx2.MockTransport(handler)),
    )
    if name == "async_oauth":
        await module.main()
    else:
        module.main()
    assert capsys.readouterr().out.strip() == "True"


def test_json_null_attributes_survive_serialization() -> None:
    request = make_request()
    request.subject.properties["nullable"] = None
    request.context = Context({"nested": {"nullable": None}})

    def handler(http_request: httpx2.Request) -> httpx2.Response:
        import json

        payload = json.loads(http_request.content)
        assert payload["subject"]["properties"]["nullable"] is None
        assert payload["context"]["nested"]["nullable"] is None
        return httpx2.Response(200, json={"decision": True})

    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
    ) as client:
        assert client.evaluate(request).decision


@pytest.mark.anyio
@pytest.mark.parametrize("name", ["oauth", "async_oauth"])
async def test_oauth_examples_require_https_token_endpoint(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(f"examples.{name}")
    monkeypatch.setenv("AUTHZEN_TOKEN_URL", "http://issuer.example.com/token")
    with pytest.raises(ValueError, match="HTTPS"):
        if name == "async_oauth":
            await module.main()
        else:
            module.main()
