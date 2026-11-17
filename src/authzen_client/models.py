"""Models for AuthZEN single access evaluations.

Unknown protocol fields are ignored. Keys inside properties and context are kept.
Optional objects default to empty objects. Use ``exclude_defaults=True`` when
dumping to omit them.
"""

from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    RootModel,
    ValidationInfo,
    field_validator,
    model_validator,
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


class Evaluation(BaseModel):
    """A batch entry whose omitted entities inherit the request defaults."""

    model_config = _MODEL_CONFIG

    subject: Subject | None = None
    action: Action | None = None
    resource: Resource | None = None
    context: Context | None = None


class EvaluationsOptions(BaseModel):
    """Batch execution semantics and additional JSON options for the PDP."""

    model_config = {**_JSON_CONFIG, "extra": "allow"}
    # Pydantic requires this narrower annotation to validate extra JSON values.
    __pydantic_extra__: dict[str, JsonValue] = Field(  # ty: ignore[incompatible-mutable-override]
        init=False
    )

    evaluations_semantic: Literal[
        "execute_all", "deny_on_first_deny", "permit_on_first_permit"
    ] = "execute_all"


class EvaluationsRequest(Evaluation):
    """Batch evaluations with optional shared defaults and short-circuiting."""

    evaluations: list[Evaluation] = Field(default_factory=list)
    options: EvaluationsOptions = Field(default_factory=EvaluationsOptions)

    @model_validator(mode="after")
    def required_entities(self) -> Self:
        for evaluation in self.evaluations or [Evaluation()]:
            for name in ("subject", "action", "resource"):
                if getattr(evaluation, name) is None and getattr(self, name) is None:
                    raise ValueError(f"Each evaluation must provide or inherit {name}.")
        return self


class EvaluationsResponse(BaseModel):
    """Ordered batch decisions, or a single decision for the fallback request."""

    model_config = _MODEL_CONFIG

    evaluations: list[Decision] | None = None
    decision: bool | None = None
    context: Context = Field(default_factory=Context)

    @model_validator(mode="after")
    def has_result(self) -> Self:
        if self.evaluations is None and self.decision is None:
            raise ValueError("The response must contain evaluations or a decision.")
        return self


class PageRequest(BaseModel):
    """Opaque continuation token, result limit and PDP-specific page options."""

    model_config = _MODEL_CONFIG

    token: str | None = None
    limit: Annotated[int, Field(ge=0)] | None = None
    properties: JsonObject = Field(default_factory=dict)


class PageResponse(BaseModel):
    """Pagination metadata. An empty next_token marks the last page."""

    model_config = _MODEL_CONFIG

    next_token: str
    count: Annotated[int, Field(ge=0)] | None = None
    total: Annotated[int, Field(ge=0)] | None = None
    properties: JsonObject = Field(default_factory=dict)


class SubjectQuery(BaseModel):
    """Subject type and properties to search. The PDP ignores any supplied id."""

    model_config = _MODEL_CONFIG

    type: str
    id: str | None = None
    properties: JsonObject = Field(default_factory=dict)


class ResourceQuery(BaseModel):
    """Resource type and properties to search. The PDP ignores any supplied id."""

    model_config = _MODEL_CONFIG

    type: str
    id: str | None = None
    properties: JsonObject = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Context and pagination shared by the three search request models."""

    model_config = _MODEL_CONFIG

    context: Context = Field(default_factory=Context)
    page: PageRequest | None = None


class SubjectSearchRequest(SearchRequest):
    """Find subjects permitted to perform an action on a resource."""

    subject: SubjectQuery
    action: Action
    resource: Resource


class ResourceSearchRequest(SearchRequest):
    """Find resources a subject may access with the given action."""

    subject: Subject
    action: Action
    resource: ResourceQuery


class ActionSearchRequest(SearchRequest):
    """Find actions a subject may perform on a resource."""

    subject: Subject
    resource: Resource


class SearchResponse[T: Subject | Resource | Action](BaseModel):
    """A page of authorized entities and optional response context."""

    model_config = _MODEL_CONFIG

    results: list[T]
    page: PageResponse | None = None
    context: Context = Field(default_factory=Context)


SubjectSearchResponse = SearchResponse[Subject]
ResourceSearchResponse = SearchResponse[Resource]
ActionSearchResponse = SearchResponse[Action]


class PDPMetadata(BaseModel):
    """Unsigned PDP metadata for locating the single-evaluation endpoint."""

    model_config = _MODEL_CONFIG

    policy_decision_point: str
    access_evaluation_endpoint: str
    access_evaluations_endpoint: str | None = None
    search_subject_endpoint: str | None = None
    search_resource_endpoint: str | None = None
    search_action_endpoint: str | None = None
    supported_capabilities: list[str] = Field(default_factory=list)

    @field_validator(
        "policy_decision_point",
        "access_evaluation_endpoint",
        "access_evaluations_endpoint",
        "search_subject_endpoint",
        "search_resource_endpoint",
        "search_action_endpoint",
    )
    @classmethod
    def https_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        url = HttpUrl(value)
        if url.scheme != "https" or url.fragment not in (None, ""):
            raise ValueError("PDP metadata URLs must use HTTPS without a fragment.")
        if info.field_name == "policy_decision_point" and url.query not in (None, ""):
            raise ValueError("The PDP identifier must not contain a query.")
        return value
