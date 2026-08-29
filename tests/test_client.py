from criterium.client import CriteriumClient
from criterium.schemas import (
    CollectionCreate,
    CollectionSuggestionRequest,
    ProductCreate,
    ResearchJobsCreate,
    ResearchSchemaObject,
)


class FakeResponse:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.raise_called = False

    def raise_for_status(self) -> None:
        self.raise_called = True

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []

    def get(self, url: str):
        self.calls.append(("GET", url, None))
        return self.response

    def post(self, url: str, json):
        self.calls.append(("POST", url, json))
        return self.response

    def patch(self, url: str, json):
        self.calls.append(("PATCH", url, json))
        return self.response

    def delete(self, url: str):
        self.calls.append(("DELETE", url, None))
        return self.response


def test_create_collection_posts_serialized_schema() -> None:
    response = FakeResponse(
        {
            "id": 1,
            "name": "Books",
            "research_instructions": None,
            "research_schema": {"type": "object", "properties": {}},
            "created_at": "2026-01-01T00:00:00Z",
        }
    )
    session = FakeSession(response)
    client = CriteriumClient("http://example.test/")
    client.session = session

    result = client.create_collection(
        CollectionCreate(
            name="Books",
            research_schema=ResearchSchemaObject(),
        )
    )

    assert result.id == 1
    assert session.calls[0][0:2] == ("POST", "http://example.test/collections")
    assert response.raise_called


def test_extract_product_posts_to_nested_resource() -> None:
    response = FakeResponse(
        {
            "id": 8,
            "collection_id": 3,
            "product_info": "Example",
            "status": "queued",
            "stage": None,
            "product_id": None,
            "error_message": None,
            "attempt_count": 0,
            "created_at": "2026-01-01T00:00:00Z",
            "started_at": None,
            "completed_at": None,
        }
    )
    session = FakeSession(response)
    client = CriteriumClient("http://example.test")
    client.session = session

    result = client.extract_product(3, ProductCreate(product_info="Example"))

    assert result.id == 8
    assert result.status == "queued"
    assert session.calls == [
        (
            "POST",
            "http://example.test/collections/3/products",
            {"product_info": "Example"},
        )
    ]


def test_create_research_jobs_posts_batch() -> None:
    response = FakeResponse([
        {
            "id": job_id,
            "collection_id": 3,
            "product_info": product_info,
            "status": "queued",
            "stage": None,
            "product_id": None,
            "error_message": None,
            "attempt_count": 0,
            "created_at": "2026-01-01T00:00:00Z",
            "started_at": None,
            "completed_at": None,
        }
        for job_id, product_info in [(8, "First"), (9, "Second")]
    ])
    session = FakeSession(response)
    client = CriteriumClient("http://example.test")
    client.session = session

    jobs = client.create_research_jobs(
        3,
        ResearchJobsCreate(product_infos=["First", "Second"]),
    )

    assert [job.product_info for job in jobs] == ["First", "Second"]
    assert session.calls == [(
        "POST",
        "http://example.test/collections/3/research-jobs",
        {"product_infos": ["First", "Second"]},
    )]


def test_suggest_collection_posts_description() -> None:
    response = FakeResponse(
        {
            "name": "Electric Vehicles",
            "research_instructions": None,
            "research_schema": {
                "type": "object",
                "properties": {"range_miles": {"type": "integer"}},
            },
        }
    )
    session = FakeSession(response)
    client = CriteriumClient("http://example.test")
    client.session = session

    result = client.suggest_collection(
        CollectionSuggestionRequest(
            description="Compare compact electric vehicles for city driving"
        )
    )

    assert result.name == "Electric Vehicles"
    assert session.calls == [
        (
            "POST",
            "http://example.test/collections/suggest-schema",
            {"description": "Compare compact electric vehicles for city driving"},
        )
    ]
