import requests
from . import schemas

class CriteriumClient:
    """Client SDK for the Criterium Research API."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def list_collections(self) -> list[schemas.CollectionResponse]:
        response = self.session.get(f"{self.base_url}/collections")
        response.raise_for_status()
        return [schemas.CollectionResponse.model_validate(item) for item in response.json()]

    def create_collection(self, request: schemas.CollectionCreate) -> schemas.CollectionResponse:
        response = self.session.post(
            f"{self.base_url}/collections", 
            json=request.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        return schemas.CollectionResponse.model_validate(response.json())

    def get_collection(self, collection_id: int) -> schemas.CollectionResponse:
        response = self.session.get(f"{self.base_url}/collections/{collection_id}")
        response.raise_for_status()
        return schemas.CollectionResponse.model_validate(response.json())

    def update_collection(self, collection_id: int, request: schemas.CollectionUpdate) -> schemas.CollectionResponse:
        response = self.session.patch(
            f"{self.base_url}/collections/{collection_id}", 
            json=request.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        return schemas.CollectionResponse.model_validate(response.json())

    def delete_collection(self, collection_id: int) -> None:
        response = self.session.delete(f"{self.base_url}/collections/{collection_id}")
        response.raise_for_status()

    def list_products(self, collection_id: int) -> list[schemas.ProductResponse]:
        response = self.session.get(f"{self.base_url}/collections/{collection_id}/products")
        response.raise_for_status()
        return [schemas.ProductResponse.model_validate(item) for item in response.json()]

    def extract_product(self, collection_id: int, request: schemas.ProductCreate) -> schemas.ProductExtractResult:
        response = self.session.post(
            f"{self.base_url}/collections/{collection_id}/products", 
            json=request.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        return schemas.ProductExtractResult.model_validate(response.json())

    def get_product(self, collection_id: int, product_id: int) -> schemas.ProductResponse:
        response = self.session.get(f"{self.base_url}/collections/{collection_id}/products/{product_id}")
        response.raise_for_status()
        return schemas.ProductResponse.model_validate(response.json())

    def delete_product(self, collection_id: int, product_id: int) -> None:
        response = self.session.delete(f"{self.base_url}/collections/{collection_id}/products/{product_id}")
        response.raise_for_status()
