# Development and builds

## Set up

```bash
uv sync --group dev
```

## Checks

```bash
uv run pytest
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run ty check
```

ty checks the library, tests and examples with every diagnostic enabled as an
error. Strict equality and generic narrowing are enabled.

Tests use controlled HTTPX2 transports. OAuth tests exercise Authlib token
acquisition, renewal, errors and asynchronous concurrency. Deployed PDP/provider
integration and workload-specific performance still require verification.

## Build and install

```bash
uv build
python -m pip install dist/authzen_client-0.2.0-py3-none-any.whl
```

The source distribution includes the documentation, examples, tests and JSON
fixtures. The wheel contains the library and its py.typed marker.

Project metadata and the MIT license are included in the distribution.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request.

- Ruff, ty, and `uv build` run on Python 3.12. The built distributions are
  uploaded as a workflow artifact.
- pytest runs on Python 3.12, 3.13, and 3.14.

`.github/workflows/publish.yml` publishes to PyPI when a GitHub release is
published. It uses PyPI trusted publishing and the `pypi` GitHub environment.
Configure that environment and the PyPI project before the first release.

## Pull requests

Develop changes on a separate branch and submit them through a pull request.
Run the local checks before requesting review.

`.github/workflows/pr-size.yml` fails a pull request that changes more than 200
lines, counting additions and deletions. `uv.lock` is excluded. A push still
succeeds.
