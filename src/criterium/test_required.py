from pydantic import BaseModel, Field
from typing import Annotated, Literal

class SchemaBase(BaseModel):
    description: str | None = None
    required: bool | None = None

class ResearchSchemaString(SchemaBase):
    type: Literal["string"] = "string"

class ResearchSchemaObject(SchemaBase):
    type: Literal["object"] = "object"
    properties: dict[str, "ResearchSchemaDef"] = Field(default_factory=dict)
    
    # We will build the actual 'required' list dynamically during serialization
    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.properties:
            req = [k for k, v in self.properties.items() if getattr(v, "required", False)]
            if req:
                data["required"] = req
        return data

ResearchSchemaDef = Annotated[
    ResearchSchemaString | ResearchSchemaObject,
    Field(discriminator="type")
]

obj = ResearchSchemaObject(
    properties={
        "title": ResearchSchemaString(required=True),
        "subtitle": ResearchSchemaString()
    }
)
print(obj.model_dump(exclude_none=True))
