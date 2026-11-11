"""Errors raised while communicating with an AuthZEN PDP."""

import httpx


class AuthZENError(Exception):
    """Base exception for AuthZEN client failures."""


class TransportError(AuthZENError):
    """The evaluation request failed at the HTTP transport layer."""


class ProtocolError(AuthZENError):
    """The PDP returned an HTTP error or an invalid AuthZEN response.

    The HTTP response is available through ``response`` when decoding succeeds.
    """

    def __init__(self, message: str, *, response: httpx.Response | None = None) -> None:
        self.response = response
        super().__init__(message)
