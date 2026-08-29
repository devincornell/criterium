import datetime
from types import SimpleNamespace

import pytest
from firecrawl.types import Document, DocumentMetadata, ScrapeOptions, SearchResultWeb

from criterium.models import ResearchCollection
from criterium.research import FirecrawlGeminiResearcher, GeminiSearchResearcher
from criterium.schemas import ResearchSchemaObject, ResearchSchemaString


def make_collection() -> ResearchCollection:
    return ResearchCollection(
        id=1,
        name="Books",
        extraction_prompt="Extract the title.",
        research_schema=ResearchSchemaObject(
            properties={"title": ResearchSchemaString()}
        ),
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


class FakeGeminiModels:
    def __init__(self, include_citations: bool = True) -> None:
        self.calls = []
        self.include_citations = include_citations

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            chunks = []
            if self.include_citations:
                chunks = [
                    SimpleNamespace(
                        web=SimpleNamespace(
                            uri="https://example.com/source",
                            title="Source",
                        )
                    )
                ]
            metadata = SimpleNamespace(grounding_chunks=chunks)
            candidate = SimpleNamespace(grounding_metadata=metadata)
            return SimpleNamespace(text="Grounded evidence", candidates=[candidate])
        return SimpleNamespace(text='{"title": "Example"}', candidates=[])


def test_gemini_research_uses_search_then_structured_extraction() -> None:
    models = FakeGeminiModels()
    researcher = GeminiSearchResearcher(
        ai_client=SimpleNamespace(models=models),
    )

    result = researcher.research("Example book", make_collection())

    assert result.extracted_data == {"title": "Example"}
    assert result.references[0].url == "https://example.com/source"
    assert models.calls[0]["config"].tools[0].google_search is not None
    assert models.calls[1]["config"].response_schema["required"] == ["title"]
    assert models.calls[1]["config"].response_schema["properties"]["title"]["nullable"] is True
    assert "return null" in models.calls[1]["config"].system_instruction.lower()


def test_gemini_research_requires_grounded_sources() -> None:
    researcher = GeminiSearchResearcher(
        ai_client=SimpleNamespace(models=FakeGeminiModels(include_citations=False)),
    )

    with pytest.raises(ValueError, match="no grounded web source"):
        researcher.research("Example book", make_collection())


class FakeFirecrawl:
    def __init__(self, inline_markdown: bool) -> None:
        self.inline_markdown = inline_markdown
        self.scraped = False

    def search(self, **kwargs):
        assert isinstance(kwargs["scrape_options"], ScrapeOptions)
        if self.inline_markdown:
            return SimpleNamespace(
                web=[
                    Document(
                        markdown="Inline evidence",
                        metadata=DocumentMetadata(source_url="https://example.com/inline"),
                    )
                ]
            )
        return SimpleNamespace(web=[SearchResultWeb(url="https://example.com/fallback")])

    def scrape(self, url: str, **kwargs):
        self.scraped = True
        return Document(markdown="Fallback evidence")


@pytest.mark.parametrize("inline_markdown", [True, False])
def test_firecrawl_discovery_handles_inline_and_fallback_content(inline_markdown: bool) -> None:
    firecrawl = FakeFirecrawl(inline_markdown)
    researcher = FirecrawlGeminiResearcher(
        ai_client=SimpleNamespace(),
        fc_app=firecrawl,
    )

    result = researcher.discover("Example book")

    assert result.raw_source_text.endswith("evidence")
    assert firecrawl.scraped is not inline_markdown
