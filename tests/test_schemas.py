from criterium.schemas import (
    ResearchSchemaArray,
    ResearchSchemaInteger,
    ResearchSchemaObject,
    ResearchSchemaString,
    to_structured_output_schema,
    to_validation_schema,
)


def make_nested_schema() -> ResearchSchemaObject:
    return ResearchSchemaObject(
        properties={
            "title": ResearchSchemaString(),
            "items": ResearchSchemaArray(
                items=ResearchSchemaObject(
                    properties={
                        "position": ResearchSchemaInteger(),
                    }
                )
            ),
        }
    )


def test_research_schema_contains_only_user_facing_criteria() -> None:
    dumped = make_nested_schema().model_dump(exclude_none=True)

    assert "required" not in str(dumped)
    assert "nullable" not in str(dumped)


def test_structured_output_schema_requires_nullable_fields_recursively() -> None:
    dumped = to_structured_output_schema(make_nested_schema())

    assert dumped["required"] == ["title", "items"]
    assert dumped["properties"]["items"]["items"]["required"] == ["position"]
    assert dumped["properties"]["title"]["nullable"] is True
    assert dumped["properties"]["items"]["nullable"] is True
    assert dumped["properties"]["items"]["items"]["properties"]["position"]["nullable"] is True


def test_validation_schema_uses_standard_nullable_types() -> None:
    dumped = to_validation_schema(make_nested_schema())

    assert dumped["required"] == ["title", "items"]
    assert dumped["properties"]["title"]["type"] == ["string", "null"]
    assert dumped["properties"]["items"]["items"]["properties"]["position"]["type"] == ["integer", "null"]


def test_legacy_output_constraints_are_ignored() -> None:
    schema = ResearchSchemaObject(
        properties={"title": ResearchSchemaString()},
        required=["title"],
        nullable=True,
    )

    dumped = schema.model_dump(exclude_none=True)

    assert dumped == {
        "type": "object",
        "properties": {"title": {"type": "string"}},
    }
