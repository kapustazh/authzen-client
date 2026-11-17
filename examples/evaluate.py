"""Check document access before returning content to an application user."""

import httpx2

from authzen_client import AuthZENClient
from examples.stub_pdp import DOCUMENTS, make_request, stub_pdp


def read_document(client: AuthZENClient, subject_id: str, document_id: str) -> str:
    """Enforce the PDP decision before returning a document."""
    response = client.evaluate(make_request(subject_id, document_id))
    if not response.decision:
        raise PermissionError("Document access denied")
    return DOCUMENTS[document_id]


def main() -> None:
    """Read the same document as an allowed and a denied user."""
    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(stub_pdp)
    ) as client:
        client.discover()
        for subject_id in ("alice", "bob"):
            try:
                content = read_document(client, subject_id, "123")
                print(f"{subject_id}: {content}")
            except PermissionError:
                print(f"{subject_id}: access denied")


if __name__ == "__main__":
    main()
