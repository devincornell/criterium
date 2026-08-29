import typing
import dataclasses
from google import genai
from google.genai import types
from firecrawl import Firecrawl
from firecrawl.types import Document, ScrapeOptions
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
    fc_app: Firecrawl
    model_name: str = "gemini-2.5-flash"

    def discover(self, product_info: str) -> DiscoveryResult:
        search_results = self.fc_app.search(
            query=f"{product_info} technical specifications reviews",
            limit=1,
            scrape_options=ScrapeOptions(
                formats=["markdown"],
                only_main_content=True,
            ),
        )

        items = search_results.web or []

        if not items:
            raise ValueError(f"No search results found for: {product_info}")

        top_result = items[0]

        if isinstance(top_result, Document):
            metadata = top_result.metadata_typed
            source_url = metadata.source_url or metadata.url
            raw_source_text = top_result.markdown
        else:
            source_url = top_result.url
            raw_source_text = None

        if source_url and not raw_source_text:
            scraped = self.fc_app.scrape(
                source_url,
                formats=["markdown"],
                only_main_content=True,
            )
            raw_source_text = scraped.markdown

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
