from criterium.schemas import (
    ResearchSchemaArray,
    ResearchSchemaInteger,
    ResearchSchemaObject,
    ResearchSchemaString,
)


def test_research_schema_computes_required_fields_recursively() -> None:
    schema = ResearchSchemaObject(
        properties={
            "title": ResearchSchemaString(is_required=True),
            "items": ResearchSchemaArray(
                items=ResearchSchemaObject(
                    properties={
                        "position": ResearchSchemaInteger(is_required=True),
                    }
                )
            ),
        }
    )

    dumped = schema.model_dump(exclude_none=True)

    assert dumped["required"] == ["title"]
    assert dumped["properties"]["items"]["items"]["required"] == ["position"]
    assert "is_required" not in str(dumped)


def test_explicit_required_fields_are_preserved_without_duplicates() -> None:
    schema = ResearchSchemaObject(
        properties={"title": ResearchSchemaString(is_required=True)},
        required=["title"],
    )

    assert schema.required == ["title"]
