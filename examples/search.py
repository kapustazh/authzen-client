"""List allowed documents while the client follows continuation tokens."""

import httpx2

from authzen_client import (
    AuthZENClient,
    PageRequest,
    ResourceQuery,
    ResourceSearchRequest,
)
from examples.stub_pdp import make_request, stub_pdp


def main() -> None:
    single = make_request()
    request = ResourceSearchRequest(
        subject=single.subject,
        action=single.action,
        resource=ResourceQuery(type="document"),
        page=PageRequest(limit=1),
    )
    with AuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(stub_pdp)
    ) as client:
        for document in client.iter_resources(request):
            print(f"document: {document.id}")


if __name__ == "__main__":
    main()
