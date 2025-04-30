from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API"""
    api_key: str
    model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-ada-002"
    max_retries: int = 3
    timeout: int = 30
    organization: Optional[str] = None

def get_openai_config() -> OpenAIConfig:
    """Get OpenAI configuration from environment variables"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
        
    return OpenAIConfig(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
        timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
        organization=os.getenv("OPENAI_ORGANIZATION")
    ) 