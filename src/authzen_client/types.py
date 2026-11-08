"""Shared JSON types for AuthZEN properties and context."""

from pydantic import JsonValue

type JsonObject = dict[str, JsonValue]
