"""Use asynchronous OAuth token acquisition and AuthZEN evaluation."""

import asyncio
import os

import httpx2
from authlib.integrations.httpx_client import AsyncOAuth2Client

from authzen_client import (
    Action,
    AsyncAuthZENClient,
    EvaluationRequest,
    Resource,
    Subject,
)


async def main() -> None:
    token_url = os.environ["AUTHZEN_TOKEN_URL"]
    if httpx2.URL(token_url).scheme != "https":
        raise ValueError("AUTHZEN_TOKEN_URL must use HTTPS.")
    async with AsyncOAuth2Client(
        client_id=os.environ["AUTHZEN_CLIENT_ID"],
        client_secret=os.environ["AUTHZEN_CLIENT_SECRET"],
        scope=os.environ.get("AUTHZEN_SCOPE"),
        token_endpoint=token_url,
        grant_type="client_credentials",
    ) as http:
        await http.fetch_token(token_url, grant_type="client_credentials")
        async with AsyncAuthZENClient(
            base_url=os.environ["AUTHZEN_PDP_URL"], http_client=http
        ) as client:
            response = await client.evaluate(
                EvaluationRequest(
                    subject=Subject(type="user", id="alice"),
                    action=Action(name="read"),
                    resource=Resource(type="document", id="123"),
                )
            )
            print(response.decision)


if __name__ == "__main__":
    asyncio.run(main())
