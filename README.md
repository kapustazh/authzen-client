# authzen-client

## Description

A typed Python client for the [AuthZEN Authorization API](https://openid.net/specs/authorization-api-1_0.html).
Ask a PDP whether a subject can perform an action on a resource. Supports sync
and async evaluation, discovery, and authentication.

## Instructions

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/kapustazh/authzen-client.git
cd authzen-client
uv sync
```

### Example usage

From the repository root, run the example against the bundled Stub-PDP.

```bash
uv run python examples/evaluate.py
```

```text
alice: decision=True
bob: decision=False
```

The client is used as follows. HTTPX MockTransport connects it to the Stub-PDP.

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
    client.discover()
    response = client.evaluate(request)

print(response.decision)  # True
```

For a real PDP, supply its HTTPS base_url and omit transport.

A denial returns decision=False. Network failures raise TransportError, while
HTTP errors and invalid responses raise ProtocolError.

### Async usage

Use AsyncAuthZENClient with async with, and await its methods.

```bash
uv run python examples/async_evaluate.py
```

Both clients support discover() to load the PDP evaluation endpoint. This step
is optional when the PDP uses the default path, /access/v1/evaluation.

### Authentication

Use headers for Bearer tokens and API keys, or auth for an HTTPX auth object.
The OAuth Client Credentials example uses httpx-auth and prints True.

```bash
uv sync --extra oauth
uv run --extra oauth python examples/oauth.py
```

OAuth token requests are synchronous and require an HTTPS endpoint. Opaque token
responses must include expires_in.

### Development

```bash
uv run pytest
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run mypy src tests examples
```

### Build

Build the wheel and source distribution into dist/.

```bash
uv build
```

### Development notes

I spent approximately 4–5 hours on the task. With more time, I would add batch
evaluations and paginated search.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
