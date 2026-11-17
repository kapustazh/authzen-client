# AuthZEN Client

Ask a Policy Decision Point whether a subject may perform an action on a resource.
The SDK validates protocol data and handles HTTPS communication. Your application
applies the returned decision.

The SDK implements the [AuthZEN Authorization API 1.0](https://openid.net/specs/authorization-api-1_0.html).

## Features

- Typed Pydantic models and JSON serialization.
- Synchronous and asynchronous clients using HTTPX2.
- Single and batch evaluations, including shared defaults and short-circuit semantics.
- Subject, resource and action search with manual or automatic pagination.
- Discovery of all five API endpoints.
- Headers, HTTPX2 authentication and optional Authlib OAuth integration.
- Per-client endpoints, timeouts and connection limits.

Start with the [quickstart](quickstart.md). For migration from the HTTPX-based
release, see the [migration guide](migration.md).
