# Search and pagination

Search returns authorized entities. Resource Search finds resources a subject
may access. Subject Search finds permitted subjects. Action Search finds permitted
actions for a subject and resource.

## Resource Search

```python
from authzen_client import (
    Action, AuthZENClient, PageRequest, ResourceQuery, ResourceSearchRequest, Subject,
)

request = ResourceSearchRequest(
    subject=Subject(type="user", id="alice"),
    action=Action(name="read"),
    resource=ResourceQuery(type="document"),
    page=PageRequest(limit=20),
)

with AuthZENClient(base_url="https://pdp.example.com") as client:
    response = client.search_resources(request)
    for resource in response.results:
        print(resource.id)
```

ResourceQuery and SubjectQuery select an entity type and optional properties.
The protocol requires PDPs to ignore any id supplied on the queried entity.

## Automatic pagination

```python
with AuthZENClient(base_url="https://pdp.example.com") as client:
    for resource in client.iter_resources(request):
        print(resource.id)
```

The iterator fetches pages lazily, preserves the original query and page options,
and passes each opaque continuation token to the PDP. It handles empty pages
that still have a next token. It stops at an empty next_token or a response with
no page object. A repeated token raises ProtocolError to prevent an endless loop.

The input request is copied before iteration and remains available for reuse.
Results are yielded incrementally. Use the client context around the entire loop.

## Manual pagination

The response page contains next_token and optional count, total and properties.
Copy the token into the next request's page.token. Keep the entities, limit and
other pagination options identical.

A non-empty next_token signals another page. A zero limit is permitted by the
model. A particular PDP may reject or constrain it. Pagination does not guarantee
an atomic snapshot. Changes during traversal may cause missing or repeated items.

## Subject and Action Search

```python
from authzen_client import (
    ActionSearchRequest, Resource, SubjectQuery, SubjectSearchRequest,
)

subjects = SubjectSearchRequest(
    subject=SubjectQuery(type="user"),
    action=Action(name="read"),
    resource=Resource(type="document", id="123"),
)
actions = ActionSearchRequest(
    subject=Subject(type="user", id="alice"),
    resource=Resource(type="document", id="123"),
)
```

Use search_subjects or search_actions for a page and iter_subjects or iter_actions
for all pages. Async clients expose awaited search methods and async iterators.
Search results describe permissions at query time. Applications enforce access
according to their freshness requirements.

```bash
uv run python -m examples.search
```
