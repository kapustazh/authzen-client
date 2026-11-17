"""Request AuthZEN decisions using asynchronous HTTPS."""

from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx2
from pydantic import BaseModel

from authzen_client._client import (
    Endpoint,
    _ClientBase,
    _request_errors,
    _response_model,
)
from authzen_client.models import (
    EvaluationRequest,
    EvaluationResponse,
    PDPMetadata,
)
from authzen_client.settings import Endpoints


class AsyncAuthZENClient(_ClientBase):
    """Request AuthZEN decisions using asynchronous HTTPS.

    Args:
        base_url: HTTPS PDP identifier. A path prefix is preserved.
        auth: HTTPX2 authentication object.
        headers: Additional headers. Content-Type is enforced as JSON.
        transport: HTTPX2 transport for testing or custom connections.
        timeout: Network-operation timeout, or None to disable timeouts.
        limits: Connection pool limits for the owned HTTP client.
        endpoints: Fallback paths or HTTPS URLs, overridden by discovery.
        http_client: Caller-owned HTTPX2 client, including Authlib clients.
            Configure its transport and authentication on that client.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth: httpx2.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx2.AsyncBaseTransport | None = None,
        timeout: httpx2.Timeout | float | None = 5.0,
        limits: httpx2.Limits | None = None,
        endpoints: Endpoints | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url, headers, endpoints)
        if http_client is not None and (
            auth is not None
            or transport is not None
            or limits is not None
            or timeout != 5.0
        ):
            raise ValueError(
                "Configure auth, transport, timeout and limits on the supplied http_client."
            )
        self._owns_http = http_client is None
        self._http = (
            http_client
            if http_client is not None
            else httpx2.AsyncClient(
                auth=auth,
                transport=transport,
                timeout=timeout,
                limits=limits if limits is not None else httpx2.Limits(),
            )
        )

    async def _post(self, endpoint: Endpoint, request: BaseModel) -> httpx2.Response:
        with _request_errors():
            return await self._http.post(
                self._url(endpoint),
                headers=self._headers,
                json=request.model_dump(mode="json", exclude_defaults=True),
            )

    async def discover(self) -> PDPMetadata:
        """Validate PDP metadata and select its advertised endpoints."""
        with _request_errors():
            response = await self._http.get(self._metadata_url(), headers=self._headers)
        return self._accept_metadata(response)

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Return a single allow or deny decision."""
        return _response_model(
            await self._post("evaluation", request), EvaluationResponse
        )

    async def aclose(self) -> None:
        """Close the owned HTTP client. Borrowed clients remain caller-owned."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        """Enter the owned HTTP client context."""
        if self._owns_http:
            await self._http.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release owned HTTP resources on leaving the context."""
        await self.aclose()
