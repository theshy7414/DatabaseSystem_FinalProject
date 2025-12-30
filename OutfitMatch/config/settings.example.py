"""
Configuration settings for OutfitMatch
Copy this file to settings.py and fill in your credentials
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Instagram Credentials
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', '')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', '')

# Neo4j Configuration
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# PostgreSQL Configuration (Legacy - will be removed)
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'outfitmatch')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

# Server Configuration
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '8000'))

# Model Configuration
USE_CUDA = os.getenv('USE_CUDA', 'true').lower() == 'true'
SEGMENTATION_MODEL = os.getenv('SEGMENTATION_MODEL', 'mattmdjaga/segformer_b2_clothes')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'facebook/dinov2-base')

# LLM Configuration
DEFAULT_LLM_MODEL = os.getenv('DEFAULT_LLM_MODEL', 'gpt-4o-mini')  # Use cheaper model by default
STYLE_PREDICTION_MODEL = os.getenv('STYLE_PREDICTION_MODEL', 'gpt-4o-mini')
NL2CYPHER_MODEL = os.getenv('NL2CYPHER_MODEL', 'gpt-4o')  # Use better model for query generation

# Cache Configuration
ENABLE_QUERY_CACHE = os.getenv('ENABLE_QUERY_CACHE', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))  # 1 hour
