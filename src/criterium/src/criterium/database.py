import dataclasses
import datetime
import typing
import sqlalchemy
import sqlalchemy.exc
from . import models
from . import exceptions

@dataclasses.dataclass(frozen=True)
class ResearchDBTables:
    metadata: sqlalchemy.MetaData
    research_collections: sqlalchemy.Table
    products: sqlalchemy.Table

    @classmethod
    def from_metadata(cls, metadata: sqlalchemy.MetaData) -> typing.Self:
        return cls(
            metadata=metadata,
            research_collections=sqlalchemy.Table(
                "research_collections",
                metadata,
                sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
                sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
                sqlalchemy.Column("extraction_prompt", sqlalchemy.Text, nullable=False),
                sqlalchemy.Column("llm_schema", sqlalchemy.JSON, nullable=False),
                sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False),
            ),
            products=sqlalchemy.Table(
                "products",
                metadata,
                sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
                sqlalchemy.Column("collection_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("research_collections.id"), nullable=False),
                sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
                sqlalchemy.Column("source_url", sqlalchemy.String(1024), nullable=False, unique=True),
                sqlalchemy.Column("raw_source_text", sqlalchemy.Text, nullable=False),
                sqlalchemy.Column("extracted_data", sqlalchemy.JSON, nullable=True),
                sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False),
            )
        )

    def all(self) -> list[sqlalchemy.Table]:
        return [self.research_collections, self.products]

@dataclasses.dataclass(frozen=True)
class ResearchDB:
    engine: sqlalchemy.Engine
    metadata: sqlalchemy.MetaData
    tabs: ResearchDBTables

    @classmethod
    def from_connection_string(
        cls,
        db_connect_string: str,
        create_if_not_exists: bool = False,
    ) -> typing.Self:
        # SQLite in-memory databases using the default pool close/wipe the database on every connection close.
        # StaticPool keeps the same in-memory connection open across multiple requests/threads.
        if "sqlite:///:memory:" in db_connect_string:
            engine = sqlalchemy.create_engine(
                db_connect_string,
                connect_args={"check_same_thread": False},
                poolclass=sqlalchemy.pool.StaticPool,
            )
        elif db_connect_string.startswith("sqlite"):
            engine = sqlalchemy.create_engine(
                db_connect_string,
                connect_args={"check_same_thread": False},
            )
        else:
            engine = sqlalchemy.create_engine(db_connect_string)
        metadata = sqlalchemy.MetaData()
        tabs = ResearchDBTables.from_metadata(metadata)

        if create_if_not_exists:
            metadata.create_all(bind=engine, tables=tabs.all(), checkfirst=True)
        
        return cls(engine=engine, metadata=metadata, tabs=tabs)

    def add_collection(
        self, 
        name: str, 
        extraction_prompt: str, 
        llm_schema: models.LLMSchema
    ) -> models.ResearchCollection:
        stmt = sqlalchemy.insert(self.tabs.research_collections).values(
            name=name,
            extraction_prompt=extraction_prompt,
            llm_schema=llm_schema.to_dict(),
            created_at=datetime.datetime.now(datetime.timezone.utc)
        ).returning(self.tabs.research_collections)
        
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            if not row:
                raise exceptions.CriteriumError("Failed to insert research collection.")
            return models.ResearchCollection.from_row(row)

    def get_collection(self, collection_id: int) -> models.ResearchCollection:
        stmt = sqlalchemy.select(self.tabs.research_collections).where(self.tabs.research_collections.c.id == collection_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if not row:
                raise exceptions.CollectionNotFoundError(f"Collection with id {collection_id} not found.")
            return models.ResearchCollection.from_row(row)

    def get_all_collections(self) -> models.ResearchCollectionList:
        stmt = sqlalchemy.select(self.tabs.research_collections)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return models.ResearchCollectionList.from_rows(rows)

    def update_collection(
        self,
        collection_id: int,
        name: str | None = None,
        extraction_prompt: str | None = None,
        llm_schema: models.LLMSchema | None = None
    ) -> models.ResearchCollection:
        update_values = {}
        if name is not None:
            update_values["name"] = name
        if extraction_prompt is not None:
            update_values["extraction_prompt"] = extraction_prompt
        if llm_schema is not None:
            update_values["llm_schema"] = llm_schema.to_dict()
            
        if not update_values:
            return self.get_collection(collection_id)

        stmt = sqlalchemy.update(self.tabs.research_collections).where(
            self.tabs.research_collections.c.id == collection_id
        ).values(**update_values).returning(self.tabs.research_collections)
        
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            if not row:
                raise exceptions.CollectionNotFoundError(f"Collection with id {collection_id} not found.")
            return models.ResearchCollection.from_row(row)

    def delete_collection(self, collection_id: int) -> None:
        # Note: Depending on foreign key constraints, you might want cascading deletes enabled in the DB,
        # or manually delete products first. Here we assume manual deletion of products for safety.
        with self.engine.begin() as conn:
            # Delete products first
            conn.execute(sqlalchemy.delete(self.tabs.products).where(self.tabs.products.c.collection_id == collection_id))
            # Then delete collection
            res = conn.execute(sqlalchemy.delete(self.tabs.research_collections).where(self.tabs.research_collections.c.id == collection_id))
            if res.rowcount == 0:
                raise exceptions.CollectionNotFoundError(f"Collection with id {collection_id} not found.")

    def add_product(
        self, 
        collection_id: int, 
        name: str, 
        source_url: str, 
        raw_source_text: str, 
        extracted_data: dict[str, typing.Any] | None = None
    ) -> models.Product:
        stmt = sqlalchemy.insert(self.tabs.products).values(
            collection_id=collection_id,
            name=name,
            source_url=source_url,
            raw_source_text=raw_source_text,
            extracted_data=extracted_data,
            created_at=datetime.datetime.now(datetime.timezone.utc)
        ).returning(self.tabs.products)
        
        with self.engine.begin() as conn:
            try:
                result = conn.execute(stmt)
                row = result.fetchone()
                if not row:
                    raise exceptions.CriteriumError("Failed to insert product.")
                return models.Product.from_row(row)
            except sqlalchemy.exc.IntegrityError as e:
                err_msg = str(e).lower()
                if "unique constraint" in err_msg or "unique" in err_msg:
                    raise exceptions.SourceUrlAlreadyExistsError(f"Product with url {source_url} already exists.") from e
                raise

    def get_product(self, product_id: int) -> models.Product:
        stmt = sqlalchemy.select(self.tabs.products).where(self.tabs.products.c.id == product_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if not row:
                raise exceptions.ProductNotFoundError(f"Product with id {product_id} not found.")
            return models.Product.from_row(row)

    def get_products_by_collection(self, collection_id: int) -> models.ProductCollection:
        stmt = sqlalchemy.select(self.tabs.products).where(self.tabs.products.c.collection_id == collection_id)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return models.ProductCollection.from_rows(rows)

    def update_product_data(self, product_id: int, extracted_data: dict[str, typing.Any]) -> models.Product:
        stmt = sqlalchemy.update(self.tabs.products).where(
            self.tabs.products.c.id == product_id
        ).values(extracted_data=extracted_data).returning(self.tabs.products)
        
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            if not row:
                raise exceptions.ProductNotFoundError(f"Product with id {product_id} not found.")
            return models.Product.from_row(row)

    def delete_product(self, product_id: int) -> None:
        stmt = sqlalchemy.delete(self.tabs.products).where(self.tabs.products.c.id == product_id)
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
            if res.rowcount == 0:
                raise exceptions.ProductNotFoundError(f"Product with id {product_id} not found.")
