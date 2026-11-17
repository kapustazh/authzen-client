import httpx2
import pytest

from authzen_client import (
    AsyncAuthZENClient,
    AuthZENClient,
    EvaluationRequest,
    PDPMetadata,
    ProtocolError,
    TransportError,
)

ENDPOINT = "https://pdp.example.com/custom/check?version=1"


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


@pytest.mark.parametrize("path", ["", "/tenant", "/tenant/"])
def test_discovery_selects_endpoint(
    evaluation_request: EvaluationRequest, path: str
) -> None:
    identifier = "https://pdp.example.com" + path
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.method)
        if request.method == "GET":
            assert "content-type" not in request.headers
            assert str(request.url) == (
                "https://pdp.example.com/.well-known/authzen-configuration" + path
            )
            return httpx2.Response(
                200,
                json={
                    "policy_decision_point": identifier,
                    "access_evaluation_endpoint": ENDPOINT,
                    "future_field": "ignored",
                },
            )
        assert str(request.url) == ENDPOINT
        return httpx2.Response(200, json={"decision": False})

    with AuthZENClient(
        base_url=identifier, transport=httpx2.MockTransport(handler)
    ) as client:
        metadata = client.discover()
        response = client.evaluate(evaluation_request)

    assert metadata.access_evaluation_endpoint == ENDPOINT
    assert PDPMetadata.model_validate_json(metadata.model_dump_json()) == metadata
    assert "future_field" not in metadata.model_dump()
    assert response.decision is False
    assert calls == ["GET", "POST"]


@pytest.mark.parametrize(
    "payload",
    [
        {"policy_decision_point": "https://pdp.example.com"},
        {"access_evaluation_endpoint": ENDPOINT},
        {
            "policy_decision_point": "https://other.example.com",
            "access_evaluation_endpoint": ENDPOINT,
        },
        {
            "policy_decision_point": "https://pdp.example.com",
            "access_evaluation_endpoint": "http://pdp.example.com/check",
        },
        {
            "policy_decision_point": "https://pdp.example.com",
            "access_evaluation_endpoint": None,
        },
    ],
)
def test_invalid_metadata_is_rejected(payload: object) -> None:
    response = httpx2.Response(200, json=payload)
    with (
        AuthZENClient(
            base_url="https://pdp.example.com",
            transport=httpx2.MockTransport(lambda request: response),
        ) as client,
        pytest.raises(ProtocolError) as error,
    ):
        client.discover()

    assert error.value.response is response


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(404),
        httpx2.Response(200, text="not JSON"),
        httpx2.Response(
            200, content=b"{", headers={"Content-Type": "application/json"}
        ),
    ],
)
def test_failed_discovery_keeps_default_endpoint(
    evaluation_request: EvaluationRequest, response: httpx2.Response
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET":
            return response
        assert request.url.path == "/tenant/access/v1/evaluation"
        return httpx2.Response(200, json={"decision": True})

    with AuthZENClient(
        base_url="https://pdp.example.com/tenant",
        transport=httpx2.MockTransport(handler),
    ) as client:
        with pytest.raises(ProtocolError):
            client.discover()
        assert client.evaluate(evaluation_request).decision is True


def test_metadata_transport_failure() -> None:
    failure = httpx2.ConnectTimeout("PDP unavailable")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise failure

    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
        ) as client,
        pytest.raises(TransportError) as error,
    ):
        client.discover()

    assert error.value.__cause__ is failure


@pytest.mark.anyio
async def test_async_discovery(evaluation_request: EvaluationRequest) -> None:
    async def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET":
            assert request.url.path == "/.well-known/authzen-configuration/tenant"
            return httpx2.Response(
                200,
                json={
                    "policy_decision_point": "https://pdp.example.com/tenant",
                    "access_evaluation_endpoint": ENDPOINT,
                },
            )
        assert str(request.url) == ENDPOINT
        return httpx2.Response(200, json={"decision": True})

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com/tenant",
        transport=httpx2.MockTransport(handler),
    ) as client:
        metadata = await client.discover()
        response = await client.evaluate(evaluation_request)

    assert metadata.access_evaluation_endpoint == ENDPOINT
    assert response.decision is True


@pytest.mark.anyio
async def test_async_discovery_rejects_identifier_mismatch() -> None:
    response = httpx2.Response(
        200,
        json={
            "policy_decision_point": "https://other.example.com",
            "access_evaluation_endpoint": ENDPOINT,
        },
    )
    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com",
        transport=httpx2.MockTransport(lambda request: response),
    ) as client:
        with pytest.raises(ProtocolError) as error:
            await client.discover()

    assert error.value.response is response
