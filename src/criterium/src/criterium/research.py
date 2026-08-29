import typing
import dataclasses
from google import genai
from google.genai import types
from firecrawl import FirecrawlApp
from . import models

@dataclasses.dataclass(frozen=True)
class DiscoveryResult:
    source_url: str
    raw_source_text: str

@dataclasses.dataclass(frozen=True)
class ResearchResult(DiscoveryResult):
    extracted_data: dict[str, typing.Any]

class Researcher(typing.Protocol):
    def discover(self, product_info: str) -> DiscoveryResult:
        """Finds the product on the web and extracts raw markdown context."""
        ...
        
    def extract(self, text: str, collection: models.ResearchCollection) -> dict[str, typing.Any]:
        """Passes the raw text and schema to an LLM for structured extraction."""
        ...
        
    def research(self, product_info: str, collection: models.ResearchCollection) -> ResearchResult:
        """Executes both discovery and extraction in a single pass."""
        ...


@dataclasses.dataclass(frozen=True)
class FirecrawlGeminiResearcher:
    ai_client: genai.Client
    fc_app: FirecrawlApp
    model_name: str = "gemini-2.5-flash"

    def discover(self, product_info: str) -> DiscoveryResult:
        search_results = self.fc_app.search(
            query=f"{product_info} technical specifications reviews",
            limit=1,
            scrape_options={"formats": ["markdown"], "onlyMainContent": True}
        )
        
        # In firecrawl-py v4, search results are placed under .web (or .data in v1)
        items = []
        if hasattr(search_results, "web") and search_results.web:
            items = search_results.web
        elif hasattr(search_results, "data") and search_results.data:
            items = search_results.data
        elif isinstance(search_results, dict):
            items = search_results.get("web") or search_results.get("data") or []
        
        # NOTE: some versions of firecrawl return a dictionary wrapped in a dictionary 
        # (e.g. {'web': [{'url': ...}]}). The check above handles it if search_results is a dict.
        
        # Pydantic BaseModels can be converted to dict
        if not items and hasattr(search_results, "model_dump"):
            dump = search_results.model_dump()
            items = dump.get("web") or dump.get("data") or []

        if not items:
            raise ValueError(f"No search results found for: {product_info}")
            
        top_result = items[0]
        
        # Extract markdown and URL safely across Document / SearchResultWeb / dict types
        raw_source_text = getattr(top_result, "markdown", None)
        source_url = getattr(top_result, "url", None)
        
        if not source_url and hasattr(top_result, "metadata") and top_result.metadata:
            source_url = getattr(top_result.metadata, "url", None) or getattr(top_result.metadata, "source_url", None)
            
        if isinstance(top_result, dict):
            raw_source_text = raw_source_text or top_result.get("markdown")
            source_url = source_url or top_result.get("url")
            if not source_url and "metadata" in top_result and isinstance(top_result["metadata"], dict):
                source_url = top_result["metadata"].get("url") or top_result["metadata"].get("source_url")
                
        # If scrape_options wasn't returned inline, fall back to scraping the URL directly
        if source_url and not raw_source_text:
            scrape_res = self.fc_app.scrape(source_url)
            raw_source_text = getattr(scrape_res, "markdown", None) or (scrape_res.get("markdown") if isinstance(scrape_res, dict) else None)

        if not source_url or not raw_source_text:
            raise ValueError("Firecrawl returned incomplete data (missing url or markdown).")
            
        return DiscoveryResult(source_url=str(source_url), raw_source_text=str(raw_source_text))

    def extract(self, text: str, collection: models.ResearchCollection) -> dict[str, typing.Any]:
        import json
        response = self.ai_client.models.generate_content(
            model=self.model_name,
            contents=f"Analyze the source text below and extract specifications.\n\nContext:\n{text}",
            config=types.GenerateContentConfig(
                system_instruction=collection.extraction_prompt,
                response_mime_type="application/json",
                response_schema=collection.research_schema.model_dump(exclude_none=True)
            ),
        )
        # The SDK returns the structured output as a JSON string in response.text
        return json.loads(response.text)
        
    def research(self, product_info: str, collection: models.ResearchCollection) -> ResearchResult:
        discovery = self.discover(product_info)
        extracted = self.extract(discovery.raw_source_text, collection)
        return ResearchResult(
            source_url=discovery.source_url,
            raw_source_text=discovery.raw_source_text,
            extracted_data=extracted
        )
