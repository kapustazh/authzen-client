"""Request AuthZEN decisions using synchronous HTTPS."""

from collections.abc import Callable, Iterator, Mapping
from types import TracebackType
from typing import Self

import httpx2
from pydantic import BaseModel

from authzen_client._client import (
    Endpoint,
    _batch_response,
    _ClientBase,
    _next_request,
    _request_errors,
    _response_model,
)
from authzen_client.async_client import AsyncAuthZENClient
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

__all__ = ["AsyncAuthZENClient", "AuthZENClient"]


class AuthZENClient(_ClientBase):
    """Request AuthZEN decisions using synchronous HTTPS.

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
        transport: httpx2.BaseTransport | None = None,
        timeout: httpx2.Timeout | float | None = 5.0,
        limits: httpx2.Limits | None = None,
        endpoints: Endpoints | None = None,
        http_client: httpx2.Client | None = None,
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
            else httpx2.Client(
                auth=auth,
                transport=transport,
                timeout=timeout,
                limits=limits if limits is not None else httpx2.Limits(),
            )
        )

    def _post(self, endpoint: Endpoint, request: BaseModel) -> httpx2.Response:
        with _request_errors():
            return self._http.post(
                self._url(endpoint),
                headers=self._headers,
                json=request.model_dump(mode="json", exclude_defaults=True),
            )

    def discover(self) -> PDPMetadata:
        """Validate PDP metadata and select its advertised endpoints."""
        with _request_errors():
            response = self._http.get(self._metadata_url(), headers=self._headers)
        return self._accept_metadata(response)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Return a single allow or deny decision."""
        return _response_model(self._post("evaluation", request), EvaluationResponse)

    def evaluate_batch(self, request: EvaluationsRequest) -> EvaluationsResponse:
        """Return ordered batch decisions using the requested execution semantics."""
        response = self._post("evaluations", request)
        return _batch_response(response, request)

    def search_resources(
        self, request: ResourceSearchRequest
    ) -> ResourceSearchResponse:
        """Fetch one page of resources permitted for the subject and action."""
        return _response_model(self._post("resources", request), ResourceSearchResponse)

    def search_subjects(self, request: SubjectSearchRequest) -> SubjectSearchResponse:
        """Fetch one page of subjects permitted for the resource and action."""
        return _response_model(self._post("subjects", request), SubjectSearchResponse)

    def search_actions(self, request: ActionSearchRequest) -> ActionSearchResponse:
        """Fetch one page of actions permitted for the subject and resource."""
        return _response_model(self._post("actions", request), ActionSearchResponse)

    def _iterate[T: SearchRequest, R: Subject | Resource | Action](
        self,
        request: T,
        search: Callable[[T], SearchResponse[R]],
    ) -> Iterator[R]:
        current: T | None = request.model_copy(deep=True)
        token = request.page.token if request.page is not None else None
        seen = {token} if token is not None and token != "" else set()
        while current is not None:
            response = search(current)
            yield from response.results
            current = _next_request(current, response.page, seen)

    def iter_resources(self, request: ResourceSearchRequest) -> Iterator[Resource]:
        """Lazily yield resources across pages without changing the input request."""
        return self._iterate(request, self.search_resources)

    def iter_subjects(self, request: SubjectSearchRequest) -> Iterator[Subject]:
        """Lazily yield subjects across pages."""
        return self._iterate(request, self.search_subjects)

    def iter_actions(self, request: ActionSearchRequest) -> Iterator[Action]:
        """Lazily yield actions across pages."""
        return self._iterate(request, self.search_actions)

    def close(self) -> None:
        """Close the owned HTTP client. Borrowed clients remain caller-owned."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Self:
        """Enter the owned HTTP client context."""
        if self._owns_http:
            self._http.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release owned HTTP resources on leaving the context."""
        self.close()
