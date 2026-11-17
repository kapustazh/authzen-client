# Development and builds

## Set up

```bash
uv sync --group docs
```

## Checks

```bash
uv run pytest
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run ty check
```

ty checks the library, tests and examples with every diagnostic enabled as an
error. Strict equality and generic narrowing are enabled. One targeted suppression
supports Pydantic's required annotation for validated extra JSON fields.

Tests use controlled HTTPX2 transports. OAuth tests exercise Authlib token
acquisition, renewal, errors and asynchronous concurrency. Deployed PDP/provider
integration and workload-specific performance still require verification.

## Documentation

```bash
uv run --group docs zensical serve
uv run --group docs zensical build --strict
```

The built site is written to site/.

## Build and install

```bash
uv build
python -m pip install dist/authzen_client-0.2.0-py3-none-any.whl
```

The source distribution includes the documentation, examples, tests and JSON
fixtures. The wheel contains the library and its py.typed marker.

Project metadata and the MIT license are included in the distribution. Publishing
requires a configured package-index account and an available distribution name.

## Pull requests

Develop changes on a separate branch and submit them through a pull request.
Run the local checks before requesting review.

The planned GitHub Actions setup will run Ruff, ty, the test matrix, package
builds and documentation builds on pull requests. Required status checks will
be configured through repository branch protection.
