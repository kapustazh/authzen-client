"""In-process document policy service for runnable examples."""

import httpx2
from pydantic import ValidationError

from authzen_client import (
    Action,
    EvaluationRequest,
    EvaluationsRequest,
    PageRequest,
    Resource,
    ResourceSearchRequest,
    Subject,
)
from authzen_client.types import JsonObject

DEMO_EMAIL = "matvey.nesterenko@gmail.com"
DOCUMENTS = {
    "123": "AuthZEN project notes",
    "456": "Deployment checklist",
    "789": "API guide",
}


def make_request(
    subject_id: str = "alice", document_id: str = "123"
) -> EvaluationRequest:
    """Create a document-read request using the demonstration subject attributes."""
    return EvaluationRequest(
        subject=Subject(type="user", id=subject_id, properties={"email": DEMO_EMAIL}),
        action=Action(name="read"),
        resource=Resource(type="document", id=document_id),
    )


def allowed(evaluation: EvaluationRequest) -> bool:
    """Evaluate the fixed document policy used by all bundled examples."""
    return (
        evaluation.subject.type == "user"
        and evaluation.subject.id == "alice"
        and evaluation.subject.properties.get("email") == DEMO_EMAIL
        and evaluation.action.name == "read"
        and evaluation.resource.type == "document"
        and evaluation.resource.id in DOCUMENTS
    )


def _page(results: list[JsonObject], page: PageRequest | None) -> httpx2.Response:
    options = page or PageRequest()
    start = int(options.token or "0")
    limit = options.limit if options.limit is not None else 2
    if start < 0 or limit == 0:
        return httpx2.Response(400, text="Unsupported demo pagination parameters")
    items = results[start : start + limit]
    next_token = str(start + len(items)) if start + len(items) < len(results) else ""
    return httpx2.Response(
        200,
        json={
            "results": items,
            "page": {"next_token": next_token, "count": len(items)},
        },
    )


def stub_pdp(request: httpx2.Request) -> httpx2.Response:
    """Serve evaluation, batch, discovery and paginated search over MockTransport."""
    base = "https://pdp.example.com"
    path = request.url.path
    if request.method == "GET" and path == "/.well-known/authzen-configuration":
        return httpx2.Response(
            200,
            json={
                "policy_decision_point": base,
                "access_evaluation_endpoint": base + "/access/v1/evaluation",
                "access_evaluations_endpoint": base + "/access/v1/evaluations",
                "search_resource_endpoint": base + "/access/v1/search/resource",
            },
        )
    if request.method != "POST":
        return httpx2.Response(404, text="Unknown endpoint")
    try:
        if path == "/access/v1/evaluation":
            return httpx2.Response(
                200,
                json={
                    "decision": allowed(
                        EvaluationRequest.model_validate_json(request.content)
                    )
                },
            )
        if path == "/access/v1/evaluations":
            batch = EvaluationsRequest.model_validate_json(request.content)
            defaults = batch.model_dump(
                include={"subject", "action", "resource", "context"}, exclude_none=True
            )
            if not batch.evaluations:
                return httpx2.Response(
                    200,
                    json={
                        "decision": allowed(EvaluationRequest.model_validate(defaults))
                    },
                )
            decisions: list[JsonObject] = []
            for entry in batch.evaluations:
                values = defaults | entry.model_dump(
                    exclude_none=True, exclude_unset=True
                )
                decisions.append(
                    {"decision": allowed(EvaluationRequest.model_validate(values))}
                )
            return httpx2.Response(200, json={"evaluations": decisions})
        if path == "/access/v1/search/resource":
            resource_query = ResourceSearchRequest.model_validate_json(request.content)
            results: list[JsonObject] = [
                {"type": "document", "id": document_id}
                for document_id in DOCUMENTS
                if resource_query.resource.type == "document"
                and allowed(
                    EvaluationRequest(
                        subject=resource_query.subject,
                        action=resource_query.action,
                        resource=Resource(type="document", id=document_id),
                    )
                )
            ]
            return _page(results, resource_query.page)
    except (ValidationError, ValueError):
        return httpx2.Response(400, text="Invalid AuthZEN request")
    return httpx2.Response(404, text="Unknown endpoint")
