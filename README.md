# authzen-client

## Description

A typed Python client for the [AuthZEN Authorization API](https://openid.net/specs/authorization-api-1_0.html).
PEP-side SDK for requesting authorization decisions from a PDP.

## Instructions

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The local development environment uses Python 3.13, as specified in `.python-version`.

Clone the repository and install runtime and development dependencies:

```bash
git clone https://github.com/kapustazh/authzen-client.git
cd authzen-client
uv sync
```

Check the project environment:

```bash
uv run python --version
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
