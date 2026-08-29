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
    research_references: sqlalchemy.Table

    @classmethod
    def from_metadata(cls, metadata: sqlalchemy.MetaData) -> typing.Self:
        research_collections = sqlalchemy.Table(
                "research_collections",
                metadata,
                sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
                sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
                sqlalchemy.Column("extraction_prompt", sqlalchemy.Text, nullable=False),
                sqlalchemy.Column("research_schema", sqlalchemy.JSON, nullable=False),
                sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False),
            )
        products = sqlalchemy.Table(
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
        research_references = sqlalchemy.Table(
            "research_references",
            metadata,
            sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
            sqlalchemy.Column(
                "product_id",
                sqlalchemy.Integer,
                sqlalchemy.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sqlalchemy.Column("url", sqlalchemy.String(2048), nullable=False),
            sqlalchemy.Column("title", sqlalchemy.String(1024), nullable=True),
            sqlalchemy.Column("provider", sqlalchemy.String(64), nullable=False),
            sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False),
            sqlalchemy.UniqueConstraint("product_id", "url", name="uq_research_reference_product_url"),
        )
        return cls(
            metadata=metadata,
            research_collections=research_collections,
            products=products,
            research_references=research_references,
        )

    def all(self) -> list[sqlalchemy.Table]:
        return [self.research_collections, self.products, self.research_references]

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
        research_schema: schemas.ResearchSchemaDef
    ) -> models.ResearchCollection:
        stmt = sqlalchemy.insert(self.tabs.research_collections).values(
            name=name,
            extraction_prompt=extraction_prompt,
            research_schema=research_schema.model_dump(exclude_none=True),
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
        research_schema: schemas.ResearchSchemaDef | None = None
    ) -> models.ResearchCollection:
        update_values = {}
        if name is not None:
            update_values["name"] = name
        if extraction_prompt is not None:
            update_values["extraction_prompt"] = extraction_prompt
        if research_schema is not None:
            update_values["research_schema"] = research_schema.model_dump(exclude_none=True)
            
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
            product_ids = sqlalchemy.select(self.tabs.products.c.id).where(
                self.tabs.products.c.collection_id == collection_id
            )
            conn.execute(
                sqlalchemy.delete(self.tabs.research_references).where(
                    self.tabs.research_references.c.product_id.in_(product_ids)
                )
            )
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
        extracted_data: dict[str, typing.Any] | None = None,
        references: typing.Iterable[models.ResearchReference] = (),
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
                product = models.Product.from_row(row)
                persisted_references = []
                seen_urls = set()
                for reference in references:
                    if reference.url in seen_urls:
                        continue
                    seen_urls.add(reference.url)
                    reference_stmt = sqlalchemy.insert(self.tabs.research_references).values(
                        product_id=product.id,
                        url=reference.url,
                        title=reference.title,
                        provider=reference.provider,
                        created_at=datetime.datetime.now(datetime.timezone.utc),
                    ).returning(self.tabs.research_references)
                    reference_row = conn.execute(reference_stmt).fetchone()
                    if not reference_row:
                        raise exceptions.CriteriumError("Failed to insert research reference.")
                    persisted_references.append(models.ResearchReference.from_row(reference_row))
                return dataclasses.replace(product, references=tuple(persisted_references))
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
            product = models.Product.from_row(row)
            references = self._get_references(conn, [product.id])
            return dataclasses.replace(product, references=references.get(product.id, ()))

    def get_products_by_collection(self, collection_id: int) -> models.ProductCollection:
        stmt = sqlalchemy.select(self.tabs.products).where(self.tabs.products.c.collection_id == collection_id)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            products = models.ProductCollection.from_rows(rows)
            references = self._get_references(conn, [product.id for product in products])
            return models.ProductCollection(
                dataclasses.replace(product, references=references.get(product.id, ()))
                for product in products
            )

    def _get_references(
        self,
        conn: sqlalchemy.Connection,
        product_ids: list[int],
    ) -> dict[int, tuple[models.ResearchReference, ...]]:
        if not product_ids:
            return {}
        stmt = sqlalchemy.select(self.tabs.research_references).where(
            self.tabs.research_references.c.product_id.in_(product_ids)
        ).order_by(self.tabs.research_references.c.id)
        references: dict[int, list[models.ResearchReference]] = {}
        for row in conn.execute(stmt):
            reference = models.ResearchReference.from_row(row)
            references.setdefault(reference.product_id, []).append(reference)
        return {product_id: tuple(items) for product_id, items in references.items()}

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
        with self.engine.begin() as conn:
            conn.execute(
                sqlalchemy.delete(self.tabs.research_references).where(
                    self.tabs.research_references.c.product_id == product_id
                )
            )
            stmt = sqlalchemy.delete(self.tabs.products).where(self.tabs.products.c.id == product_id)
            res = conn.execute(stmt)
            if res.rowcount == 0:
                raise exceptions.ProductNotFoundError(f"Product with id {product_id} not found.")
