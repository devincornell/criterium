import dataclasses
from typing import Any

@dataclasses.dataclass
class ResearchSchema:
    type: str
    properties: dict[str, 'ResearchSchema'] | None = None

    def __post_init__(self):
        if self.properties:
            for k, v in self.properties.items():
                if isinstance(v, dict):
                    self.properties[k] = ResearchSchema(**v)

data = {"type": "object", "properties": {"a": {"type": "string"}}}
schema = ResearchSchema(**data)
print(schema)
