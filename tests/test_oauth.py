import asyncio
import time
from urllib.parse import parse_qs

import httpx2
import pytest
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client

from authzen_client import (
    AsyncAuthZENClient,
    AuthZENClient,
    EvaluationRequest,
    ProtocolError,
    TransportError,
)


@pytest.fixture
def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest.model_validate(
        {
            "subject": {"type": "user", "id": "alice"},
            "action": {"name": "read"},
            "resource": {"type": "document", "id": "123"},
        }
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_token_acquisition_expiry_and_reuse(
    evaluation_request: EvaluationRequest,
) -> None:
    issued: list[str] = []
    received: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "issuer.example.com":
            assert request.method == "POST"
            assert request.headers["authorization"] == "Basic Y2xpZW50OnNlY3JldA=="
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["client_credentials"],
                "scope": ["authzen:evaluate"],
            }
            issued.append(f"token-{len(issued) + 1}")
            return httpx2.Response(
                200,
                json={
                    "access_token": issued[-1],
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        received.append(request.headers["authorization"])
        return httpx2.Response(200, json={"decision": True})

    with OAuth2Client(
        "client",
        "secret",
        scope="authzen:evaluate",
        token_endpoint="https://issuer.example.com/token",
        grant_type="client_credentials",
        transport=httpx2.MockTransport(handler),
    ) as http:
        http.fetch_token(
            "https://issuer.example.com/token", grant_type="client_credentials"
        )
        with AuthZENClient(
            base_url="https://pdp.example.com", http_client=http
        ) as client:
            assert client.evaluate(evaluation_request).decision
            http.token = {**http.token, "expires_at": time.time() - 1}
            assert client.evaluate(evaluation_request).decision
            assert client.evaluate(evaluation_request).decision
        assert not http.is_closed
    assert issued == ["token-1", "token-2"]
    assert received == ["Bearer token-1", "Bearer token-2", "Bearer token-2"]


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(401, json={"error": "invalid_client"}),
        httpx2.Response(200, json={}),
        httpx2.Response(200, json=[]),
        httpx2.Response(
            200, content=b"{", headers={"Content-Type": "application/json"}
        ),
    ],
)
def test_token_errors_stop_evaluation(
    evaluation_request: EvaluationRequest, response: httpx2.Response
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "issuer.example.com"
        return response

    with (
        OAuth2Client(
            "client",
            "secret",
            token_endpoint="https://issuer.example.com/token",
            grant_type="client_credentials",
            token={"access_token": "old", "token_type": "Bearer", "expires_at": 1},
            transport=httpx2.MockTransport(handler),
        ) as http,
        AuthZENClient(base_url="https://pdp.example.com", http_client=http) as client,
        pytest.raises(ProtocolError),
    ):
        client.evaluate(evaluation_request)


def test_token_transport_failure(evaluation_request: EvaluationRequest) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectTimeout("Token endpoint unavailable")

    with (
        OAuth2Client(
            "client",
            "secret",
            token_endpoint="https://issuer.example.com/token",
            grant_type="client_credentials",
            token={"access_token": "old", "token_type": "Bearer", "expires_at": 1},
            transport=httpx2.MockTransport(handler),
        ) as http,
        AuthZENClient(base_url="https://pdp.example.com", http_client=http) as client,
        pytest.raises(TransportError),
    ):
        client.evaluate(evaluation_request)


@pytest.mark.anyio
async def test_async_token_renewal_is_nonblocking_and_shared(
    evaluation_request: EvaluationRequest,
) -> None:
    token_calls = 0
    received: list[str] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal token_calls
        if request.url.host == "issuer.example.com":
            token_calls += 1
            await asyncio.sleep(0)
            return httpx2.Response(
                200,
                json={
                    "access_token": f"token-{token_calls}",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        received.append(request.headers["authorization"])
        return httpx2.Response(200, json={"decision": True})

    async with AsyncOAuth2Client(
        "client",
        "secret",
        token_endpoint="https://issuer.example.com/token",
        grant_type="client_credentials",
        transport=httpx2.MockTransport(handler),
    ) as http:
        await http.fetch_token(
            "https://issuer.example.com/token", grant_type="client_credentials"
        )
        http.token = {**http.token, "expires_at": time.time() - 1}
        async with AsyncAuthZENClient(
            base_url="https://pdp.example.com", http_client=http
        ) as client:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *(client.evaluate(evaluation_request) for _ in range(5))
                ),
                timeout=2,
            )
        assert not http.is_closed
    assert token_calls == 2
    assert received == ["Bearer token-2"] * 5
    assert all(result.decision for result in results)


@pytest.mark.anyio
async def test_async_token_failure_is_protocol_error(
    evaluation_request: EvaluationRequest,
) -> None:
    async with (
        AsyncOAuth2Client(
            "client",
            "secret",
            token_endpoint="https://issuer.example.com/token",
            grant_type="client_credentials",
            token={"access_token": "old", "token_type": "Bearer", "expires_at": 1},
            transport=httpx2.MockTransport(
                lambda request: httpx2.Response(401, json={"error": "invalid_client"})
            ),
        ) as http,
        AsyncAuthZENClient(
            base_url="https://pdp.example.com", http_client=http
        ) as client,
    ):
        with pytest.raises(ProtocolError):
            await client.evaluate(evaluation_request)
