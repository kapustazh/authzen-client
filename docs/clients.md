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

## Your own HTTP connection

A normal client does not pass http_client. The library opens the connection and
closes it at the end of the with block.

Pass http_client when you already have an HTTPX2 client. The OAuth guide does
this with an Authlib client that gets the access token. The library sends the
access check through that connection and does not close it. You close it.

```python
import httpx2
from authzen_client import AuthZENClient

with httpx2.Client() as http:
    with AuthZENClient(base_url="https://pdp.example.com", http_client=http) as client:
        response = client.evaluate(request)
```

Set authentication, transport, timeout, and connection limits on http. The
library rejects those arguments when http_client is set.
