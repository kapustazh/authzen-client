import json

import pytest
from pydantic import BaseModel, ValidationError

from authzen_client import (
    Action,
    Context,
    Decision,
    EvaluationRequest,
    EvaluationResponse,
    JsonObject,
    Resource,
    Subject,
)

REQUEST = {
    "subject": {"type": "user", "id": "alice@example.com"},
    "action": {"name": "can_read"},
    "resource": {"type": "document", "id": "123"},
}
ATTRIBUTES: JsonObject = {
    "department": "Sales",
    "roles": ["reader", "editor"],
    "metadata": {"enabled": True, "count": 2, "score": 1.5, "missing": None},
    "empty": {},
    "label": "test 1, 2, 3 :D",
}


@pytest.mark.parametrize("model", [Subject, Resource, Action])
def test_properties_preserve_arbitrary_json(model: type[BaseModel]) -> None:
    payload = {"type": "example", "id": "123", "name": "read"}
    instance = model.model_validate({**payload, "properties": ATTRIBUTES})

    assert json.loads(instance.model_dump_json())["properties"] == ATTRIBUTES
    assert model.model_validate_json(instance.model_dump_json()) == instance


@pytest.mark.parametrize(
    ("model", "payload", "required"),
    [
        (Subject, REQUEST["subject"], "type"),
        (Subject, REQUEST["subject"], "id"),
        (Resource, REQUEST["resource"], "type"),
        (Resource, REQUEST["resource"], "id"),
        (Action, REQUEST["action"], "name"),
        (EvaluationRequest, REQUEST, "subject"),
        (EvaluationRequest, REQUEST, "action"),
        (EvaluationRequest, REQUEST, "resource"),
        (Decision, {"decision": True}, "decision"),
    ],
)
def test_required_fields(
    model: type[BaseModel], payload: dict[str, object], required: str
) -> None:
    incomplete = payload.copy()
    del incomplete[required]

    with pytest.raises(ValidationError):
        model.model_validate(incomplete)


@pytest.mark.parametrize("value", ["false", 1, None])
def test_decision_requires_a_boolean(value: object) -> None:
    with pytest.raises(ValidationError):
        EvaluationResponse.model_validate_json(json.dumps({"decision": value}))


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Subject, {"type": 1, "id": "alice"}),
        (Subject, {"type": "user", "id": None}),
        (Resource, {"type": "document", "id": 123}),
        (Action, {"name": True}),
        (Subject, {**REQUEST["subject"], "properties": None}),
        (Resource, {**REQUEST["resource"], "properties": []}),
        (Action, {"name": "read", "properties": "invalid"}),
        (EvaluationRequest, {**REQUEST, "context": None}),
        (EvaluationRequest, {**REQUEST, "subject": "alice"}),
        (EvaluationResponse, {"decision": True, "context": []}),
        (EvaluationResponse, {"decision": True, "context": None}),
        (Context, []),
        (Context, None),
    ],
)
def test_invalid_field_types(model: type[BaseModel], payload: object) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize("value", [object(), float("nan")])
def test_open_objects_reject_non_json_values(value: object) -> None:
    with pytest.raises(ValidationError):
        Context.model_validate({"nested": {"invalid": value}})

    with pytest.raises(ValidationError):
        Subject.model_validate({**REQUEST["subject"], "properties": {"bad": value}})


def test_unknown_protocol_fields_are_ignored() -> None:
    request = EvaluationRequest.model_validate(
        {
            **REQUEST,
            "future_field": "ignored",
            "subject": {**REQUEST["subject"], "future_field": "ignored"},
            "action": {**REQUEST["action"], "future_field": "ignored"},
            "resource": {**REQUEST["resource"], "future_field": "ignored"},
        }
    )
    response = EvaluationResponse.model_validate(
        {"decision": False, "future_field": "ignored", "context": ATTRIBUTES}
    )

    assert "future_field" not in request.model_dump()
    assert "future_field" not in request.subject.model_dump()
    assert "future_field" not in request.action.model_dump()
    assert "future_field" not in request.resource.model_dump()
    assert "future_field" not in response.model_dump()
    assert response.context.root == ATTRIBUTES


def test_context_preserves_keys_that_match_model_attributes() -> None:
    payload = {"root": {"nested": True}, "model_config": "opaque", "decision": None}
    response = EvaluationResponse.model_validate(
        {"decision": False, "context": payload}
    )

    assert response.context.root == payload
    assert json.loads(response.model_dump_json())["context"] == payload


def test_minimal_request_serialization() -> None:
    request = EvaluationRequest.model_validate(REQUEST)

    assert json.loads(request.model_dump_json(exclude_defaults=True)) == REQUEST


def test_default_objects_are_independent() -> None:
    first = EvaluationRequest.model_validate(REQUEST)
    second = EvaluationRequest.model_validate(REQUEST)
    first.subject.properties["department"] = "Sales"
    first.context.root["location"] = "Berlin"

    assert second.subject.properties == {}
    assert second.context.root == {}
