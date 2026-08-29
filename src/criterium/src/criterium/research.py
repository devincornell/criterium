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
            scrapeOptions={"formats": ["markdown"], "onlyMainContent": True}
        )
        
        if not search_results or not search_results.get("data"):
            raise ValueError(f"No search results found for: {product_info}")
            
        top_result = search_results["data"][0]
        source_url = top_result.get("url", "")
        raw_source_text = top_result.get("markdown", "")
        
        if not source_url or not raw_source_text:
            raise ValueError("Firecrawl returned incomplete data (missing url or markdown).")
            
        return DiscoveryResult(source_url=source_url, raw_source_text=raw_source_text)

    def extract(self, text: str, collection: models.ResearchCollection) -> dict[str, typing.Any]:
        import json
        response = self.ai_client.models.generate_content(
            model=self.model_name,
            contents=f"Analyze the source text below and extract specifications.\n\nContext:\n{text}",
            config=types.GenerateContentConfig(
                system_instruction=collection.extraction_prompt,
                response_mime_type="application/json",
                response_schema=collection.llm_schema
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
