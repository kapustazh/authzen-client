# authzen-client

A typed Python SDK for the [AuthZEN Authorization API](https://openid.net/specs/authorization-api-1_0.html).
Supports sync and async evaluation, batch requests, paginated search, discovery,
and authentication through HTTPX2 and Authlib.

## Installation

Requires Python 3.12+. The package is on [PyPI](https://pypi.org/project/authzen-client/).

```bash
python -m pip install authzen-client
```

OAuth Client Credentials needs the optional extra.

```bash
python -m pip install 'authzen-client[oauth]'
```

## Quickstart

Pass the PDP's HTTPS base URL and apply its decision in your application.

```python
from authzen_client import Action, AuthZENClient, EvaluationRequest, Resource, Subject

request = EvaluationRequest(
    subject=Subject(type="user", id="alice"),
    action=Action(name="read"),
    resource=Resource(type="document", id="123"),
)

with AuthZENClient(base_url="https://pdp.example.com") as client:
    response = client.evaluate(request)

if response.decision:
    print("Access granted")
else:
    print("Access denied")
```

Run the bundled document-service example against an in-process PDP.

```bash
uv sync
uv run python -m examples.evaluate
```

```text
alice: AuthZEN project notes
bob: access denied
```

## Documentation

- [Quickstart and runnable examples](docs/quickstart.md)
- [Sync and async clients](docs/clients.md)
- [Batch evaluations](docs/batch.md)
- [Search and pagination](docs/search.md)
- [Authentication](docs/authentication.md)
- [Configuration and discovery](docs/configuration.md)
- [Errors](docs/errors.md)
- [API reference](docs/api.md)
- [Migrating from 0.1](docs/migration.md)
- [Development and builds](docs/development.md)

## License

[MIT](LICENSE).
