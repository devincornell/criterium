from .database import ResearchDB, ResearchDBTables
from .models import ResearchCollection, Product, ResearchCollectionList, ProductCollection, ResearchSchema
from .exceptions import CriteriumError, CollectionNotFoundError, ProductNotFoundError, SourceUrlAlreadyExistsError
from .research import Researcher, FirecrawlGeminiResearcher, DiscoveryResult, ResearchResult
from . import schemas
from .client import CriteriumClient

def hello() -> str:
    return "Hello from criterium!"

