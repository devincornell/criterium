from pydantic import BaseModel, Field, model_validator
from typing import Annotated, Literal

class SchemaBase(BaseModel):
    description: str | None = None
    is_required: bool = Field(default=False, exclude=True) # Exclude from JSON output

class ResearchSchemaString(SchemaBase):
    type: Literal["string"] = "string"

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

ResearchSchemaDef = Annotated[
    ResearchSchemaString | ResearchSchemaObject,
    Field(discriminator="type")
]

obj = ResearchSchemaObject(
    properties={
        "title": ResearchSchemaString(is_required=True),
        "subtitle": ResearchSchemaString()
    }
)
print(obj.model_dump(exclude_none=True))
