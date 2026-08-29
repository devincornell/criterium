import typing
from pydantic import BaseModel
from . import models

# --- Schemas (Pydantic for I/O validation) ---

class ResearchSchemaDef(BaseModel):
    type: str
    description: str | None = None
    properties: dict[str, "ResearchSchemaDef"] | None = None
    items: typing.Optional["ResearchSchemaDef"] = None
    required: list[str] | None = None

class CollectionCreate(BaseModel):
    name: str
    extraction_prompt: str
    research_schema: models.ResearchSchema

class CollectionUpdate(BaseModel):
    name: str | None = None
    extraction_prompt: str | None = None
    research_schema: models.ResearchSchema | None = None

class CollectionResponse(BaseModel):
    id: int
    name: str
    extraction_prompt: str
    research_schema: models.ResearchSchema
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
