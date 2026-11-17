# Sync and async clients

## Synchronous use

Use one client across related operations to reuse HTTP connections.

```python
from authzen_client import AuthZENClient

with AuthZENClient(base_url="https://pdp.example.com") as client:
    response = client.evaluate(request)
```

The request variable represents an EvaluationRequest created as in the
[quickstart](quickstart.md).

## Asynchronous use

```python
from authzen_client import AsyncAuthZENClient

async with AsyncAuthZENClient(base_url="https://pdp.example.com") as client:
    response = await client.evaluate(request)
```

Batch, search and discovery methods are awaited in the same way.
Use async for to consume asynchronous result iterators.

```python
async with AsyncAuthZENClient(base_url="https://pdp.example.com") as client:
    async for resource in client.iter_resources(search_request):
        print(resource.id)
```

The application controls task scheduling and concurrency. For several independent
requests, it can use asyncio.gather and an appropriate concurrency limit.

## Client ownership

By default, the SDK creates and owns its HTTPX2 client. Exiting with or async with
closes it. Explicit close and aclose methods are also available.

An injected http_client belongs to the caller. Keep it open while using the SDK
and close it in the outer application context. This supports Authlib clients and
custom TLS or proxy configuration.

```python
import httpx2
from authzen_client import AuthZENClient

with httpx2.Client() as http:
    with AuthZENClient(base_url="https://pdp.example.com", http_client=http) as client:
        response = client.evaluate(request)
```

Configure authentication, transport, timeout and connection limits on an injected
HTTP client. The SDK rejects conflicting constructor settings.
