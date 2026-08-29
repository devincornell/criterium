import fastapi
import typing
import pathlib
from fastapi.responses import HTMLResponse, RedirectResponse
import criterium
from criterium.schemas import (
    CollectionCreate, CollectionUpdate, CollectionResponse,
    ProductCreate, ProductExtractResult, ProductResponse
)

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


# --- Collections Endpoints ---

@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(db: criterium.ResearchDB = fastapi.Depends(get_db)):
    return db.get_all_collections()

@router.post("/collections", response_model=CollectionResponse)
def create_collection(
    data: CollectionCreate,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    return db.add_collection(
        name=data.name,
        extraction_prompt=data.extraction_prompt,
        research_schema=data.research_schema
    )

@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        return db.get_collection(collection_id)
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int, 
    data: CollectionUpdate,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        return db.update_collection(
            collection_id=collection_id,
            name=data.name,
            extraction_prompt=data.extraction_prompt,
            research_schema=data.research_schema
        )
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

@router.get("/collections/{collection_id}/products", response_model=list[ProductResponse])
def list_products(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    return db.get_products_by_collection(collection_id)

@router.post("/collections/{collection_id}/products", response_model=ProductExtractResult)
def extract_product(
    collection_id: int, 
    data: ProductCreate,
    request: fastapi.Request,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    """
    This endpoint will take the product_info query, scrape it, and extract data
    against the collection's schema.
    """
    try:
        collection = db.get_collection(collection_id)
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))
    
    researcher = criterium.GeminiSearchResearcher(
        ai_client=request.app.state.ai_client,
    )

    try:
        research_result = researcher.research(data.product_info, collection)
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=f"Research failed: {e}")

    try:
        product = db.add_product(
            collection_id=collection_id,
            name=f"Research: {data.product_info}",
            source_url=research_result.source_url,
            raw_source_text=research_result.raw_source_text,
            extracted_data=research_result.extracted_data,
        )
    except criterium.SourceUrlAlreadyExistsError as e:
        raise fastapi.HTTPException(status_code=409, detail=str(e))

    return ProductExtractResult(
        source_url=product.source_url, 
        status="success", 
        product_id=product.id
    )

@router.get("/collections/{collection_id}/products/{product_id}", response_model=ProductResponse)
def get_product(
    collection_id: int, 
    product_id: int,
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    try:
        product = db.get_product(product_id)
        if product.collection_id != collection_id:
            raise fastapi.HTTPException(status_code=404, detail="Product not found in this collection")
        return product
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
