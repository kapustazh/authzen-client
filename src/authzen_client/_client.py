"""Shared protocol validation and endpoint state for both clients."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import httpx2
from pydantic import BaseModel, ValidationError

from authzen_client.exceptions import ProtocolError, TransportError
from authzen_client.models import (
    PageRequest,
    PageResponse,
    PDPMetadata,
    SearchRequest,
)
from authzen_client.settings import Endpoints

try:
    from authlib.common.errors import AuthlibBaseError
except ImportError:
    _AUTH_ERRORS: tuple[type[Exception], ...] = ()
else:
    _AUTH_ERRORS = (AuthlibBaseError,)

type Endpoint = Literal["evaluation", "evaluations", "subjects", "resources", "actions"]

_METADATA_FIELDS = {
    "evaluation": "access_evaluation_endpoint",
    "evaluations": "access_evaluations_endpoint",
    "subjects": "search_subject_endpoint",
    "resources": "search_resource_endpoint",
    "actions": "search_action_endpoint",
}


def _with_base(base: httpx2.URL, value: str) -> str:
    """Join an endpoint onto the PDP base, keeping a base path such as /tenant."""
    if httpx2.URL(value).is_absolute_url:
        return value
    prefix = str(base)
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix + value.lstrip("/")


def _base_url(value: str) -> httpx2.URL:
    try:
        url = httpx2.URL(value)
    except httpx2.InvalidURL as exc:
        raise ValueError("base_url must be a valid HTTPS URL.") from exc
    if url.scheme != "https" or not url.host or url.query or url.fragment:
        raise ValueError("base_url must be an HTTPS URL without query or fragment.")
    return url


@contextmanager
def _request_errors() -> Generator[None, None, None]:
    try:
        yield
    except httpx2.DecodingError as exc:
        raise ProtocolError("The PDP response could not be decoded.") from exc
    except httpx2.RequestError as exc:
        raise TransportError("The AuthZEN HTTP request failed.") from exc
    except _AUTH_ERRORS as exc:
        raise ProtocolError("OAuth authentication failed.") from exc
    except (httpx2.HTTPError, ValueError, AttributeError) as exc:
        raise ProtocolError(
            "HTTP request or authentication failed.",
            response=getattr(exc, "response", None),
        ) from exc


def _response_model[T: BaseModel](response: httpx2.Response, model: type[T]) -> T:
    if response.status_code != 200:
        raise ProtocolError(
            f"The PDP returned HTTP {response.status_code}, expected 200.",
            response=response,
        )
    media_type = response.headers.get("content-type", "").partition(";")[0]
    if media_type.strip().lower() != "application/json":
        raise ProtocolError(
            "The PDP response Content-Type must be application/json.", response=response
        )
    try:
        return model.model_validate_json(response.content)
    except ValidationError as exc:
        raise ProtocolError(
            "The PDP returned an invalid response.", response=response
        ) from exc


class _Omitted:
    """Constructor argument the caller did not pass."""


_OMITTED = _Omitted()


def _timeout(
    value: httpx2.Timeout | float | None | _Omitted,
) -> httpx2.Timeout | float | None:
    if isinstance(value, _Omitted):
        return 5.0
    return value


def _reject_borrowed_settings(
    *,
    auth: object | None,
    transport: object | None,
    limits: object | None,
    timeout: object,
) -> None:
    """Name each setting that must be configured on a caller-owned HTTP client."""
    conflicts: list[str] = []
    if auth is not None:
        conflicts.append("auth")
    if transport is not None:
        conflicts.append("transport")
    if limits is not None:
        conflicts.append("limits")
    if not isinstance(timeout, _Omitted):
        conflicts.append("timeout")
    if conflicts:
        raise ValueError(
            f"Configure {', '.join(conflicts)} on the supplied http_client."
        )


def _page_state[T: SearchRequest](request: T) -> tuple[T, set[str]]:
    """Copy a search and record its token so later pages cannot mutate or loop."""
    seen: set[str] = set()
    token = None if request.page is None else request.page.token
    if token is not None and token != "":
        seen.add(token)
    return request.model_copy(deep=True), seen


def _next_request[T: SearchRequest](
    request: T, page: PageResponse | None, seen: set[str]
) -> T | None:
    if page is None or not page.next_token:
        return None
    if page.next_token in seen:
        raise ProtocolError("The PDP repeated a pagination token.")
    seen.add(page.next_token)
    next_page = (request.page or PageRequest()).model_copy(
        update={"token": page.next_token}
    )
    return request.model_copy(update={"page": next_page})


class _ClientBase:
    def __init__(
        self,
        base_url: str,
        headers: Mapping[str, str] | None,
        endpoints: Endpoints | None,
    ) -> None:
        self._base = _base_url(base_url)
        self._pdp_identifier = base_url
        self._endpoints = endpoints if endpoints is not None else Endpoints()
        self.metadata: PDPMetadata | None = None
        self._headers = httpx2.Headers(headers)
        self._headers.setdefault("Accept", "application/json")

    def _body_headers(self) -> httpx2.Headers:
        """JSON content type for requests that send a body."""
        headers = self._headers.copy()
        headers["Content-Type"] = "application/json"
        return headers

    def _url(self, endpoint: Endpoint) -> str:
        advertised = getattr(self.metadata, _METADATA_FIELDS[endpoint], None)
        fallback = getattr(self._endpoints, endpoint)
        chosen = advertised if advertised is not None else fallback
        return _with_base(self._base, str(chosen))

    def _metadata_url(self) -> str:
        url = urlsplit(self._pdp_identifier)
        return urlunsplit(
            (
                url.scheme,
                url.netloc,
                "/.well-known/authzen-configuration" + url.path,
                "",
                "",
            )
        )

    def _accept_metadata(self, response: httpx2.Response) -> PDPMetadata:
        metadata = _response_model(response, PDPMetadata)
        if metadata.policy_decision_point != self._pdp_identifier:
            raise ProtocolError(
                "The metadata PDP identifier does not match base_url.",
                response=response,
            )
        self.metadata = metadata
        return metadata
