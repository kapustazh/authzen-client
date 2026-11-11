"""Run the client against an in-process Stub-PDP."""

import httpx

from authzen_client import (
    Action,
    AuthZENClient,
    EvaluationRequest,
    Resource,
    Subject,
)


def stub_pdp(request: httpx.Request) -> httpx.Response:
    """Allow Alice to read document 123 using a fixed demonstration policy."""
    if request.method != "POST" or request.url.path != "/access/v1/evaluation":
        return httpx.Response(404, text="Unknown endpoint")

    evaluation = EvaluationRequest.model_validate_json(request.content)
    allowed = (
        evaluation.subject.type == "user"
        and evaluation.subject.id == "alice"
        and evaluation.action.name == "read"
        and evaluation.resource.type == "document"
        and evaluation.resource.id == "123"
    )
    return httpx.Response(200, json={"decision": allowed})


def main() -> None:
    """Print an allow and a deny decision from the Stub-PDP."""
    with AuthZENClient(
        base_url="https://pdp.example.com",
        transport=httpx.MockTransport(stub_pdp),
    ) as client:
        for subject_id in ("alice", "bob"):
            request = EvaluationRequest(
                subject=Subject(type="user", id=subject_id),
                action=Action(name="read"),
                resource=Resource(type="document", id="123"),
            )
            response = client.evaluate(request)
            print(f"{subject_id}: decision={response.decision}")


if __name__ == "__main__":
    main()
