# Configuration and discovery

## Network settings

```python
import httpx2
from authzen_client import AuthZENClient

client = AuthZENClient(
    base_url="https://pdp.example.com",
    timeout=httpx2.Timeout(10.0, connect=3.0),
    limits=httpx2.Limits(max_connections=20, max_keepalive_connections=10),
)
client.close()
```

The default timeout is five seconds per network operation. Pass None to disable
it. Connection limits use HTTPX2 defaults unless configured. Cancellation in an
async caller propagates normally.

For an injected http_client, configure these values on the HTTP client itself.
HTTPX2 uses the operating system trust store for TLS verification by default.
Custom TLS and proxy configuration can be supplied through an injected client.

## Endpoint defaults

| Operation | Default path |
| --- | --- |
| Single evaluation | /access/v1/evaluation |
| Batch evaluations | /access/v1/evaluations |
| Subject Search | /access/v1/search/subject |
| Resource Search | /access/v1/search/resource |
| Action Search | /access/v1/search/action |

These are defaults from the AuthZEN HTTPS binding. A path prefix in base_url is
preserved when constructing endpoint URLs.

```python
from authzen_client import AuthZENClient, Endpoints

client = AuthZENClient(
    base_url="https://pdp.example.com/tenant",
    endpoints=Endpoints(resources="/custom/search"),
)
client.close()
```

The resulting resource search URL is https://pdp.example.com/tenant/custom/search.
Endpoints can also be absolute HTTPS URLs. Settings belong to each client.

## Discovery

Call discover explicitly, or await discover on the asynchronous client.

The client retrieves unsigned JSON metadata from the AuthZEN well-known location,
validates it, and requires an exact match between policy_decision_point and the
configured base_url. For a tenant path, the well-known segment is inserted before
that path as required by the protocol.

Advertised endpoint URLs take precedence over configured fallback paths. Optional
endpoints absent from metadata retain their fallback paths as described by the
HTTPS binding. A PDP may respond with an error for an unsupported operation.
The last valid metadata is exposed through client.metadata.

A failed discovery raises an exception and preserves the previous configuration.
Metadata is replaced only after validation succeeds. Signed metadata verification
is a possible future extension. Configure a trusted PDP and protect its metadata
endpoint because discovered URLs determine where subsequent requests are sent.
