import json
from types import SimpleNamespace

import pytest

from criterium.schema_generation import (
    GeminiCollectionSuggester,
    _SuggestedField,
    _to_research_schema,
)
SUGGESTION = {
    "name": "Compact Electric Vehicles",
    "extraction_prompt": "Extract comparable vehicle specifications.",
    "fields": [
        {
            "name": "model",
            "field_type": "string",
            "description": "Vehicle model name.",
        },
        {
            "name": "range_miles",
            "field_type": "integer",
            "description": "EPA range in miles.",
        },
    ],
}


class FakeModels:
    def __init__(self, response) -> None:
        self.response = response
        self.request = None

    def generate_content(self, **kwargs):
        self.request = kwargs
        return self.response


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(parsed=SUGGESTION, text=None),
        SimpleNamespace(parsed=None, text=json.dumps(SUGGESTION)),
    ],
)
def test_gemini_suggester_validates_sdk_and_json_responses(response) -> None:
    models = FakeModels(response)
    suggester = GeminiCollectionSuggester(SimpleNamespace(models=models))

    result = suggester.suggest("Compare compact electric vehicles for city driving")

    assert result.name == "Compact Electric Vehicles"
    assert result.research_schema.required == ["model", "range_miles"]
    assert result.research_schema.properties["range_miles"].nullable is True
    assert models.request["model"] == "gemini-3.7-flash"
    response_schema = models.request["config"].response_schema.model_json_schema()
    assert "additionalProperties" not in json.dumps(response_schema)
    for name, definition in response_schema.get("$defs", {}).items():
        assert f"#/$defs/{name}" not in json.dumps(definition)


def test_gemini_suggester_rejects_empty_response() -> None:
    models = FakeModels(SimpleNamespace(parsed=None, text=None))
    suggester = GeminiCollectionSuggester(SimpleNamespace(models=models))

    with pytest.raises(ValueError, match="no collection suggestion"):
        suggester.suggest("Compare compact electric vehicles for city driving")


@pytest.mark.parametrize(
    ("field_type", "expected_type"),
    [
        ("string", "string"),
        ("integer", "integer"),
        ("number", "number"),
        ("boolean", "boolean"),
    ],
)
def test_scalar_suggested_fields_convert_to_research_schema(
    field_type: str,
    expected_type: str,
) -> None:
    field = _SuggestedField.model_validate(
        {
            "name": "value",
            "field_type": field_type,
            "description": "A comparable value.",
        }
    )

    assert _to_research_schema(field).type == expected_type


def test_nested_suggested_fields_convert_to_research_schema() -> None:
    field = _SuggestedField.model_validate({
        "name": "features",
        "field_type": "array",
        "description": "Feature details.",
        "items": {
            "field_type": "object",
            "description": "A feature.",
            "properties": [{
                "name": "name",
                "field_type": "string",
                "description": "A feature name.",
            }],
        },
    })

    schema = _to_research_schema(field).model_dump(exclude_none=True)

    assert schema["items"]["required"] == ["name"]
    assert schema["items"]["properties"]["name"]["type"] == "string"


def test_array_suggestion_requires_item_schema() -> None:
    field = _SuggestedField(
        name="features",
        field_type="array",
        description="Feature names.",
    )

    with pytest.raises(ValueError, match="has no item schema"):
        _to_research_schema(field)
