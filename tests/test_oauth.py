from collections.abc import Iterator
from urllib.parse import parse_qs

import httpx
import pytest
from httpx_auth import OAuth2, OAuth2ClientCredentials

from authzen_client import (
    AuthZENClient,
    EvaluationRequest,
    ProtocolError,
    TransportError,
)


@pytest.fixture(autouse=True)
def clear_token_cache() -> Iterator[None]:
    OAuth2.token_cache.clear()
    yield
    OAuth2.token_cache.clear()


@pytest.fixture
def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest.model_validate(
        {
            "subject": {"type": "user", "id": "alice"},
            "action": {"name": "read"},
            "resource": {"type": "document", "id": "123"},
        }
    )


def test_token_acquisition_expiry_and_reuse(
    evaluation_request: EvaluationRequest,
) -> None:
    issued: list[str] = []
    received: list[str] = []

    def token_endpoint(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://issuer.example.com/token"
        assert request.headers["authorization"] == "Basic Y2xpZW50OnNlY3JldA=="
        assert parse_qs(request.content.decode()) == {
            "grant_type": ["client_credentials"],
            "scope": ["authzen:evaluate"],
        }
        issued.append(f"token-{len(issued) + 1}")
        return httpx.Response(
            200,
            json={
                "access_token": issued[-1],
                "token_type": "Bearer",
                "expires_in": 1 if len(issued) == 1 else 3600,
            },
        )

    def pdp(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://pdp.example.com/access/v1/evaluation"
        received.append(request.headers["authorization"])
        return httpx.Response(200, json={"decision": True})

    with httpx.Client(transport=httpx.MockTransport(token_endpoint)) as token_client:
        auth = OAuth2ClientCredentials(
            token_url="https://issuer.example.com/token",
            client_id="client",
            client_secret="secret",
            scope="authzen:evaluate",
            client=token_client,
        )
        with AuthZENClient(
            base_url="https://pdp.example.com",
            auth=auth,
            transport=httpx.MockTransport(pdp),
        ) as client:
            for _ in range(3):
                assert client.evaluate(evaluation_request).decision is True

    assert issued == ["token-1", "token-2"]
    assert received == ["Bearer token-1", "Bearer token-2", "Bearer token-2"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"error": "invalid_client"}),
        httpx.Response(200, json={}),
        httpx.Response(200, content=b"{", headers={"Content-Type": "application/json"}),
        pytest.param(httpx.Response(200, json=[]), id="token-response-is-array"),
        pytest.param(
            httpx.Response(
                200, json={"access_token": "opaque-token", "token_type": "Bearer"}
            ),
            id="opaque-token-without-expiry",
        ),
        pytest.param(
            httpx.Response(
                200,
                json={
                    "access_token": "demo-token",
                    "token_type": "Bearer",
                    "expires_in": "tomorrow",
                },
            ),
            id="invalid-expiry",
        ),
    ],
)
def test_token_errors_stop_evaluation(
    evaluation_request: EvaluationRequest, response: httpx.Response
) -> None:
    def pdp(request: httpx.Request) -> httpx.Response:
        pytest.fail("The PDP was called after token acquisition failed.")

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: response)
    ) as token_client:
        auth = OAuth2ClientCredentials(
            token_url="https://issuer.example.com/token",
            client_id="client",
            client_secret="secret",
            client=token_client,
        )
        with (
            AuthZENClient(
                base_url="https://pdp.example.com",
                auth=auth,
                transport=httpx.MockTransport(pdp),
            ) as client,
            pytest.raises(ProtocolError) as error,
        ):
            client.evaluate(evaluation_request)

    assert error.value.__cause__ is not None


def test_token_transport_failure(evaluation_request: EvaluationRequest) -> None:
    failure = httpx.ConnectTimeout("Token endpoint unavailable")

    def token_endpoint(request: httpx.Request) -> httpx.Response:
        raise failure

    def pdp(request: httpx.Request) -> httpx.Response:
        pytest.fail("The PDP was called after token acquisition failed.")

    with httpx.Client(transport=httpx.MockTransport(token_endpoint)) as token_client:
        auth = OAuth2ClientCredentials(
            token_url="https://issuer.example.com/token",
            client_id="client",
            client_secret="secret",
            client=token_client,
        )
        with (
            AuthZENClient(
                base_url="https://pdp.example.com",
                auth=auth,
                transport=httpx.MockTransport(pdp),
            ) as client,
            pytest.raises(TransportError) as error,
        ):
            client.evaluate(evaluation_request)

    assert error.value.__cause__ is failure
