# API reference

## Clients

AuthZENClient and AsyncAuthZENClient accept keyword-only constructor arguments.

| Argument | Default | Purpose |
| --- | --- | --- |
| base_url | Required | HTTPS PDP identifier |
| auth | None | HTTPX2 authentication |
| headers | None | Additional request headers |
| transport | None | HTTPX2 sync or async transport |
| timeout | 5.0 | Network-operation timeout, float, Timeout or None |
| limits | None | HTTPX2 connection limits |
| endpoints | None | Endpoints fallback configuration |
| http_client | None | Caller-owned HTTPX2 client |

Use the matching sync or async HTTP client and transport. Configure authentication
and network options directly on an injected http_client.

| Method | Input | Output |
| --- | --- | --- |
| evaluate | EvaluationRequest | EvaluationResponse |
| evaluate_batch | EvaluationsRequest | EvaluationsResponse |
| discover | None | PDPMetadata |
| search_resources | ResourceSearchRequest | ResourceSearchResponse |
| search_subjects | SubjectSearchRequest | SubjectSearchResponse |
| search_actions | ActionSearchRequest | ActionSearchResponse |
| iter_resources | ResourceSearchRequest | Iterator or AsyncIterator of Resource |
| iter_subjects | SubjectSearchRequest | Iterator or AsyncIterator of Subject |
| iter_actions | ActionSearchRequest | Iterator or AsyncIterator of Action |

Await async evaluate, batch, search and discover methods. Consume async iterators
with async for. Use close for the sync client and await aclose for the async one.

## Models

- Subject and Resource require string type and id, and accept JSON properties.
- Action requires string name and accepts JSON properties.
- Context wraps a JSON object through its root attribute.
- EvaluationRequest requires subject, action and resource, with optional Context.
- Decision contains a strict boolean decision and optional Context.
- EvaluationResponse is an alias for Decision.
- Evaluation contains optional entities inherited from an EvaluationsRequest.
- EvaluationsRequest adds evaluations and EvaluationsOptions to shared defaults.
- EvaluationsResponse contains ordered evaluations or a fallback decision.
- PageRequest accepts token, non-negative limit and JSON properties.
- PageResponse requires next_token and accepts non-negative count and total.
- SubjectQuery and ResourceQuery describe the queried entity type and properties.
- Search responses contain typed results, optional PageResponse and Context.
- PDPMetadata contains the PDP identifier, evaluation endpoint, optional endpoints
  and supported_capabilities.
- Endpoints contains the five fallback paths or absolute HTTPS URLs.

Models support Pydantic validation and round-trips. Unknown protocol fields are
ignored. JSON attributes inside Context and properties are retained. Batch options
retain additional JSON options. None represents an omitted optional field in the
new request models. The client omits it from the wire payload.
