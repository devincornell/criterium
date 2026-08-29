import dataclasses
import typing

@dataclasses.dataclass(frozen=True)
class ResearchSchema:
    type: str
    description: str | None = None
    properties: dict[str, 'ResearchSchema'] | None = None
    items: typing.Optional['ResearchSchema'] = None
    required: list[str] | None = None
    is_required: bool = False

data = {
    "type": "object",
    "properties": {
        "title": {"type": "string"}
    }
}
schema = ResearchSchema(**data)
print(type(schema.properties["title"]))
