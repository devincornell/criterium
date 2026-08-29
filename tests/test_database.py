import pytest

from criterium.database import ResearchDB
from criterium.exceptions import (
    CollectionNotFoundError,
    ProductNotFoundError,
    SourceUrlAlreadyExistsError,
)
from criterium.models import ResearchReference
from criterium.schemas import ResearchSchemaObject, ResearchSchemaString


@pytest.fixture
def db():
    database = ResearchDB.from_connection_string(
        "sqlite:///:memory:",
        create_if_not_exists=True,
    )
    yield database
    database.engine.dispose()


def make_schema() -> ResearchSchemaObject:
    return ResearchSchemaObject(
        properties={"title": ResearchSchemaString(is_required=True)}
    )


def test_collection_crud(db: ResearchDB) -> None:
    collection = db.add_collection("Books", "Extract title", make_schema())

    assert db.get_collection(collection.id).name == "Books"
    assert len(db.get_all_collections()) == 1

    updated = db.update_collection(collection.id, name="Novels")
    assert updated.name == "Novels"

    db.delete_collection(collection.id)
    with pytest.raises(CollectionNotFoundError):
        db.get_collection(collection.id)


def test_product_references_round_trip_and_cascade(db: ResearchDB) -> None:
    collection = db.add_collection("Books", "Extract title", make_schema())
    product = db.add_product(
        collection_id=collection.id,
        name="Example",
        source_url="https://example.com/one",
        raw_source_text="Evidence",
        extracted_data={"title": "Example"},
        references=[
            ResearchReference("https://example.com/one", "One", "google_search"),
            ResearchReference("https://example.com/two", "Two", "google_search"),
            ResearchReference("https://example.com/one", "Duplicate", "google_search"),
        ],
    )

    assert len(product.references) == 2
    assert [item.title for item in db.get_product(product.id).references] == ["One", "Two"]
    assert len(db.get_products_by_collection(collection.id)[0].references) == 2

    db.delete_collection(collection.id)
    with pytest.raises(ProductNotFoundError):
        db.get_product(product.id)


def test_duplicate_source_url_is_rejected(db: ResearchDB) -> None:
    collection = db.add_collection("Books", "Extract title", make_schema())
    values = {
        "collection_id": collection.id,
        "name": "Example",
        "source_url": "https://example.com/one",
        "raw_source_text": "Evidence",
    }

    db.add_product(**values)

    with pytest.raises(SourceUrlAlreadyExistsError):
        db.add_product(**values)
