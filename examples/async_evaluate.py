"""Run asynchronous evaluations against the bundled Stub-PDP."""

import asyncio

import httpx
from evaluate import stub_pdp

from authzen_client import (
    Action,
    AsyncAuthZENClient,
    EvaluationRequest,
    Resource,
    Subject,
)


async def main() -> None:
    """Print an allow and a deny decision using the asynchronous client."""
    async with AsyncAuthZENClient(
        base_url="https://pdp.example.com",
        transport=httpx.MockTransport(stub_pdp),
    ) as client:
        await client.discover()
        for subject_id in ("alice", "bob"):
            request = EvaluationRequest(
                subject=Subject(type="user", id=subject_id),
                action=Action(name="read"),
                resource=Resource(type="document", id="123"),
            )
            response = await client.evaluate(request)
            print(f"{subject_id}: decision={response.decision}")


if __name__ == "__main__":
    asyncio.run(main())
