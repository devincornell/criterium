from pydantic import BaseModel, Field
from typing import Annotated, Literal

class SchemaBase(BaseModel):
    description: str | None = None

class ResearchSchemaString(SchemaBase):
    type: Literal["string"] = "string"

class ResearchSchemaInteger(SchemaBase):
    type: Literal["integer"] = "integer"

class ResearchSchemaArray(SchemaBase):
    type: Literal["array"] = "array"
    items: "ResearchSchemaDef"

class ResearchSchemaObject(SchemaBase):
    type: Literal["object"] = "object"
    properties: dict[str, "ResearchSchemaDef"] | None = None
    required: list[str] | None = None

ResearchSchemaDef = Annotated[
    ResearchSchemaString | ResearchSchemaInteger | ResearchSchemaArray | ResearchSchemaObject,
    Field(discriminator="type")
]

class CollectionCreate(BaseModel):
    name: str
    schema_def: ResearchSchemaDef

obj = CollectionCreate(
    name="Test",
    schema_def=ResearchSchemaObject(
        properties={
            "books": ResearchSchemaArray(
                items=ResearchSchemaString()
            )
        }
    )
)
print(obj.model_dump(exclude_none=True))
