# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file located in the same directory (backend/)
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    # It's better practice to require SECRET_KEY from env, not provide a weak default
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        print("WARNING: SECRET_KEY not set in environment variables! Using a default (INSECURE).")
        SECRET_KEY = 'you-will-never-guess-CHANGE-ME' # Still provide a fallback but warn

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db') # Default to SQLite if not set
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- AI Assistant Config ---
    # URL for your locally running Ollama server
    OLLAMA_URL = os.environ.get('OLLAMA_URL') or 'http://localhost:11434'
    # Default LLM model to use with Ollama
    OLLAMA_DEFAULT_MODEL = os.environ.get('OLLAMA_DEFAULT_MODEL') or 'llama3:8b'
    # Default embedding model
    OLLAMA_EMBEDDING_MODEL = os.environ.get('OLLAMA_EMBEDDING_MODEL') or 'nomic-embed-text'

    # --- RAG Config ---
    # Path for ChromaDB persistent storage
    VECTOR_DB_PATH = os.environ.get('VECTOR_DB_PATH') or os.path.join(basedir, 'vector_db')
    VECTOR_DB_COLLECTION = os.environ.get('VECTOR_DB_COLLECTION') or 'nexus_documents'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Add any production-specific configs here (e.g., logging)

# Select configuration based on FLASK_ENV or default to Development
config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig
)

key = os.getenv('FLASK_ENV', 'development')
app_config = config_by_name[key]
