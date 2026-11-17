# Authentication

## Headers and HTTPX2 auth

```python
import httpx2
from authzen_client import AuthZENClient

client = AuthZENClient(
    base_url="https://pdp.example.com",
    headers={"Authorization": "Bearer your-access-token"},
)
client.close()

with AuthZENClient(
    base_url="https://pdp.example.com",
    auth=httpx2.BasicAuth("username", "password"),
) as client:
    pass
```

Supply credentials from your application's configuration or secret store.
The application identity used to access the PDP API is independent of the Subject
in an evaluation request.

## OAuth Client Credentials

Install the OAuth extra.

```bash
python -m pip install 'authzen-client[oauth]'
```

Authlib provides synchronous and asynchronous OAuth clients compatible with HTTPX2.
Pass an initialized OAuth client through http_client. The application owns its
lifecycle. Configure the token endpoint and grant type so Authlib can obtain a
new token when the previous one approaches expiry.

```python
import os
from authlib.integrations.httpx_client import OAuth2Client
from authzen_client import AuthZENClient

token_url = os.environ["AUTHZEN_TOKEN_URL"]
with OAuth2Client(
    client_id=os.environ["AUTHZEN_CLIENT_ID"],
    client_secret=os.environ["AUTHZEN_CLIENT_SECRET"],
    token_endpoint=token_url,
    grant_type="client_credentials",
    scope=os.environ.get("AUTHZEN_SCOPE"),
) as http:
    http.fetch_token(token_url, grant_type="client_credentials")
    with AuthZENClient(
        base_url=os.environ["AUTHZEN_PDP_URL"],
        http_client=http,
    ) as client:
        response = client.evaluate(request)
```

The request variable is an EvaluationRequest as in the [quickstart](quickstart.md).
Use an HTTPS token endpoint. Access tokens are held by the supplied OAuth client.

## Asynchronous token acquisition

```python
import os
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authzen_client import AsyncAuthZENClient

token_url = os.environ["AUTHZEN_TOKEN_URL"]
async with AsyncOAuth2Client(
    client_id=os.environ["AUTHZEN_CLIENT_ID"],
    client_secret=os.environ["AUTHZEN_CLIENT_SECRET"],
    token_endpoint=token_url,
    grant_type="client_credentials",
    scope=os.environ.get("AUTHZEN_SCOPE"),
) as http:
    await http.fetch_token(token_url, grant_type="client_credentials")
    async with AsyncAuthZENClient(
        base_url=os.environ["AUTHZEN_PDP_URL"],
        http_client=http,
    ) as client:
        response = await client.evaluate(request)
```

Authlib coordinates renewal for concurrent calls sharing one AsyncOAuth2Client.
The initial token request and later renewal use asynchronous HTTP operations.
For Client Credentials, a new access token is obtained using client credentials.

## Configured-server examples

Provide AUTHZEN_PDP_URL, AUTHZEN_TOKEN_URL, AUTHZEN_CLIENT_ID and
AUTHZEN_CLIENT_SECRET in your environment. AUTHZEN_SCOPE is optional and must
match your provider configuration. The examples check user alice reading document
123. Adapt these entities to your policies.

```bash
uv sync --extra oauth
uv run --extra oauth python -m examples.oauth
uv run --extra oauth python -m examples.async_oauth
```

These examples contact the configured servers. Unit tests exercise the same
Authlib integration through controlled HTTPX2 transports.
