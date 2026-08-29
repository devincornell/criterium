from .database import ResearchDB, ResearchDBTables
from .models import ResearchCollection, Product, ResearchCollectionList, ProductCollection
from .exceptions import CriteriumError, CollectionNotFoundError, ProductNotFoundError, SourceUrlAlreadyExistsError
from .research import Researcher, FirecrawlGeminiResearcher, DiscoveryResult, ResearchResult

def hello() -> str:
    return "Hello from criterium!"

