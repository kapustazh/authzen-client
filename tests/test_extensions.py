import json

import httpx2
import pytest
from pydantic import BaseModel, ValidationError

from authzen_client import (
    Action,
    ActionSearchRequest,
    ActionSearchResponse,
    AsyncAuthZENClient,
    AuthZENClient,
    Context,
    Decision,
    Endpoints,
    Evaluation,
    EvaluationsOptions,
    EvaluationsRequest,
    EvaluationsResponse,
    PageRequest,
    PageResponse,
    ProtocolError,
    Resource,
    ResourceQuery,
    ResourceSearchRequest,
    ResourceSearchResponse,
    Subject,
    SubjectQuery,
    SubjectSearchRequest,
    SubjectSearchResponse,
)

SUBJECT = Subject(type="user", id="alice")
ACTION = Action(name="read")
RESOURCE = Resource(type="document", id="123")
RESOURCE_SEARCH = ResourceSearchRequest(
    subject=SUBJECT, action=ACTION, resource=ResourceQuery(type="document")
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    "model",
    [
        Evaluation(subject=SUBJECT),
        EvaluationsOptions.model_validate(
            {"evaluations_semantic": "deny_on_first_deny", "custom": {"nested": None}}
        ),
        EvaluationsRequest(
            subject=SUBJECT, action=ACTION, evaluations=[Evaluation(resource=RESOURCE)]
        ),
        EvaluationsResponse(evaluations=[Decision(decision=False)]),
        EvaluationsResponse(decision=False),
        PageRequest(limit=0, token="opaque", properties={"sort": "name"}),
        PageResponse(next_token="", count=0),
        SubjectQuery(type="user"),
        ResourceQuery(type="document"),
        RESOURCE_SEARCH,
        SubjectSearchRequest(
            subject=SubjectQuery(type="user"), action=ACTION, resource=RESOURCE
        ),
        ActionSearchRequest(subject=SUBJECT, resource=RESOURCE),
        ResourceSearchResponse(results=[RESOURCE]),
        SubjectSearchResponse(results=[SUBJECT]),
        ActionSearchResponse(results=[ACTION]),
        Endpoints(evaluation="/custom/check"),
    ],
)
def test_extension_models_round_trip(model: BaseModel) -> None:
    assert type(model).model_validate_json(model.model_dump_json()) == model


@pytest.mark.parametrize(
    "payload",
    [{}, {"evaluations": [{}]}, {"subject": SUBJECT.model_dump(), "evaluations": []}],
)
def test_batch_requires_complete_inherited_entities(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EvaluationsRequest.model_validate(payload)


@pytest.mark.parametrize(
    "model,payload",
    [
        (PageRequest, {"limit": -1}),
        (PageRequest, {"limit": True}),
        (PageResponse, {"next_token": "", "total": -1}),
        (PageResponse, {}),
        (EvaluationsResponse, {}),
        (Endpoints, {"resources": "http://pdp.example.com/search"}),
        (Endpoints, {"resources": "//other.example.com/search"}),
        (Endpoints, {"resources": "relative"}),
    ],
)
def test_invalid_extension_values(
    model: type[BaseModel], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_batch_options_reject_non_json() -> None:
    with pytest.raises(ValidationError):
        EvaluationsOptions.model_validate({"custom": {1}})


def test_batch_preserves_defaults_overrides_and_empty_context() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/tenant/access/v1/evaluations"
        payload = json.loads(request.content)
        assert payload["context"] == {"tenant": "one"}
        assert payload["options"]["custom"] is None
        assert payload["evaluations"][0] == {
            "resource": {"type": "document", "id": "123"},
            "context": {},
        }
        assert payload["evaluations"][1]["action"] == {"name": "write"}
        return httpx2.Response(
            200, json={"evaluations": [{"decision": True}, {"decision": False}]}
        )

    request = EvaluationsRequest(
        subject=SUBJECT,
        action=ACTION,
        context=Context({"tenant": "one"}),
        options=EvaluationsOptions.model_validate({"custom": None}),
        evaluations=[
            Evaluation(resource=RESOURCE, context=Context()),
            Evaluation(resource=RESOURCE, action=Action(name="write")),
        ],
    )
    with AuthZENClient(
        base_url="https://pdp.example.com/tenant",
        transport=httpx2.MockTransport(handler),
    ) as client:
        assert client.evaluate_batch(request).evaluations is not None


def test_batch_empty_array_uses_single_decision() -> None:
    request = EvaluationsRequest(subject=SUBJECT, action=ACTION, resource=RESOURCE)
    with AuthZENClient(
        base_url="https://pdp.example.com",
        transport=httpx2.MockTransport(
            lambda r: httpx2.Response(200, json={"decision": False})
        ),
    ) as client:
        assert client.evaluate_batch(request).decision is False


@pytest.mark.parametrize(
    "kind,search_request,result",
    [
        ("resources", RESOURCE_SEARCH, RESOURCE.model_dump()),
        (
            "subjects",
            SubjectSearchRequest(
                subject=SubjectQuery(type="user"), action=ACTION, resource=RESOURCE
            ),
            SUBJECT.model_dump(),
        ),
        (
            "actions",
            ActionSearchRequest(subject=SUBJECT, resource=RESOURCE),
            ACTION.model_dump(),
        ),
    ],
)
def test_each_search_api(
    kind: str, search_request: BaseModel, result: dict[str, object]
) -> None:
    paths = {
        "resources": "/access/v1/search/resource",
        "subjects": "/access/v1/search/subject",
        "actions": "/access/v1/search/action",
    }

    def handler(http_request: httpx2.Request) -> httpx2.Response:
        assert http_request.method == "POST"
        assert http_request.url.path == paths[kind]
        return httpx2.Response(200, json={"results": [result]})

    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
    ) as client:
        response = getattr(client, f"search_{kind}")(search_request)
    assert response.results[0].model_dump() == result


def test_pagination_preserves_query_and_continues_through_empty_page() -> None:
    request = RESOURCE_SEARCH.model_copy(deep=True)
    request.page = PageRequest(limit=2, properties={"sort": "id"})
    before = request.model_dump()
    calls: list[dict[str, object]] = []

    def handler(http_request: httpx2.Request) -> httpx2.Response:
        payload = json.loads(http_request.content)
        calls.append(payload)
        if len(calls) == 1:
            assert "token" not in payload["page"]
            return httpx2.Response(
                200, json={"results": [], "page": {"next_token": "opaque"}}
            )
        assert payload["page"] == {
            "limit": 2,
            "properties": {"sort": "id"},
            "token": "opaque",
        }
        assert payload["subject"] == {"type": "user", "id": "alice"}
        return httpx2.Response(
            200,
            json={
                "results": [{"type": "document", "id": "123"}],
                "page": {"next_token": ""},
            },
        )

    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
    ) as client:
        assert [r.id for r in client.iter_resources(request)] == ["123"]
    assert request.model_dump() == before
    assert len(calls) == 2


