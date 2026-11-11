import asyncio
import json
from unittest.mock import patch

import httpx
import pytest

from authzen_client import (
    AsyncAuthZENClient,
    EvaluationRequest,
    ProtocolError,
    TransportError,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest.model_validate(
        {
            "subject": {"type": "user", "id": "alice"},
            "action": {"name": "read"},
            "resource": {"type": "document", "id": "123"},
        }
    )


@pytest.mark.parametrize("decision", [True, False])
async def test_async_evaluation(
    evaluation_request: EvaluationRequest, decision: bool
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://pdp.example.com/tenant/access/v1/evaluation"
        assert request.headers["authorization"] == "Bearer demo-token"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == evaluation_request.model_dump(
            mode="json", exclude_defaults=True
        )
        return httpx.Response(
            200, json={"decision": decision, "context": {"reason": "demo"}}
        )

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com/tenant",
        headers={"Authorization": "Bearer demo-token", "content-type": "text/plain"},
        transport=httpx.MockTransport(handler),
    ) as client:
        response = await client.evaluate(evaluation_request)

    assert response.decision is decision
    assert response.context.root == {"reason": "demo"}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, json={"decision": False}),
        httpx.Response(200, text="wrong content type"),
        httpx.Response(200, json={"decision": "false"}),
    ],
)
async def test_async_protocol_errors(
    evaluation_request: EvaluationRequest, response: httpx.Response
) -> None:
    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com",
        transport=httpx.MockTransport(lambda request: response),
    ) as client:
        with pytest.raises(ProtocolError) as error:
            await client.evaluate(evaluation_request)

    assert error.value.response is response


async def test_async_transport_error(evaluation_request: EvaluationRequest) -> None:
    failure = httpx.ReadTimeout("PDP unavailable")

    async def handler(request: httpx.Request) -> httpx.Response:
        raise failure

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(TransportError) as error:
            await client.evaluate(evaluation_request)

    assert error.value.__cause__ is failure


async def test_async_auth_object(evaluation_request: EvaluationRequest) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Basic Y2xpZW50OnNlY3JldA=="
        return httpx.Response(200, json={"decision": True})

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com",
        auth=httpx.BasicAuth("client", "secret"),
        transport=httpx.MockTransport(handler),
    ) as client:
        assert (await client.evaluate(evaluation_request)).decision is True


async def test_async_context_manager_closes_transport_on_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    with patch.object(transport, "aclose") as close:
        with pytest.raises(RuntimeError, match="application failed"):
            async with AsyncAuthZENClient(
                base_url="https://pdp.example.com", transport=transport
            ):
                raise RuntimeError("application failed")

        close.assert_awaited_once_with()


async def test_explicit_aclose_closes_transport() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    client = AsyncAuthZENClient(base_url="https://pdp.example.com", transport=transport)

    with patch.object(transport, "aclose") as close:
        await client.aclose()
        close.assert_awaited_once_with()


async def test_evaluations_can_run_concurrently(
    evaluation_request: EvaluationRequest,
) -> None:
    ready = asyncio.Event()
    started = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal started
        started += 1
        if started == 2:
            ready.set()
        await ready.wait()
        return httpx.Response(200, json={"decision": True})

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com", transport=httpx.MockTransport(handler)
    ) as client:
        results = await asyncio.wait_for(
            asyncio.gather(
                client.evaluate(evaluation_request), client.evaluate(evaluation_request)
            ),
            timeout=2,
        )

    assert started == 2
    assert all(result.decision for result in results)


async def test_async_client_rejects_http_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        AsyncAuthZENClient(base_url="http://pdp.example.com")
