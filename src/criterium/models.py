import dataclasses
import datetime
import typing
import sqlalchemy
from pydantic import TypeAdapter
from . import schemas

@dataclasses.dataclass(frozen=True)
class ResearchReference:
    url: str
    title: str | None = None
    provider: str = "unknown"
    id: int | None = None
    product_id: int | None = None
    created_at: datetime.datetime | None = None

    @classmethod
    def from_row(cls, row: sqlalchemy.Row) -> typing.Self:
        return cls(
            id=row._mapping["id"],
            product_id=row._mapping["product_id"],
            url=row._mapping["url"],
            title=row._mapping["title"],
            provider=row._mapping["provider"],
            created_at=row._mapping["created_at"],
        )

@dataclasses.dataclass(frozen=True)
class ResearchCollection:
    id: int
    name: str
    research_instructions: str | None
    research_schema: schemas.ResearchSchemaDef
    created_at: datetime.datetime

    @classmethod
    def from_row(cls, row: sqlalchemy.Row) -> typing.Self:
        return cls(
            id=row._mapping["id"],
            name=row._mapping["name"],
            research_instructions=row._mapping["research_instructions"] or None,
            research_schema=TypeAdapter(schemas.ResearchSchemaDef).validate_python(row._mapping["research_schema"]),
            created_at=row._mapping["created_at"]
        )

class ResearchCollectionList(list[ResearchCollection]):
    @classmethod
    def from_rows(cls, rows: typing.Iterable[sqlalchemy.Row]) -> typing.Self:
        return cls([ResearchCollection.from_row(r) for r in rows])

@dataclasses.dataclass(frozen=True)
class Product:
    id: int
    collection_id: int
    name: str
    source_url: str
    raw_source_text: str
    extracted_data: dict[str, typing.Any] | None
    created_at: datetime.datetime
    references: tuple[ResearchReference, ...] = ()

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

class ProductCollection(list[Product]):
    @classmethod
    def from_rows(cls, rows: typing.Iterable[sqlalchemy.Row]) -> typing.Self:
        return cls([Product.from_row(r) for r in rows])

@dataclasses.dataclass(frozen=True)
class ResearchJob:
    id: int
    collection_id: int
    product_info: str
    status: str
    stage: str | None
    product_id: int | None
    error_message: str | None
    attempt_count: int
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None

    @classmethod
    def from_row(cls, row: sqlalchemy.Row) -> typing.Self:
        return cls(**{
            field.name: row._mapping[field.name]
            for field in dataclasses.fields(cls)
        })

class ResearchJobCollection(list[ResearchJob]):
    @classmethod
    def from_rows(cls, rows: typing.Iterable[sqlalchemy.Row]) -> typing.Self:
        return cls([ResearchJob.from_row(row) for row in rows])
