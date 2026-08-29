import dataclasses

import pytest
from fastapi.testclient import TestClient

import criterium
from app import create_app
from app.api import get_collection_suggester
from app.config import Settings


@dataclasses.dataclass
class FakeResearcher:
    should_fail: bool = False
    omit_required_field: bool = False
    return_null: bool = False

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
            extracted_data=(
                {}
                if self.omit_required_field
                else {"title": None if self.return_null else product_info}
            ),
            references=(
                criterium.ResearchReference(
                    url="https://example.com/source",
                    title="Source",
                    provider="test",
                ),
            ),
        )

@dataclasses.dataclass
class FakeCollectionSuggester:
    should_fail: bool = False

    def suggest(self, description: str) -> criterium.schemas.CollectionSuggestionResponse:
        if self.should_fail:
            raise RuntimeError("provider unavailable")
        return criterium.schemas.CollectionSuggestionResponse.model_validate(
            {
                "name": "Suggested Collection",
                "extraction_prompt": f"Research {description}",
                "research_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Canonical item title.",
                        }
                    },
                    "required": ["title"],
                },
            }
        )


@pytest.fixture
def app():
    settings = Settings(
        gemini_api_key="test-gemini-key",
        firecrawl_api_key="test-firecrawl-key",
        db_url="sqlite:///:memory:",
        research_worker_poll_seconds=3600,
    )
    test_app = create_app(settings=settings)
    test_app.state.researcher = FakeResearcher()
    return test_app


@pytest.fixture
def client(app):
    app.dependency_overrides[get_collection_suggester] = lambda: FakeCollectionSuggester()
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


def test_suggest_collection_schema(client: TestClient) -> None:
    response = client.post(
        "/collections/suggest-schema",
        json={"description": "Compare science fiction novels by major attributes"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Suggested Collection"
    assert payload["research_schema"]["required"] == ["title"]


def test_suggest_collection_schema_validates_description(client: TestClient) -> None:
    response = client.post(
        "/collections/suggest-schema",
        json={"description": "short"},
    )

    assert response.status_code == 422


def test_suggest_collection_schema_handles_provider_failure(app) -> None:
    app.dependency_overrides[get_collection_suggester] = lambda: FakeCollectionSuggester(
        should_fail=True
    )
    with TestClient(app) as client:
        response = client.post(
            "/collections/suggest-schema",
            json={"description": "Compare science fiction novels by major attributes"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Schema suggestion failed: provider unavailable"


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
        f"/collections/{collection_id}/research-jobs",
        json={"product_info": "Example"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["product_id"] is None

    assert client.app.state.research_worker.run_once() is True
    job = client.get(f"/research-jobs/{response.json()['id']}").json()
    assert job["status"] == "succeeded"

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
        f"/collections/{collection_id}/research-jobs",
        json={"product_info": "Example"},
    )
    client.app.state.research_worker.run_once()
    product_id = client.get(f"/research-jobs/{response.json()['id']}").json()["product_id"]

    assert client.get(
        f"/collections/{other_collection_id}/products/{product_id}"
    ).status_code == 404


def test_duplicate_source_marks_second_job_failed(client: TestClient) -> None:
    collection_id = create_collection(client)
    url = f"/collections/{collection_id}/research-jobs"

    first = client.post(url, json={"product_info": "First"})
    client.app.state.research_worker.run_once()
    assert client.get(f"/research-jobs/{first.json()['id']}").json()["status"] == "succeeded"

    second = client.post(url, json={"product_info": "Second"})
    client.app.state.research_worker.run_once()
    failed_job = client.get(f"/research-jobs/{second.json()['id']}").json()
    assert failed_job["status"] == "failed"
    assert "already exists" in failed_job["error_message"]


def test_research_failure_is_reported_on_job(app) -> None:
    app.state.researcher = FakeResearcher(should_fail=True)
    with TestClient(app) as client:
        collection_id = create_collection(client)
        response = client.post(
            f"/collections/{collection_id}/research-jobs",
            json={"product_info": "Example"},
        )
        client.app.state.research_worker.run_once()
        job_response = client.get(f"/research-jobs/{response.json()['id']}")

    assert response.status_code == 202
    assert job_response.json()["status"] == "failed"
    assert job_response.json()["error_message"] == "provider unavailable"


def test_incomplete_research_result_is_reported_on_job(app) -> None:
    app.state.researcher = FakeResearcher(omit_required_field=True)
    with TestClient(app) as client:
        collection_id = create_collection(client)
        response = client.post(
            f"/collections/{collection_id}/research-jobs",
            json={"product_info": "Example"},
        )
        client.app.state.research_worker.run_once()
        job = client.get(f"/research-jobs/{response.json()['id']}").json()

    assert job["status"] == "failed"
    assert "required property" in job["error_message"]


def test_unknown_research_value_is_persisted_as_null(app) -> None:
    app.state.researcher = FakeResearcher(return_null=True)
    with TestClient(app) as client:
        collection_id = create_collection(client)
        response = client.post(
            f"/collections/{collection_id}/research-jobs",
            json={"product_info": "Example"},
        )
        client.app.state.research_worker.run_once()
        job = client.get(f"/research-jobs/{response.json()['id']}").json()
        product = client.get(
            f"/collections/{collection_id}/products/{job['product_id']}"
        ).json()

    assert job["status"] == "succeeded"
    assert product["extracted_data"] == {"title": None}


def test_research_job_list_and_missing_job(client: TestClient) -> None:
    collection_id = create_collection(client)
    response = client.post(
        f"/collections/{collection_id}/research-jobs",
        json={"product_info": "Example"},
    )

    jobs = client.get(f"/collections/{collection_id}/research-jobs").json()
    assert [job["id"] for job in jobs] == [response.json()["id"]]
    assert client.get("/research-jobs/999").status_code == 404


def test_legacy_product_post_queues_research(client: TestClient) -> None:
    collection_id = create_collection(client)

    response = client.post(
        f"/collections/{collection_id}/products",
        json={"product_info": "Example"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
