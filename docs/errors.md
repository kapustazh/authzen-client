# Errors

| Situation | Result |
| --- | --- |
| Valid HTTP 200 with decision=false | Regular denial result |
| Connection failure or timeout | TransportError |
| Unexpected HTTP status | ProtocolError |
| Invalid content type, encoding or response model | ProtocolError |
| Authentication failure during an SDK request | ProtocolError or TransportError |
| Invalid input model | Pydantic ValidationError |
| Invalid client configuration | ValueError |

TransportError and ProtocolError inherit from AuthZENError. The original cause
is preserved through exception chaining. ProtocolError exposes response when one
is available.

```python
from authzen_client import AuthZENError

try:
    response = client.evaluate(request)
except AuthZENError:
    # Choose an application policy for a failed authorization check.
    raise
```

A timeout can occur after the PDP has processed the request. The caller then has
an unknown result and must choose its failure policy. A protected operation may
be blocked while the technical error is logged or reported separately.

Initial Authlib fetch_token calls in the application raise Authlib or HTTPX2
exceptions directly. Failures while an injected OAuth client renews a token
inside an SDK operation are translated at the SDK request boundary.

The SDK performs one request per operation. Retry policy can be applied by the
caller using its overall deadline and the PDP's requirements. Take care with
credentials, tokens and sensitive attributes in logs.
