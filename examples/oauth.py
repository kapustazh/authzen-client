"""Run OAuth 2.0 Client Credentials against stubbed token and PDP endpoints."""

import httpx
from evaluate import stub_pdp
from httpx_auth import OAuth2ClientCredentials

from authzen_client import Action, AuthZENClient, EvaluationRequest, Resource, Subject


def stub_token_endpoint(request: httpx.Request) -> httpx.Response:
    """Issue a short-lived demonstration access token."""
    return httpx.Response(
        200,
        json={
            "access_token": "demo-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )


def authenticated_pdp(request: httpx.Request) -> httpx.Response:
    """Evaluate requests carrying the demonstration access token."""
    if request.headers.get("Authorization") != "Bearer demo-access-token":
        return httpx.Response(401, json={"error": "invalid_token"})
    return stub_pdp(request)


def main() -> None:
    """Obtain an access token and evaluate a request using that token."""
    with httpx.Client(
        transport=httpx.MockTransport(stub_token_endpoint)
    ) as token_client:
        auth = OAuth2ClientCredentials(
            token_url="https://issuer.example.com/token",
            client_id="demo-client",
            client_secret="demo-secret",
            scope="authzen:evaluate",
            client=token_client,
        )
        with AuthZENClient(
            base_url="https://pdp.example.com",
            auth=auth,
            transport=httpx.MockTransport(authenticated_pdp),
        ) as client:
            response = client.evaluate(
                EvaluationRequest(
                    subject=Subject(type="user", id="alice"),
                    action=Action(name="read"),
                    resource=Resource(type="document", id="123"),
                )
            )
            print(response.decision)


if __name__ == "__main__":
    main()
