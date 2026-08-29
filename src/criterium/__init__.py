from .database import ResearchDB, ResearchDBTables
from .models import ResearchCollection, ResearchReference, Product, ResearchCollectionList, ProductCollection
from .exceptions import CriteriumError, CollectionNotFoundError, ProductNotFoundError, SourceUrlAlreadyExistsError
from .research import Researcher, FirecrawlGeminiResearcher, GeminiSearchResearcher, DiscoveryResult, ResearchResult
from .schema_generation import CollectionSuggester, GeminiCollectionSuggester
from . import schemas
from .client import CriteriumClient

def hello() -> str:
    return "Hello from criterium!"

