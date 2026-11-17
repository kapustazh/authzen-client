"""Request AuthZEN decisions using asynchronous HTTPS."""

from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from types import TracebackType
from typing import Self

import httpx2
from pydantic import BaseModel

from authzen_client._client import (
    _OMITTED,
    Endpoint,
    _ClientBase,
    _next_request,
    _Omitted,
    _page_state,
    _reject_borrowed_settings,
    _request_errors,
    _response_model,
    _timeout,
)
from authzen_client.models import (
    Action,
    ActionSearchRequest,
    ActionSearchResponse,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationsRequest,
    EvaluationsResponse,
    PDPMetadata,
    Resource,
    ResourceSearchRequest,
    ResourceSearchResponse,
    SearchRequest,
    SearchResponse,
    Subject,
    SubjectSearchRequest,
    SubjectSearchResponse,
)
from authzen_client.settings import Endpoints


class AsyncAuthZENClient(_ClientBase):
    """Request AuthZEN decisions using asynchronous HTTPS.

    Args:
        base_url: HTTPS PDP identifier. A path prefix is preserved.
        auth: HTTPX2 authentication object.
        headers: Additional headers. POST requests send JSON.
        transport: HTTPX2 transport for testing or custom connections.
        timeout: Network-operation timeout, or None to disable timeouts.
        limits: Connection pool limits for the owned HTTP client.
        endpoints: Fallback paths or HTTPS URLs, overridden by discovery.
        http_client: HTTPX2 client you created, including an Authlib client.
            You close it. Set its transport and authentication on that client.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth: httpx2.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx2.AsyncBaseTransport | None = None,
        timeout: httpx2.Timeout | float | None | _Omitted = _OMITTED,
        limits: httpx2.Limits | None = None,
        endpoints: Endpoints | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        super().__init__(base_url, headers, endpoints)
        if http_client is not None:
            _reject_borrowed_settings(
                auth=auth, transport=transport, limits=limits, timeout=timeout
            )
            self._owns_http = False
            self._http = http_client
            return
        self._owns_http = True
        self._http = httpx2.AsyncClient(
            auth=auth,
            transport=transport,
            timeout=_timeout(timeout),
            limits=limits if limits is not None else httpx2.Limits(),
        )

    async def _post(self, endpoint: Endpoint, request: BaseModel) -> httpx2.Response:
        with _request_errors():
            return await self._http.post(
                self._url(endpoint),
                headers=self._body_headers(),
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

    async def evaluate_batch(self, request: EvaluationsRequest) -> EvaluationsResponse:
        """Return the batch response from the PDP."""
        return _response_model(
            await self._post("evaluations", request), EvaluationsResponse
        )

    async def search_resources(
        self, request: ResourceSearchRequest
    ) -> ResourceSearchResponse:
        """Fetch one page of resources permitted for the subject and action."""
        return _response_model(
            await self._post("resources", request), ResourceSearchResponse
        )

    async def search_subjects(
        self, request: SubjectSearchRequest
    ) -> SubjectSearchResponse:
        """Fetch one page of subjects permitted for the resource and action."""
        return _response_model(
            await self._post("subjects", request), SubjectSearchResponse
        )

    async def search_actions(
        self, request: ActionSearchRequest
    ) -> ActionSearchResponse:
        """Fetch one page of actions permitted for the subject and resource."""
        return _response_model(
            await self._post("actions", request), ActionSearchResponse
        )

    async def _iterate[T: SearchRequest, R: Subject | Resource | Action](
        self,
        request: T,
        search: Callable[[T], Awaitable[SearchResponse[R]]],
    ) -> AsyncIterator[R]:
        current: T | None
        current, seen = _page_state(request)
        while current is not None:
            response = await search(current)
            for result in response.results:
                yield result
            current = _next_request(current, response.page, seen)

    def iter_resources(self, request: ResourceSearchRequest) -> AsyncIterator[Resource]:
        """Lazily yield resources across pages without changing the input request."""
        return self._iterate(request, self.search_resources)

    def iter_subjects(self, request: SubjectSearchRequest) -> AsyncIterator[Subject]:
        """Lazily yield subjects across pages."""
        return self._iterate(request, self.search_subjects)

    def iter_actions(self, request: ActionSearchRequest) -> AsyncIterator[Action]:
        """Lazily yield actions across pages."""
        return self._iterate(request, self.search_actions)

    async def aclose(self) -> None:
        """Close the HTTP client this library opened. A passed http_client stays open."""
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
