import typing
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Annotated, Literal

# --- Schemas (Pydantic for I/O validation) ---

class SchemaBase(BaseModel):
    description: str | None = None

class ResearchSchemaString(SchemaBase):
    type: Literal["string"] = "string"

class ResearchSchemaInteger(SchemaBase):
    type: Literal["integer"] = "integer"

class ResearchSchemaNumber(SchemaBase):
    type: Literal["number"] = "number"

class ResearchSchemaBoolean(SchemaBase):
    type: Literal["boolean"] = "boolean"

class ResearchSchemaArray(SchemaBase):
    type: Literal["array"] = "array"
    items: "ResearchSchemaDef"

class ResearchSchemaObject(SchemaBase):
    type: Literal["object"] = "object"
    properties: dict[str, "ResearchSchemaDef"] = Field(default_factory=dict)

# Discriminated union allows Pydantic to automatically resolve the correct subclass based on the "type" field
ResearchSchemaDef = Annotated[
    ResearchSchemaString | ResearchSchemaInteger | ResearchSchemaNumber | ResearchSchemaBoolean | ResearchSchemaArray | ResearchSchemaObject,
    Field(discriminator="type")
]


def to_structured_output_schema(research_schema: ResearchSchemaDef) -> dict[str, typing.Any]:
    schema = research_schema.model_dump(exclude_none=True)
    _add_output_constraints(schema, use_nullable_keyword=True)
    return schema


def to_validation_schema(research_schema: ResearchSchemaDef) -> dict[str, typing.Any]:
    schema = research_schema.model_dump(exclude_none=True)
    _add_output_constraints(schema, use_nullable_keyword=False)
    return schema


def _add_output_constraints(
    schema: dict[str, typing.Any],
    *,
    use_nullable_keyword: bool,
    nullable: bool = False,
) -> None:
    if nullable:
        if use_nullable_keyword:
            schema["nullable"] = True
        else:
            schema["type"] = [schema["type"], "null"]

    properties = schema.get("properties", {})
    if properties:
        schema["required"] = list(properties)
    for property_schema in properties.values():
        _add_output_constraints(
            property_schema,
            use_nullable_keyword=use_nullable_keyword,
            nullable=True,
        )

    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        _add_output_constraints(
            item_schema,
            use_nullable_keyword=use_nullable_keyword,
        )

class CollectionCreate(BaseModel):
    name: str
    research_instructions: str | None = None
    research_schema: ResearchSchemaDef

class CollectionUpdate(BaseModel):
    name: str | None = None
    research_instructions: str | None = None
    research_schema: ResearchSchemaDef | None = None

class CollectionSuggestionRequest(BaseModel):
    description: str = Field(min_length=10, max_length=4000)

class CollectionSuggestionResponse(BaseModel):
    name: str
    research_instructions: str | None = None
    research_schema: ResearchSchemaObject

import datetime

class CollectionResponse(BaseModel):
    id: int
    name: str
    research_instructions: str | None
    research_schema: ResearchSchemaDef
    created_at: datetime.datetime

class ProductCreate(BaseModel):
    product_info: str = Field(min_length=1, max_length=2000)

class ResearchJobsCreate(BaseModel):
    product_infos: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def normalize_product_infos(self):
        normalized = [product_info.strip() for product_info in self.product_infos]
        if any(not product_info for product_info in normalized):
            raise ValueError("Product names must not be empty.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Product names must be unique within a batch.")
        self.product_infos = normalized
        return self

class ResearchJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    product_info: str
    status: Literal["queued", "running", "succeeded", "failed"]
    stage: str | None
    product_id: int | None
    error_message: str | None
    attempt_count: int
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None

class ResearchReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    url: str
    title: str | None
    provider: str
    created_at: datetime.datetime

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    name: str
    source_url: str
    raw_source_text: str
    extracted_data: dict[str, typing.Any] | None
    created_at: datetime.datetime
    references: list[ResearchReferenceResponse] = Field(default_factory=list)
