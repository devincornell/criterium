import dataclasses

@dataclasses.dataclass
class ResearchSchema:
    type: str
    properties: dict | None = None

schema = ResearchSchema(type="object", properties={"a": {"type": "string"}})
print(dataclasses.asdict(schema))
