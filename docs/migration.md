# Migrating from 0.1 to 0.2

## HTTPX2

Version 0.2 uses HTTPX2. Update imports in application code that supplies auth,
transports, timeouts or HTTP response objects.

```python
import httpx2
```

HTTPX2 classes and the original HTTPX classes belong to distinct packages.
Construct supplied objects from HTTPX2 for this release. Logger names and the
default User-Agent also use httpx2. TLS verification uses the operating system
trust store by default.

The public AuthZEN model names, evaluate and discover methods remain available.
AsyncAuthZENClient is also available from its dedicated async_client module.

## OAuth

The oauth extra now installs Authlib. Follow the
[authentication guide](authentication.md) to initialize an OAuth2Client or
AsyncOAuth2Client, fetch the initial token and pass it through http_client.
The caller owns that client's lifecycle.

## Examples

Run examples as modules from the repository root.

```bash
uv run python -m examples.evaluate
```

Additional Subject attributes belong in properties. The document example now
shows the application applying the decision before returning content.

## New APIs

Batch models, all three Search APIs, pagination iterators and per-client network
and endpoint settings are available. Discovery now reads optional endpoints for
these operations.
