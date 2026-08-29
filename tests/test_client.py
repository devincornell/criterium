from criterium.client import CriteriumClient
from criterium.schemas import CollectionCreate, ProductCreate, ResearchSchemaObject


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
            "extraction_prompt": "Extract",
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
            extraction_prompt="Extract",
            research_schema=ResearchSchemaObject(),
        )
    )

    assert result.id == 1
    assert session.calls[0][0:2] == ("POST", "http://example.test/collections")
    assert response.raise_called


def test_extract_product_posts_to_nested_resource() -> None:
    response = FakeResponse(
        {
            "source_url": "https://example.com",
            "status": "success",
            "product_id": 4,
            "references": [],
        }
    )
    session = FakeSession(response)
    client = CriteriumClient("http://example.test")
    client.session = session

    result = client.extract_product(3, ProductCreate(product_info="Example"))

    assert result.product_id == 4
    assert session.calls == [
        (
            "POST",
            "http://example.test/collections/3/products",
            {"product_info": "Example"},
        )
    ]
