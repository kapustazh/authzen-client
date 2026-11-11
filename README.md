# authzen-client

## Description

A typed Python client for the [AuthZEN Authorization API](https://openid.net/specs/authorization-api-1_0.html).
PEP-side SDK for requesting authorization decisions from a PDP.

## Instructions

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The local development environment uses Python 3.13, as specified in .python-version.

Clone the repository and install runtime and development dependencies.

```bash
git clone https://github.com/kapustazh/authzen-client.git
cd authzen-client
uv sync
```

### Example usage

Run the bundled example from the repository root.

```bash
uv run python examples/evaluate.py
```

Expected output is shown below.

```text
alice: decision=True
bob: decision=False
```

The bundled Stub-PDP handles requests through HTTPX MockTransport.

```python
import httpx

from authzen_client import (
    Action,
    AuthZENClient,
    EvaluationRequest,
    Resource,
    Subject,
)
from examples.evaluate import stub_pdp

request = EvaluationRequest(
    subject=Subject(type="user", id="alice"),
    action=Action(name="read"),
    resource=Resource(type="document", id="123"),
)

with AuthZENClient(
    base_url="https://pdp.example.com",
    transport=httpx.MockTransport(stub_pdp),
) as client:
    response = client.evaluate(request)

print(response.decision)  # True
```

For a real PDP, set base_url and use the default transport.

Denied access returns decision=False. Connection failures and timeouts raise
TransportError. HTTP errors and invalid responses raise ProtocolError.

### Async usage

Use AsyncAuthZENClient with async with and await client.evaluate(request).
Run the bundled async example with the same output as the synchronous example.

```bash
uv run python examples/async_evaluate.py
```

### Discovery

Call client.discover() to load the PDP evaluation endpoint. With the async
client, use await client.discover().

### Authentication

Pass credentials through headers or an HTTPX auth object through auth.

For OAuth Client Credentials, install the oauth extra and pass this auth object
to the synchronous client. Use an HTTPS token endpoint. Opaque token responses
must include expires_in.

```python
from httpx_auth import OAuth2ClientCredentials

auth = OAuth2ClientCredentials(
    token_url="https://issuer.example.com/token",
    client_id="client-id",
    client_secret="client-secret",
    scope="authzen:evaluate",
)
```

Run the OAuth example with stubbed token and PDP endpoints. It prints True.

```bash
uv sync --extra oauth
uv run --extra oauth python examples/oauth.py
```

### Development

```bash
uv run pytest
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run mypy src tests examples
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
