"""Errors raised while communicating with an AuthZEN PDP."""

import httpx2


class AuthZENError(Exception):
    """Base exception for AuthZEN client failures."""


class TransportError(AuthZENError):
    """A request to the PDP or token service failed at the HTTP transport layer."""


class ProtocolError(AuthZENError):
    """An HTTP or response error from the PDP or token service.

    The ``response`` attribute contains the HTTP response when available.
    """

    def __init__(
        self, message: str, *, response: httpx2.Response | None = None
    ) -> None:
        self.response = response
        super().__init__(message)
