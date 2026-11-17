# Quickstart

## Install

Python 3.12+ is required.

```bash
python -m pip install authzen-client
```

OAuth Client Credentials needs the optional extra: `python -m pip install 'authzen-client[oauth]'`.

## Request a decision

```python
from authzen_client import Action, AuthZENClient, EvaluationRequest, Resource, Subject

request = EvaluationRequest(
    subject=Subject(type="user", id="alice"),
    action=Action(name="read"),
    resource=Resource(type="document", id="123"),
)

with AuthZENClient(base_url="https://pdp.example.com") as client:
    response = client.evaluate(request)

if not response.decision:
    raise PermissionError("Document access denied")
```

The PDP URL above is a placeholder. Supply your deployed PDP's HTTPS URL.
Authentication and trustworthy Subject data are configured by your application.

## Run a complete application example

The bundled example checks access before returning document content. It includes
an in-process PDP implemented through HTTPX2 MockTransport.

Run from the repository root.

```bash
uv sync
uv run python -m examples.evaluate
```

```text
alice: AuthZEN project notes
bob: access denied
```

Extra subject attributes, such as email, belong inside properties.

```python
subject = Subject(
    type="user",
    id="alice",
    properties={"email": "alice@example.com"},
)
```

## Other examples

```bash
uv run python -m examples.async_evaluate
uv run python -m examples.batch
uv run python -m examples.search
```

The [authentication guide](authentication.md) covers examples that use configured
OAuth and PDP servers.
