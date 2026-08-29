from .database import ResearchDB, ResearchDBTables
from .models import ResearchCollection, ResearchReference, Product, ResearchJob, ResearchCollectionList, ProductCollection, ResearchJobCollection
from .exceptions import CriteriumError, CollectionNotFoundError, ProductNotFoundError, ResearchJobNotFoundError, SourceUrlAlreadyExistsError
from .research import Researcher, FirecrawlGeminiResearcher, GeminiSearchResearcher, DiscoveryResult, ResearchResult
from .jobs import ResearchJobWorker
from .schema_generation import CollectionSuggester, GeminiCollectionSuggester
from . import schemas
from .client import CriteriumClient

def hello() -> str:
    return "Hello from criterium!"

