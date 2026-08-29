import dataclasses

import pytest
from fastapi.testclient import TestClient

import criterium
from app import create_app
from app.api import get_researcher
from app.config import Settings


@dataclasses.dataclass
class FakeResearcher:
    should_fail: bool = False

    def discover(self, product_info: str) -> criterium.DiscoveryResult:
        raise NotImplementedError

    def extract(self, text: str, collection: criterium.ResearchCollection):
        raise NotImplementedError

    def research(
        self,
        product_info: str,
        collection: criterium.ResearchCollection,
    ) -> criterium.ResearchResult:
        if self.should_fail:
            raise RuntimeError("provider unavailable")
        return criterium.ResearchResult(
            source_url="https://example.com/source",
            raw_source_text="Grounded evidence",
            extracted_data={"title": product_info},
            references=(
                criterium.ResearchReference(
                    url="https://example.com/source",
                    title="Source",
                    provider="test",
                ),
            ),
        )


@pytest.fixture
def app():
    settings = Settings(
        gemini_api_key="test-gemini-key",
        firecrawl_api_key="test-firecrawl-key",
        db_url="sqlite:///:memory:",
    )
    return create_app(settings=settings)


@pytest.fixture
def client(app):
    app.dependency_overrides[get_researcher] = lambda: FakeResearcher()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def collection_payload() -> dict:
    return {
        "name": "Books",
        "extraction_prompt": "Extract the title.",
        "research_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    }


def create_collection(client: TestClient) -> int:
    response = client.post("/collections", json=collection_payload())
    assert response.status_code == 200
    return response.json()["id"]


def test_collection_crud_and_missing_resource(client: TestClient) -> None:
    collection_id = create_collection(client)

    assert client.get(f"/collections/{collection_id}").status_code == 200
    assert client.patch(
        f"/collections/{collection_id}",
        json={"name": "Novels"},
    ).json()["name"] == "Novels"

    assert client.delete(f"/collections/{collection_id}").status_code == 200
    assert client.get(f"/collections/{collection_id}").status_code == 404


def test_product_research_persists_data_and_references(client: TestClient) -> None:
    collection_id = create_collection(client)

    response = client.post(
        f"/collections/{collection_id}/products",
        json={"product_info": "Example"},
    )

    assert response.status_code == 200
    assert response.json()["references"][0]["provider"] == "test"

    products = client.get(f"/collections/{collection_id}/products").json()
    assert products[0]["extracted_data"] == {"title": "Example"}
    assert products[0]["references"][0]["title"] == "Source"

    product_id = products[0]["id"]
    assert client.get(
        f"/collections/{collection_id}/products/{product_id}"
    ).status_code == 200
    assert client.delete(
        f"/collections/{collection_id}/products/{product_id}"
    ).status_code == 200
    assert client.get(
        f"/collections/{collection_id}/products/{product_id}"
    ).status_code == 404


def test_product_cannot_be_read_through_another_collection(client: TestClient) -> None:
    collection_id = create_collection(client)
    other_collection_id = create_collection(client)
    response = client.post(
        f"/collections/{collection_id}/products",
        json={"product_info": "Example"},
    )
    product_id = response.json()["product_id"]

    assert client.get(
        f"/collections/{other_collection_id}/products/{product_id}"
    ).status_code == 404


def test_duplicate_source_returns_conflict(client: TestClient) -> None:
    collection_id = create_collection(client)
    url = f"/collections/{collection_id}/products"

    assert client.post(url, json={"product_info": "First"}).status_code == 200
    assert client.post(url, json={"product_info": "Second"}).status_code == 409


def test_research_failure_returns_server_error(app) -> None:
    app.dependency_overrides[get_researcher] = lambda: FakeResearcher(should_fail=True)
    with TestClient(app) as client:
        collection_id = create_collection(client)
        response = client.post(
            f"/collections/{collection_id}/products",
            json={"product_info": "Example"},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Research failed: provider unavailable"
