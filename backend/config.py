"""
Application settings — loaded from environment variables.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_host: str = "mysql"
    db_port: int = 3306
    db_name: str = "quizchatbot"
    db_user: str = "quizuser"
    db_pass: str = "quizpass"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000  # container-internal port (host port is 8200)

    # Ollama
    ollama_host: str = "http://host.docker.internal:11434"
    llm_model: str = "llama3"
    embed_model: str = "nomic-embed-text"

    # Security
    api_secret_key: str = "change_this_to_a_strong_secret_key"
    token_expire_hours: int = 24

    # ChromaDB collection name
    chroma_collection: str = "knowledge_base"

    # Admin
    admin_key: str = "admin123"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
