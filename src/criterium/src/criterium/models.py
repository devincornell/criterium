import dataclasses
import datetime
import typing
import sqlalchemy

@dataclasses.dataclass(frozen=True)
class ResearchSchema:
    type: str
    description: str | None = None
    properties: dict[str, 'ResearchSchema'] | None = None
    items: typing.Optional['ResearchSchema'] = None
    required: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, typing.Any]) -> typing.Self:
        properties = None
        if data.get("properties"):
            properties = {k: cls.from_dict(v) for k, v in data["properties"].items()}
        
        items = None
        if data.get("items"):
            items = cls.from_dict(data["items"])

        return cls(
            type=str(data["type"]),
            description=str(data["description"]) if "description" in data else None,
            properties=properties,
            items=items,
            required=list(data["required"]) if "required" in data else None
        )

    def to_dict(self) -> dict[str, typing.Any]:
        res: dict[str, typing.Any] = {"type": self.type}
        if self.description is not None:
            res["description"] = self.description
        if self.properties is not None:
            res["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.items is not None:
            res["items"] = self.items.to_dict()
        if self.required is not None:
            res["required"] = self.required
        return res

@dataclasses.dataclass(frozen=True)
class ResearchCollection:
    id: int
    name: str
    extraction_prompt: str
    research_schema: ResearchSchema
    created_at: datetime.datetime

    @classmethod
    def from_dict(cls, data: dict[str, typing.Any]) -> typing.Self:
        dt = datetime.datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            extraction_prompt=str(data["extraction_prompt"]),
            research_schema=ResearchSchema.from_dict(data["research_schema"]),
            created_at=dt
        )

    @classmethod
    def from_row(cls, row: sqlalchemy.Row) -> typing.Self:
        return cls(
            id=row._mapping["id"],
            name=row._mapping["name"],
            extraction_prompt=row._mapping["extraction_prompt"],
            research_schema=ResearchSchema.from_dict(row._mapping["research_schema"]),
            created_at=row._mapping["created_at"]
        )

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "id": self.id,
            "name": self.name,
            "extraction_prompt": self.extraction_prompt,
            "research_schema": self.research_schema.to_dict(),
            "created_at": self.created_at.isoformat()
        }

class ResearchCollectionList(list[ResearchCollection]):
    @classmethod
    def from_rows(cls, rows: typing.Iterable[sqlalchemy.Row]) -> typing.Self:
        return cls([ResearchCollection.from_row(r) for r in rows])

    def to_dict_list(self) -> list[dict[str, typing.Any]]:
        return [c.to_dict() for c in self]

@dataclasses.dataclass(frozen=True)
class Product:
    id: int
    collection_id: int
    name: str
    source_url: str
    raw_source_text: str
    extracted_data: dict[str, typing.Any] | None
    created_at: datetime.datetime

    @classmethod
    def from_dict(cls, data: dict[str, typing.Any]) -> typing.Self:
        dt = datetime.datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        return cls(
            id=int(data["id"]),
            collection_id=int(data["collection_id"]),
            name=str(data["name"]),
            source_url=str(data["source_url"]),
            raw_source_text=str(data["raw_source_text"]),
            extracted_data=dict(data["extracted_data"]) if data.get("extracted_data") else None,
            created_at=dt
        )

    @classmethod
    def from_row(cls, row: sqlalchemy.Row) -> typing.Self:
        return cls(
            id=row._mapping["id"],
            collection_id=row._mapping["collection_id"],
            name=row._mapping["name"],
            source_url=row._mapping["source_url"],
            raw_source_text=row._mapping["raw_source_text"],
            extracted_data=row._mapping["extracted_data"],
            created_at=row._mapping["created_at"]
        )

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "name": self.name,
            "source_url": self.source_url,
            "raw_source_text": self.raw_source_text,
            "extracted_data": self.extracted_data,
            "created_at": self.created_at.isoformat()
        }

class ProductCollection(list[Product]):
    @classmethod
    def from_rows(cls, rows: typing.Iterable[sqlalchemy.Row]) -> typing.Self:
        return cls([Product.from_row(r) for r in rows])

    def to_dict_list(self) -> list[dict[str, typing.Any]]:
        return [p.to_dict() for p in self]
