"""Shared protocol validation and endpoint state for both clients."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import httpx2
from pydantic import BaseModel, ValidationError

from authzen_client.exceptions import ProtocolError, TransportError
from authzen_client.models import PDPMetadata
from authzen_client.settings import Endpoints

try:
    from authlib.common.errors import AuthlibBaseError
except ImportError:
    _AUTH_ERRORS: tuple[type[Exception], ...] = ()
else:
    _AUTH_ERRORS = (AuthlibBaseError,)

type Endpoint = Literal["evaluation"]

_METADATA_FIELDS = {
    "evaluation": "access_evaluation_endpoint",
}


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


class _ClientBase:
    def __init__(
        self,
        base_url: str,
        headers: Mapping[str, str] | None,
        endpoints: Endpoints | None,
    ) -> None:
        self._base = _base_url(base_url)
        self._pdp_identifier = base_url
        self._endpoints = endpoints or Endpoints()
        self.metadata: PDPMetadata | None = None
        self._headers = httpx2.Headers(headers)
        self._headers.setdefault("Accept", "application/json")
        self._headers["Content-Type"] = "application/json"

    def _url(self, endpoint: Endpoint) -> str:
        advertised = getattr(self.metadata, _METADATA_FIELDS[endpoint], None)
        value = str(advertised or getattr(self._endpoints, endpoint))
        if httpx2.URL(value).is_absolute_url:
            return str(value)
        base = str(self._base)
        return base + value.lstrip("/") if base.endswith("/") else base + value

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
