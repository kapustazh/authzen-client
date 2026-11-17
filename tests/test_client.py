import json
from unittest.mock import patch

import httpx2
import pytest

from authzen_client import (
    AuthZENClient,
    EvaluationRequest,
    ProtocolError,
    TransportError,
)

REQUEST_PAYLOAD = {
    "subject": {"type": "user", "id": "alice", "properties": {"department": "Sales"}},
    "action": {"name": "read"},
    "resource": {"type": "document", "id": "123"},
    "context": {"ip_address": "192.0.2.1"},
}


@pytest.fixture
def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest.model_validate(REQUEST_PAYLOAD)


@pytest.mark.parametrize(
    ("base_url", "expected_path", "decision"),
    [
        ("https://pdp.example.com", "/access/v1/evaluation", True),
        ("https://pdp.example.com/tenant/", "/tenant/access/v1/evaluation", False),
        ("https://pdp.example.com/test/", "/test/access/v1/evaluation", False),
    ],
)
def test_evaluation_request_and_response(
    evaluation_request: EvaluationRequest,
    base_url: str,
    expected_path: str,
    decision: bool,
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert request.url == f"https://pdp.example.com{expected_path}"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == REQUEST_PAYLOAD
        return httpx2.Response(
            200,
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"decision": decision, "context": {"reason": "policy evaluation"}},
        )

    with AuthZENClient(
        base_url=base_url, transport=httpx2.MockTransport(handler)
    ) as client:
        response = client.evaluate(evaluation_request)

    assert response.decision is decision
    assert response.context.root == {"reason": "policy evaluation"}


@pytest.mark.parametrize("status", [204, 302, 403, 500])
def test_non_200_status_is_a_protocol_error(
    evaluation_request: EvaluationRequest, status: int
) -> None:
    response = httpx2.Response(
        status,
        headers={"Location": "https://other.example.com"},
        json={"decision": False},
    )
    transport = httpx2.MockTransport(lambda request: response)

    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=transport
        ) as client,
        pytest.raises(ProtocolError) as error,
    ):
        client.evaluate(evaluation_request)

    assert error.value.response is response
    assert response.status_code == status
    assert response.json() == {"decision": False}


@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ({}, b'{"decision": true}'),
        ({"Content-Type": "text/html"}, b'{"decision": true}'),
        ({"Content-Type": "application/json"}, b'{"decision":'),
        ({"Content-Type": "application/json"}, b'{"decision": "false"}'),
    ],
)
def test_invalid_response_is_a_protocol_error(
    evaluation_request: EvaluationRequest, headers: dict[str, str], body: bytes
) -> None:
    response = httpx2.Response(200, headers=headers, content=body)
    transport = httpx2.MockTransport(lambda request: response)

    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=transport
        ) as client,
        pytest.raises(ProtocolError) as error,
    ):
        client.evaluate(evaluation_request)

    assert error.value.response is response


@pytest.mark.parametrize("error_type", [httpx2.ConnectError, httpx2.ReadTimeout])
def test_transport_failure_preserves_its_cause(
    evaluation_request: EvaluationRequest, error_type: type[httpx2.RequestError]
) -> None:
    failure = error_type("PDP unavailable")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise failure

    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
        ) as client,
        pytest.raises(TransportError) as error,
    ):
        client.evaluate(evaluation_request)

    assert error.value.__cause__ is failure


def test_invalid_content_encoding_is_a_protocol_error(
    evaluation_request: EvaluationRequest,
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
            content=b"invalid compressed data",
        )

    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
        ) as client,
        pytest.raises(ProtocolError) as error,
    ):
        client.evaluate(evaluation_request)

    assert isinstance(error.value.__cause__, httpx2.DecodingError)


def test_context_manager_closes_transport_on_error() -> None:
    transport = httpx2.MockTransport(lambda request: httpx2.Response(200))

    with patch.object(transport, "close") as close:
        with (
            pytest.raises(RuntimeError, match="application failed"),
            AuthZENClient(base_url="https://pdp.example.com", transport=transport),
        ):
            raise RuntimeError("application failed")

        close.assert_called_once_with()


def test_explicit_close_closes_transport() -> None:
    transport = httpx2.MockTransport(lambda request: httpx2.Response(200))
    client = AuthZENClient(base_url="https://pdp.example.com", transport=transport)

    with patch.object(transport, "close") as close:
        client.close()
        close.assert_called_once_with()


@pytest.mark.parametrize(
    "base_url",
    [
        "http://pdp.example.com",
        "https:///missing-host",
        "https://pdp.example.com?query=value",
        "https://pdp.example.com#fragment",
        "https://pdp.example.com:invalid",
    ],
)
def test_invalid_base_url_is_rejected(base_url: str) -> None:
    with pytest.raises(ValueError, match="base_url"):
        AuthZENClient(base_url=base_url)


@pytest.mark.parametrize(
    ("header", "credential"),
    [("Authorization", "Bearer demo-token"), ("X-API-Key", "demo-key")],
)
def test_credential_headers_are_forwarded(
    evaluation_request: EvaluationRequest, header: str, credential: str
) -> None:
    headers = {header: credential, "content-type": "text/plain"}
    original = headers.copy()

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers[header] == credential
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == REQUEST_PAYLOAD
        return httpx2.Response(200, json={"decision": True})

    with AuthZENClient(
        base_url="https://pdp.example.com",
        headers=headers,
        transport=httpx2.MockTransport(handler),
    ) as client:
        assert client.evaluate(evaluation_request).decision is True

    assert headers == original


def test_httpx_auth_is_used(evaluation_request: EvaluationRequest) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["authorization"] == "Basic Y2xpZW50OnNlY3JldA=="
        return httpx2.Response(200, json={"decision": True})

    with AuthZENClient(
        base_url="https://pdp.example.com",
        auth=httpx2.BasicAuth("client", "secret"),
        transport=httpx2.MockTransport(handler),
    ) as client:
        assert client.evaluate(evaluation_request).decision is True


def test_rejected_credentials_raise_protocol_error(
    evaluation_request: EvaluationRequest,
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["authorization"] == "Bearer invalid-token"
        return httpx2.Response(
            401,
            headers={"WWW-Authenticate": "Bearer"},
            text="Invalid credentials",
        )

    with (
        AuthZENClient(
            base_url="https://pdp.example.com",
            headers={"Authorization": "Bearer invalid-token"},
            transport=httpx2.MockTransport(handler),
        ) as client,
        pytest.raises(ProtocolError) as error,
    ):
        client.evaluate(evaluation_request)

    assert error.value.response is not None
    assert error.value.response.status_code == 401
