"""Validate the information-model examples published in the AuthZEN specification."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

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

MODELS: dict[str, type[BaseModel]] = {
    "Subject": Subject,
    "Resource": Resource,
    "Action": Action,
    "Context": Context,
    "Decision": Decision,
    "EvaluationRequest": EvaluationRequest,
    "EvaluationResponse": EvaluationResponse,
}
EXAMPLES = json.loads(
    Path(__file__).with_name("fixtures").joinpath("model_examples.json").read_text()
)["examples"]


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        pytest.param(MODELS[example["model"]], example["payload"], id=example["name"])
        for example in EXAMPLES
    ],
)
def test_specification_examples(model: type[BaseModel], payload: JsonObject) -> None:
    original = model.model_validate_json(json.dumps(payload))

    assert model.model_validate(payload) == original
    assert json.loads(original.model_dump_json(exclude_defaults=True)) == payload
    assert model.model_validate_json(original.model_dump_json()) == original
