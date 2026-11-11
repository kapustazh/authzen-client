"""Synchronous HTTPS client for AuthZEN single access evaluations."""

from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx
from pydantic import ValidationError

from authzen_client.exceptions import ProtocolError, TransportError
from authzen_client.models import EvaluationRequest, EvaluationResponse


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
        try:
            url = httpx.URL(base_url)
        except httpx.InvalidURL as exc:
            raise ValueError("base_url must be a valid HTTPS URL.") from exc
        if url.scheme != "https" or not url.host or url.query or url.fragment:
            raise ValueError(
                "base_url must be an absolute HTTPS URL without a query or fragment."
            )

        request_headers = httpx.Headers(headers)
        request_headers.setdefault("Accept", "application/json")
        request_headers["Content-Type"] = "application/json"

        self._http = httpx.Client(
            base_url=url,
            auth=auth,
            transport=transport,
            headers=request_headers,
        )

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Evaluate an access request, returning both allow and deny decisions.

        Raises:
            TransportError: A PDP or token request could not be completed.
            ProtocolError: Authentication failed or the PDP response was invalid.
        """
        payload = request.model_dump(mode="json", exclude_defaults=True)
        try:
            response = self._http.post("/access/v1/evaluation", json=payload)
        except httpx.DecodingError as exc:
            raise ProtocolError("The PDP response could not be decoded.") from exc
        except httpx.RequestError as exc:
            raise TransportError("The AuthZEN evaluation request failed.") from exc
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise ProtocolError(
                "HTTP request or authentication failed.",
                response=getattr(exc, "response", None),
            ) from exc

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
            return EvaluationResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise ProtocolError(
                "The PDP returned an invalid evaluation response.", response=response
            ) from exc

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
