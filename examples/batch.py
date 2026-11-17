"""Check access to several documents in one AuthZEN request."""

import httpx2

from authzen_client import AuthZENClient, Evaluation, EvaluationsRequest, Resource
from examples.stub_pdp import make_request, stub_pdp


def main() -> None:
    single = make_request()
    document_ids = ("123", "456", "missing")
    request = EvaluationsRequest(
        subject=single.subject,
        action=single.action,
        evaluations=[
            Evaluation(resource=Resource(type="document", id=value))
            for value in document_ids
        ],
    )
    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(stub_pdp)
    ) as client:
        response = client.evaluate_batch(request)
    assert response.evaluations is not None
    for document_id, decision in zip(document_ids, response.evaluations, strict=True):
        print(f"{document_id}: decision={decision.decision}")


if __name__ == "__main__":
    main()