def test_repeated_pagination_token_raises() -> None:
    transport = httpx2.MockTransport(
        lambda r: httpx2.Response(
            200, json={"results": [], "page": {"next_token": "repeated"}}
        )
    )
    with (
        AuthZENClient(
            base_url="https://pdp.example.com", transport=transport
        ) as client,
        pytest.raises(ProtocolError, match="repeated"),
    ):
        list(client.iter_resources(RESOURCE_SEARCH))


def test_discovery_overrides_configured_batch_and_search_paths() -> None:
    paths: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        if request.method == "GET":
            return httpx2.Response(
                200,
                json={
                    "policy_decision_point": "https://pdp.example.com",
                    "access_evaluation_endpoint": "https://pdp.example.com/check",
                    "access_evaluations_endpoint": "https://pdp.example.com/batch",
                    "search_resource_endpoint": "https://pdp.example.com/find",
                },
            )
        if request.url.path == "/batch":
            return httpx2.Response(200, json={"evaluations": [{"decision": True}]})
        return httpx2.Response(200, json={"results": []})

    with AuthZENClient(
        base_url="https://pdp.example.com",
        endpoints=Endpoints(resources="/fallback"),
        transport=httpx2.MockTransport(handler),
    ) as client:
        client.discover()
        client.evaluate_batch(
            EvaluationsRequest(
                evaluations=[
                    Evaluation(subject=SUBJECT, action=ACTION, resource=RESOURCE)
                ]
            )
        )
        client.search_resources(RESOURCE_SEARCH)
    assert paths == ["/.well-known/authzen-configuration", "/batch", "/find"]


def test_network_settings_and_independent_endpoint_configuration() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.extensions["timeout"]["read"] == 12
        assert request.url.path == "/custom"
        return httpx2.Response(200, json={"results": []})

    with AuthZENClient(
        base_url="https://pdp.example.com",
        timeout=httpx2.Timeout(12),
        limits=httpx2.Limits(max_connections=2),
        endpoints=Endpoints(resources="/custom"),
        transport=httpx2.MockTransport(handler),
    ) as client:
        client.search_resources(RESOURCE_SEARCH)
    with AuthZENClient(base_url="https://pdp.example.com") as client:
        assert client._url("resources").endswith("/access/v1/search/resource")


@pytest.mark.anyio
async def test_async_batch_and_all_search_iterators() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("evaluations"):
            return httpx2.Response(200, json={"evaluations": [{"decision": False}]})
        result = {"resource": RESOURCE, "subject": SUBJECT, "action": ACTION}[
            request.url.path.rsplit("/", 1)[-1]
        ]
        return httpx2.Response(200, json={"results": [result.model_dump()]})

    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(handler)
    ) as client:
        result = await client.evaluate_batch(
            EvaluationsRequest(
                subject=SUBJECT,
                action=ACTION,
                resource=RESOURCE,
                evaluations=[Evaluation()],
            )
        )
        assert result.evaluations is not None
        assert result.evaluations[0].decision is False
        assert [r.id async for r in client.iter_resources(RESOURCE_SEARCH)] == ["123"]
        assert [
            s.id
            async for s in client.iter_subjects(
                SubjectSearchRequest(
                    subject=SubjectQuery(type="user"), action=ACTION, resource=RESOURCE
                )
            )
        ] == ["alice"]
        assert [
            a.name
            async for a in client.iter_actions(
                ActionSearchRequest(subject=SUBJECT, resource=RESOURCE)
            )
        ] == ["read"]


def test_external_client_configuration_is_explicit() -> None:
    with (
        httpx2.Client() as http,
        pytest.raises(ValueError, match="timeout"),
    ):
        AuthZENClient(base_url="https://pdp.example.com", http_client=http, timeout=5.0)


@pytest.mark.parametrize(
    "base_url,path",
    [
        ("https://pdp.example.com/tenant//", "/tenant//access/v1/search/resource"),
        (
            "https://pdp.example.com/tenant%2Fsegment/",
            "/tenant/segment/access/v1/search/resource",
        ),
    ],
)
def test_endpoint_construction_preserves_base_path(base_url: str, path: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == path
        return httpx2.Response(200, json={"results": []})

    with AuthZENClient(
        base_url=base_url, transport=httpx2.MockTransport(handler)
    ) as client:
        client.search_resources(RESOURCE_SEARCH)
