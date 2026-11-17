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
uv run python -m examples.evaluate
```

```text
alice: AuthZEN project notes
bob: access denied
```

The client is used as follows. HTTPX2 MockTransport connects it to the Stub-PDP.

```python
import httpx2

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
    transport=httpx2.MockTransport(stub_pdp),
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
uv run python -m examples.async_evaluate
```

Both clients support discover() to load the PDP evaluation endpoint. This step
is optional when the PDP uses the default path, /access/v1/evaluation.

### Authentication

Use headers for Bearer tokens and API keys, or auth for an HTTPX2 auth object.
For OAuth Client Credentials, install the oauth extra and pass an Authlib
OAuth2Client or AsyncOAuth2Client through http_client. The caller owns its lifecycle.

The examples read AUTHZEN_PDP_URL, AUTHZEN_TOKEN_URL, AUTHZEN_CLIENT_ID and
AUTHZEN_CLIENT_SECRET from environment variables. AUTHZEN_SCOPE is optional.
Use an HTTPS token endpoint and fetch the initial token before evaluating.

```bash
uv sync --extra oauth
uv run --extra oauth python -m examples.oauth
uv run --extra oauth python -m examples.async_oauth
```

### Development

```bash
uv run pytest
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run ty check
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
