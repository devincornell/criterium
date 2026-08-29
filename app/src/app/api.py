import fastapi
import typing
import pathlib
from fastapi.responses import HTMLResponse, RedirectResponse
import criterium
from criterium.schemas import (
    CollectionCreate, CollectionUpdate, CollectionResponse,
    CollectionSuggestionRequest, CollectionSuggestionResponse,
    ProductCreate, ProductResponse, ResearchJobResponse
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

def get_researcher(request: fastapi.Request) -> criterium.Researcher:
    return criterium.GeminiSearchResearcher(ai_client=request.app.state.ai_client)

def get_collection_suggester(request: fastapi.Request) -> criterium.CollectionSuggester:
    return criterium.GeminiCollectionSuggester(ai_client=request.app.state.ai_client)


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

@router.post("/collections/suggest-schema", response_model=CollectionSuggestionResponse)
def suggest_collection_schema(
    data: CollectionSuggestionRequest,
    suggester: criterium.CollectionSuggester = fastapi.Depends(get_collection_suggester),
):
    try:
        return suggester.suggest(data.description)
    except Exception as e:
        raise fastapi.HTTPException(status_code=502, detail=f"Schema suggestion failed: {e}")

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

@router.get("/research-jobs", response_model=list[ResearchJobResponse])
def list_research_jobs(db: criterium.ResearchDB = fastapi.Depends(get_db)):
    return db.get_research_jobs()

@router.get("/research-jobs/{job_id}", response_model=ResearchJobResponse)
def get_research_job(
    job_id: int,
    db: criterium.ResearchDB = fastapi.Depends(get_db),
):
    try:
        return db.get_research_job(job_id)
    except criterium.ResearchJobNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

@router.get("/collections/{collection_id}/research-jobs", response_model=list[ResearchJobResponse])
def list_collection_research_jobs(
    collection_id: int,
    db: criterium.ResearchDB = fastapi.Depends(get_db),
):
    try:
        db.get_collection(collection_id)
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))
    return db.get_research_jobs(collection_id=collection_id)

@router.get("/collections/{collection_id}/products", response_model=list[ProductResponse])
def list_products(
    collection_id: int, 
    db: criterium.ResearchDB = fastapi.Depends(get_db)
):
    return db.get_products_by_collection(collection_id)

@router.post(
    "/collections/{collection_id}/products",
    response_model=ResearchJobResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    deprecated=True,
)
@router.post(
    "/collections/{collection_id}/research-jobs",
    response_model=ResearchJobResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
)
def create_research_job(
    collection_id: int, 
    data: ProductCreate,
    db: criterium.ResearchDB = fastapi.Depends(get_db),
):
    """
    Queue product research and return immediately with its job status.
    """
    try:
        return db.add_research_job(
            collection_id=collection_id,
            product_info=data.product_info,
        )
    except criterium.CollectionNotFoundError as e:
        raise fastapi.HTTPException(status_code=404, detail=str(e))

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
