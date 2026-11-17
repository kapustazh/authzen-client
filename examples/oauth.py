"""Use OAuth Client Credentials with a configured authorization server and PDP."""

import os

import httpx2
from authlib.integrations.httpx_client import OAuth2Client

from authzen_client import Action, AuthZENClient, EvaluationRequest, Resource, Subject


def main() -> None:
    token_url = os.environ["AUTHZEN_TOKEN_URL"]
    if httpx2.URL(token_url).scheme != "https":
        raise ValueError("AUTHZEN_TOKEN_URL must use HTTPS.")
    with OAuth2Client(
        client_id=os.environ["AUTHZEN_CLIENT_ID"],
        client_secret=os.environ["AUTHZEN_CLIENT_SECRET"],
        scope=os.environ.get("AUTHZEN_SCOPE"),
        token_endpoint=token_url,
        grant_type="client_credentials",
    ) as http:
        http.fetch_token(token_url, grant_type="client_credentials")
        with AuthZENClient(
            base_url=os.environ["AUTHZEN_PDP_URL"], http_client=http
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
