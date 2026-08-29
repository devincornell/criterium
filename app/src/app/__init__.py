import pathlib
import uvicorn
import fastapi
from contextlib import asynccontextmanager

import criterium
from google import genai
from firecrawl import Firecrawl
from .config import settings
from .api import router

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # Initialize your clients using the pydantic settings
    # We use get_secret_value() because we defined them as SecretStr to prevent accidental logging
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

    yield
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
        "required": ["title"]
      }
    }
  },
  "required": ["title", "year"]
}
```

**Pro-Tip:** If you prefer Python, you can write a Pydantic `BaseModel` and call `MyModel.model_json_schema()` to automatically generate the JSON Schema equivalent to paste into your Collection!
"""

def create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI(
        title="Criterium Research API", 
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan
    )
    app.include_router(router)
    return app

def main() -> None:
    message = criterium.hello()
    print(f"App says: {message}")
    
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)
