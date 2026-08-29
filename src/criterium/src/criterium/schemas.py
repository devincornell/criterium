import typing
from pydantic import BaseModel, Field
from typing import Annotated, Literal
from . import models

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
    required: list[str] | None = None

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

class CollectionResponse(BaseModel):
    id: int
    name: str
    extraction_prompt: str
    research_schema: ResearchSchemaDef
    created_at: str

class ProductCreate(BaseModel):
    product_info: str

class ProductExtractResult(BaseModel):
    source_url: str
    status: str
    product_id: int | None = None
    error: str | None = None

class ProductResponse(BaseModel):
    id: int
    collection_id: int
    name: str
    source_url: str
    raw_source_text: str
    extracted_data: dict[str, typing.Any] | None
    created_at: str
