from pydantic import BaseModel
import dataclasses
import typing

@dataclasses.dataclass
class LLMSchema:
    type: str
    description: str | None = None
    properties: dict[str, "LLMSchema"] | None = None
    items: typing.Optional["LLMSchema"] = None
    required: list[str] | None = None

class CollectionCreate(BaseModel):
    name: str
    llm_schema: LLMSchema

schema = CollectionCreate(name="test", llm_schema={"type": "object", "properties": {"a": {"type": "string"}}})
print(schema)
