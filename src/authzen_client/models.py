"""Models for AuthZEN single access evaluations.

Unknown protocol fields are ignored. Keys inside properties and context are kept.
Optional objects default to empty objects. Use ``exclude_defaults=True`` when
dumping to omit them.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    RootModel,
    ValidationInfo,
    field_validator,
)

from authzen_client.types import JsonObject

_JSON_CONFIG = ConfigDict(strict=True, allow_inf_nan=False)
_MODEL_CONFIG: ConfigDict = {**_JSON_CONFIG, "extra": "ignore"}


class Context(RootModel[JsonObject]):
    """Environment or enforcement data serialized as a plain JSON object.

    Access the underlying dictionary through ``root``. The PEP and PDP define
    the meaning of its keys.
    """

    model_config = _JSON_CONFIG

    root: JsonObject = Field(default_factory=dict)


class Subject(BaseModel):
    """A user or machine principal whose id is scoped to its type."""

    model_config = _MODEL_CONFIG

    type: str
    id: str
    properties: JsonObject = Field(default_factory=dict)


class Resource(BaseModel):
    """A target resource whose id is scoped to its type."""

    model_config = _MODEL_CONFIG

    type: str
    id: str
    properties: JsonObject = Field(default_factory=dict)


class Action(BaseModel):
    """An operation the subject wants to perform, such as read or update."""

    model_config = _MODEL_CONFIG

    name: str
    properties: JsonObject = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    """A single access check for a subject, action, and resource."""

    model_config = _MODEL_CONFIG

    subject: Subject
    action: Action
    resource: Resource
    context: Context = Field(default_factory=Context)


class Decision(BaseModel):
    """The PDP's allow or deny result and optional enforcement context.

    A false decision is a regular denial result. The PEP interprets any
    additional information in context when enforcing the decision.
    """

    model_config = _MODEL_CONFIG

    decision: bool
    context: Context = Field(default_factory=Context)


# The single-evaluation response has the same structure as a Decision.
EvaluationResponse = Decision


class PDPMetadata(BaseModel):
    """Unsigned PDP metadata for locating the single-evaluation endpoint."""

    model_config = _MODEL_CONFIG

    policy_decision_point: str
    access_evaluation_endpoint: str

    @field_validator("policy_decision_point", "access_evaluation_endpoint")
    @classmethod
    def https_url(cls, value: str, info: ValidationInfo) -> str:
        url = HttpUrl(value)
        if url.scheme != "https" or url.fragment:
            raise ValueError("PDP metadata URLs must use HTTPS without a fragment.")
        if info.field_name == "policy_decision_point" and url.query:
            raise ValueError("The PDP identifier must not contain a query.")
        return value
