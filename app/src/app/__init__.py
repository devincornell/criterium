import criterium
from google import genai
from firecrawl import FirecrawlApp
from .config import settings

def main() -> None:
    message = criterium.hello()
    print(f"App says: {message}")
    
    # Initialize your clients using the pydantic settings
    # We use get_secret_value() because we defined them as SecretStr to prevent accidental logging
    ai_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    fc_app = FirecrawlApp(api_key=settings.firecrawl_api_key.get_secret_value())
    
    print("API Clients initialized successfully!")
