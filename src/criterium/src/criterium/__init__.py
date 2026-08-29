from .database import ResearchDB, ResearchDBTables
from .models import ResearchCollection, Product, ResearchCollectionList, ProductCollection
from .exceptions import CriteriumError, CollectionNotFoundError, ProductNotFoundError, SourceUrlAlreadyExistsError

def hello() -> str:
    return "Hello from criterium!"

