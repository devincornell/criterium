import typing
from pydantic import BaseModel, Field, model_validator
from typing import Annotated, Literal

# --- Schemas (Pydantic for I/O validation) ---

class SchemaBase(BaseModel):
    description: str | None = None
    is_required: bool = Field(default=False, exclude=True) # Exclude from JSON dump

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
    def compute_required(self):
        if self.properties:
            reqs = [k for k, v in self.properties.items() if getattr(v, "is_required", False)]
            if reqs:
                if self.required is None:
                    self.required = []
                self.required.extend(x for x in reqs if x not in self.required)
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

import datetime

class CollectionResponse(BaseModel):
    id: int
    name: str
    extraction_prompt: str
    research_schema: ResearchSchemaDef
    created_at: datetime.datetime

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
    created_at: datetime.datetime
