"""Synchronous and asynchronous clients for AuthZEN single access evaluations."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ValidationError

from authzen_client.exceptions import ProtocolError, TransportError
from authzen_client.models import EvaluationRequest, EvaluationResponse, PDPMetadata


def _base_url(value: str) -> httpx.URL:
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as exc:
        raise ValueError("base_url must be a valid HTTPS URL.") from exc
    if url.scheme != "https" or not url.host or url.query or url.fragment:
        raise ValueError(
            "base_url must be an absolute HTTPS URL without a query or fragment."
        )
    return url


def _headers(values: Mapping[str, str] | None) -> httpx.Headers:
    headers = httpx.Headers(values)
    headers.setdefault("Accept", "application/json")
    headers["Content-Type"] = "application/json"
    return headers


@contextmanager
def _request_errors() -> Iterator[None]:
    try:
        yield
    except httpx.DecodingError as exc:
        raise ProtocolError("The PDP response could not be decoded.") from exc
    except httpx.RequestError as exc:
        raise TransportError("The AuthZEN HTTP request failed.") from exc
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise ProtocolError(
            "HTTP request or authentication failed.",
            response=getattr(exc, "response", None),
        ) from exc


def _response_model[T: BaseModel](response: httpx.Response, model: type[T]) -> T:
    if response.status_code != 200:
        raise ProtocolError(
            f"The PDP returned HTTP {response.status_code}, expected 200.",
            response=response,
        )

    media_type = response.headers.get("content-type", "").partition(";")[0]
    if media_type.strip().lower() != "application/json":
        raise ProtocolError(
            "The PDP response Content-Type must be application/json.",
            response=response,
        )

    try:
        return model.model_validate_json(response.content)
    except ValidationError as exc:
        raise ProtocolError(
            "The PDP returned an invalid response.", response=response
        ) from exc


def _metadata_url(identifier: str) -> str:
    url = urlsplit(identifier)
    path = "/.well-known/authzen-configuration" + url.path
    return urlunsplit((url.scheme, url.netloc, path, "", ""))


def _metadata_response(response: httpx.Response, identifier: str) -> PDPMetadata:
    metadata = _response_model(response, PDPMetadata)
    if metadata.policy_decision_point != identifier:
        raise ProtocolError(
            "The metadata PDP identifier does not match base_url.", response=response
        )
    return metadata


class AuthZENClient:
    """Request access decisions from an AuthZEN PDP.

    Args:
        base_url: HTTPS PDP base URL. Any path prefix is preserved.
        auth: HTTPX authentication object for accessing the PDP.
        headers: Additional request headers. Content-Type is enforced as JSON.
        transport: Optional HTTPX transport for testing or custom connections.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=_base_url(base_url),
            auth=auth,
            transport=transport,
            headers=_headers(headers),
        )
        self._pdp_identifier = base_url
        self._evaluation_url = "/access/v1/evaluation"

    def discover(self) -> PDPMetadata:
        """Fetch unsigned PDP metadata and select its evaluation endpoint.

        Raises:
            TransportError: The metadata request could not be completed.
            ProtocolError: Metadata is invalid or identifies a different PDP.
        """
        with _request_errors():
            response = self._http.get(_metadata_url(self._pdp_identifier))
        metadata = _metadata_response(response, self._pdp_identifier)
        self._evaluation_url = metadata.access_evaluation_endpoint
        return metadata

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Evaluate an access request, returning both allow and deny decisions.

        Raises:
            TransportError: A PDP or token request could not be completed.
            ProtocolError: Authentication failed or the PDP response was invalid.
        """
        payload = request.model_dump(mode="json", exclude_defaults=True)
        with _request_errors():
            response = self._http.post(self._evaluation_url, json=payload)
        return _response_model(response, EvaluationResponse)

    def close(self) -> None:
        """Close the HTTP client and its transport."""
        self._http.close()

    def __enter__(self) -> Self:
        """Open the HTTP client for use in a with block."""
        self._http.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the HTTP client when leaving a with block."""
        self._http.__exit__(exc_type, exc_value, traceback)


class AsyncAuthZENClient:
    """Request access decisions using asynchronous HTTPS connections.

    Args:
        base_url: HTTPS PDP base URL. Any path prefix is preserved.
        auth: HTTPX authentication object suitable for asynchronous requests.
        headers: Additional request headers. Content-Type is enforced as JSON.
        transport: Optional asynchronous HTTPX transport.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=_base_url(base_url),
            auth=auth,
            transport=transport,
            headers=_headers(headers),
        )
        self._pdp_identifier = base_url
        self._evaluation_url = "/access/v1/evaluation"

    async def discover(self) -> PDPMetadata:
        """Fetch unsigned PDP metadata and select its evaluation endpoint.

        Raises:
            TransportError: The metadata request could not be completed.
            ProtocolError: Metadata is invalid or identifies a different PDP.
        """
        with _request_errors():
            response = await self._http.get(_metadata_url(self._pdp_identifier))
        metadata = _metadata_response(response, self._pdp_identifier)
        self._evaluation_url = metadata.access_evaluation_endpoint
        return metadata

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Evaluate an access request, returning both allow and deny decisions.

        Raises:
            TransportError: A PDP or token request could not be completed.
            ProtocolError: Authentication failed or the PDP response was invalid.
        """
        payload = request.model_dump(mode="json", exclude_defaults=True)
        with _request_errors():
            response = await self._http.post(self._evaluation_url, json=payload)
        return _response_model(response, EvaluationResponse)

    async def aclose(self) -> None:
        """Close the asynchronous HTTP client and its transport."""
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        """Open the HTTP client for use in an async with block."""
        await self._http.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the HTTP client when leaving an async with block."""
        await self._http.__aexit__(exc_type, exc_value, traceback)
