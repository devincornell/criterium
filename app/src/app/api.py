import fastapi
import typing
import pathlib
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
import criterium

router = fastapi.APIRouter()

@router.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/app")

@router.get("/app", include_in_schema=False)
def serve_ui():
    html_path = pathlib.Path(__file__).parent / "ui.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

# Dependency to get the DB instance (we will attach the db to the app state)
def get_db(request: fastapi.Request) -> criterium.ResearchDB:
    return request.app.state.db

# --- Schemas (Pydantic for I/O validation) ---

class CollectionCreate(BaseModel):
    name: str
    extraction_prompt: str
    llm_schema: dict[str, typing.Any]

class CollectionUpdate(BaseModel):
    name: str | None = None
    extraction_prompt: str | None = None
    llm_schema: dict[str, typing.Any] | None = None

class ProductCreate(BaseModel):
    source_url: str

class ProductExtractResult(BaseModel):
    source_url: str
    status: str
    product_id: int | None = None
    error: str | None = None


# --- Collections Endpoints ---

@router.get("/collections")
def list_collections(db: criterium.ResearchDB = fastapi.Depends(get_db)):
    collections = db.get_all_collections()
    return collections.to_dict_list()

@router.post("/collections")
def create_collection(
    data: CollectionCreate,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    collection = db.add_collection(
        name=data.name,
        extraction_prompt=data.extraction_prompt,
        llm_schema=data.llm_schema
    )
    return collection.to_dict()

@router.get("/collections/{collection_id}")
def get_collection(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        collection = db.get_collection(collection_id)
        return collection.to_dict()
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

@router.patch("/collections/{collection_id}")
def update_collection(
    collection_id: int, 
    data: CollectionUpdate,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        collection = db.update_collection(
            collection_id=collection_id,
            name=data.name,
            extraction_prompt=data.extraction_prompt,
            llm_schema=data.llm_schema
        )
        # TODO: Trigger background job to re-extract data for all products in this collection
        return collection.to_dict()
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        db.delete_collection(collection_id)
        return {"status": "success", "message": f"Collection {collection_id} deleted."}
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))


# --- Products Endpoints ---

@router.get("/collections/{collection_id}/products")
def list_products(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    products = db.get_products_by_collection(collection_id)
    return products.to_dict_list()

@router.post("/collections/{collection_id}/products")
def extract_product(
    collection_id: int, 
    data: ProductCreate,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    """
    This endpoint will take the source_url, scrape it, and extract data
    against the collection's schema.
    """
    try:
        collection = db.get_collection(collection_id)
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))
    
    # Placeholder for actual extraction logic
    # In reality:
    # 1. Firecrawl scrape data.source_url
    # 2. Gemini extract structured output
    # 3. Save to DB
    
    raw_source = f"Raw source placeholder for {data.source_url}"
    extracted = {"mock": "data"}

    try:
        product = db.add_product(
            collection_id=collection_id,
            name=f"Extracted from {data.source_url}",
            source_url=data.source_url,
            raw_source_text=raw_source,
            extracted_data=extracted
        )
        return ProductExtractResult(
            source_url=data.source_url, 
            status="success", 
            product_id=product.id
        )
    except criterium.SourceUrlAlreadyExistsError as e:
        raise fastapi.HTTPException(status_code=409, detail=str(e))

@router.get("/collections/{collection_id}/products/{product_id}")
def get_product(
    collection_id: int, 
    product_id: int,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        product = db.get_product(product_id)
        if product.collection_id != collection_id:
            raise fastapi.HTTPException(status_code=404, detail="Product not found in this collection")
        return product.to_dict()
    except criterium.ProductNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

@router.delete("/collections/{collection_id}/products/{product_id}")
def delete_product(
    collection_id: int, 
    product_id: int,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        product = db.get_product(product_id)
        if product.collection_id != collection_id:
            raise fastapi.HTTPException(status_code=404, detail="Product not found in this collection")
        
        db.delete_product(product_id)
        return {"status": "success", "message": f"Product {product_id} deleted."}
    except criterium.ProductNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))
