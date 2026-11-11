"""Synchronous HTTPS client for AuthZEN single access evaluations."""

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
        transport: Optional HTTPX transport for testing or custom connections.
    """

    def __init__(
        self, *, base_url: str, transport: httpx.BaseTransport | None = None
    ) -> None:
        try:
            url = httpx.URL(base_url)
        except httpx.InvalidURL as exc:
            raise ValueError("base_url must be a valid HTTPS URL.") from exc
        if url.scheme != "https" or not url.host or url.query or url.fragment:
            raise ValueError(
                "base_url must be an absolute HTTPS URL without a query or fragment."
            )

        self._http = httpx.Client(
            base_url=url,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Evaluate an access request, returning both allow and deny decisions.

        Raises:
            TransportError: The HTTP request could not be completed.
            ProtocolError: The PDP returned an HTTP error or invalid response.
        """
        payload = request.model_dump(mode="json", exclude_defaults=True)
        try:
            response = self._http.post("/access/v1/evaluation", json=payload)
        except httpx.DecodingError as exc:
            raise ProtocolError("The PDP response could not be decoded.") from exc
        except httpx.RequestError as exc:
            raise TransportError("The AuthZEN evaluation request failed.") from exc

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
