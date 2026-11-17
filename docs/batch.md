# Batch evaluations

Use evaluate_batch to send several evaluations in one HTTPS request.
The default endpoint is /access/v1/evaluations.

## Shared defaults

```python
from authzen_client import (
    Action, AuthZENClient, Evaluation, EvaluationsRequest, Resource, Subject,
)

request = EvaluationsRequest(
    subject=Subject(type="user", id="alice"),
    action=Action(name="read"),
    evaluations=[
        Evaluation(resource=Resource(type="document", id="123")),
        Evaluation(resource=Resource(type="document", id="456")),
    ],
)

with AuthZENClient(base_url="https://pdp.example.com") as client:
    response = client.evaluate_batch(request)

for decision in response.evaluations or []:
    print(decision.decision)
```

Each entry inherits omitted subject, action, resource and context from the
top-level request. An entry replaces a supplied entity in full. An explicitly
empty Context overrides a shared Context with an empty object.

Each effective evaluation must provide a subject, action and resource. Models
validate these requirements before sending the request.

## Execution semantics

```python
from authzen_client import EvaluationsOptions

options = EvaluationsOptions(evaluations_semantic="deny_on_first_deny")
```

The supported semantics are execute_all, deny_on_first_deny and
permit_on_first_permit. Execute all is the default. A PDP may return only the
evaluated prefix. The client returns that response as sent.

Results preserve request order. Additional PDP options can be passed through
EvaluationsOptions.model_validate with JSON-compatible extra fields.

An empty or omitted evaluations array uses the protocol's single-evaluation
fallback. In that case, provide top-level subject, action and resource and read
the response decision field.

## Errors

A general HTTP or protocol error raises an SDK exception. Individual negative
decisions, including PDP-provided error details in Context, remain ordered results.

For large workloads, choose batch sizes according to your PDP's documented limits.
Requests are sent as provided. The asynchronous client offers the same method
with await.

Run the bundled example.

```bash
uv run python -m examples.batch
```
