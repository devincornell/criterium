import pathlib
import threading
import uvicorn
import fastapi
from contextlib import asynccontextmanager

import criterium
from google import genai
from firecrawl import Firecrawl
from .config import Settings, get_settings
from .api import router

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    settings = getattr(app.state, "settings", None) or get_settings()
    app.state.ai_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    app.state.fc_app = Firecrawl(api_key=settings.firecrawl_api_key.get_secret_value())
    print("API Clients initialized successfully!")

    # Set up the database 
    db_url = settings.db_url
    print(f"Connecting to database at {db_url}...")
    app.state.db = criterium.ResearchDB.from_connection_string(
        db_connect_string=db_url, 
        create_if_not_exists=True
    )
    requeued_jobs = app.state.db.requeue_running_research_jobs()
    if requeued_jobs:
        print(f"Requeued {requeued_jobs} interrupted research job(s).")

    researcher = getattr(app.state, "researcher", None) or criterium.GeminiSearchResearcher(
        ai_client=app.state.ai_client
    )
    app.state.research_worker = criterium.ResearchJobWorker(
        db=app.state.db,
        researcher=researcher,
        poll_interval=settings.research_worker_poll_seconds,
    )
    app.state.research_worker_stop = threading.Event()
    app.state.research_worker_threads = [
      threading.Thread(
        target=app.state.research_worker.run_forever,
        args=(app.state.research_worker_stop,),
        name=f"criterium-research-worker-{worker_number + 1}",
        daemon=True,
      )
      for worker_number in range(settings.research_worker_concurrency)
    ]
    for worker_thread in app.state.research_worker_threads:
      worker_thread.start()

    try:
        yield
    finally:
        app.state.research_worker_stop.set()
        for worker_thread in app.state.research_worker_threads:
          worker_thread.join(timeout=5)
        if not any(worker_thread.is_alive() for worker_thread in app.state.research_worker_threads):
            app.state.db.engine.dispose()
        print("Shutting down...")

API_DESCRIPTION = """
# Dynamic Schema Research Agent

This API enables structured, automated entity research. Instead of forcing findings into rigid, hardcoded database columns, you define **a priori evaluation criteria** using JSON Schema.

## Creating your Research Schema

When creating a new Collection, you must provide a `research_schema` using standard JSON Schema. The LLM uses this to structure its output.

### Example: Book Researcher
```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "The exact title of the primary book."
    },
    "year": {
      "type": "integer",
      "description": "The 4-digit year the book was published."
    },
    "series_books": {
      "type": "array",
      "description": "Other books in the same series.",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "chronological_order": { "type": "integer" }
        },
        "required": ["title", "chronological_order"]
      }
  },
  "required": ["title", "year", "series_books"]
}
```

**Pro-Tip:** If you prefer Python, you can write a Pydantic `BaseModel` and call `MyModel.model_json_schema()` to automatically generate the JSON Schema equivalent to paste into your Collection!
"""

def create_app(settings: Settings | None = None) -> fastapi.FastAPI:
    app = fastapi.FastAPI(
        title="Criterium Research API", 
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan
    )
    if settings is not None:
        app.state.settings = settings
    app.include_router(router)
    return app

def main() -> None:
    message = criterium.hello()
    print(f"App says: {message}")
    
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
