"""Evaluate document access concurrently using the asynchronous client."""

import asyncio

import httpx2

from authzen_client import AsyncAuthZENClient
from examples.stub_pdp import make_request, stub_pdp


async def main() -> None:
    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com", transport=httpx2.MockTransport(stub_pdp)
    ) as client:
        await client.discover()
        results = await asyncio.gather(
            *(client.evaluate(make_request(user)) for user in ("alice", "bob"))
        )
        for user, result in zip(("alice", "bob"), results, strict=True):
            print(f"{user}: decision={result.decision}")


if __name__ == "__main__":
    asyncio.run(main())
