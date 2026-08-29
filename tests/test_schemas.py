from criterium.schemas import (
    ResearchSchemaArray,
    ResearchSchemaInteger,
    ResearchSchemaObject,
    ResearchSchemaString,
)


def test_research_schema_computes_required_fields_recursively() -> None:
    schema = ResearchSchemaObject(
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

    dumped = schema.model_dump(exclude_none=True)

    assert dumped["required"] == ["title", "items"]
    assert dumped["properties"]["items"]["items"]["required"] == ["position"]
    assert dumped["properties"]["title"]["nullable"] is True
    assert dumped["properties"]["items"]["nullable"] is True
    assert dumped["properties"]["items"]["items"]["properties"]["position"]["nullable"] is True


def test_partial_required_list_is_normalized_to_all_properties() -> None:
    schema = ResearchSchemaObject(
        properties={
            "title": ResearchSchemaString(),
            "year": ResearchSchemaInteger(),
        },
        required=["title"],
    )

    assert schema.required == ["title", "year"]
