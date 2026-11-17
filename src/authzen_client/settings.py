"""Per-client endpoint defaults from the AuthZEN HTTPS binding."""

import httpx2
from pydantic import BaseModel, ConfigDict, field_validator


class Endpoints(BaseModel):
    """Fallback endpoint paths or HTTPS URLs, overridden by discovery."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    evaluation: str = "/access/v1/evaluation"
    evaluations: str = "/access/v1/evaluations"
    subjects: str = "/access/v1/search/subject"
    resources: str = "/access/v1/search/resource"
    actions: str = "/access/v1/search/action"

    @field_validator("*")
    @classmethod
    def endpoint_url(cls, value: str) -> str:
        url = httpx2.URL(value)
        if url.fragment or value.startswith("//"):
            raise ValueError(
                "Endpoints must not contain a fragment or authority-only URL."
            )
        if url.is_absolute_url:
            if url.scheme != "https" or not url.host:
                raise ValueError("Absolute endpoints must use HTTPS.")
        elif not value.startswith("/"):
            raise ValueError("Relative endpoints must start with /.")
        return value
