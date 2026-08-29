import typing
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Annotated, Literal

# --- Schemas (Pydantic for I/O validation) ---

class SchemaBase(BaseModel):
    description: str | None = None
    nullable: bool | None = None

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
    required: list[str] | None = None

    @model_validator(mode='after')
    def require_all_properties(self):
        self.required = list(self.properties) or None
        for property_schema in self.properties.values():
            property_schema.nullable = True
        return self

# Discriminated union allows Pydantic to automatically resolve the correct subclass based on the "type" field
ResearchSchemaDef = Annotated[
    ResearchSchemaString | ResearchSchemaInteger | ResearchSchemaNumber | ResearchSchemaBoolean | ResearchSchemaArray | ResearchSchemaObject,
    Field(discriminator="type")
]

class CollectionCreate(BaseModel):
    name: str
    extraction_prompt: str
    research_schema: ResearchSchemaDef

class CollectionUpdate(BaseModel):
    name: str | None = None
    extraction_prompt: str | None = None
    research_schema: ResearchSchemaDef | None = None

class CollectionSuggestionRequest(BaseModel):
    description: str = Field(min_length=10, max_length=4000)

class CollectionSuggestionResponse(BaseModel):
    name: str
    extraction_prompt: str
    research_schema: ResearchSchemaObject

import datetime

class CollectionResponse(BaseModel):
    id: int
    name: str
    extraction_prompt: str
    research_schema: ResearchSchemaDef
    created_at: datetime.datetime

class ProductCreate(BaseModel):
    product_info: str

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
