from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str
    
    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    
    FILE_DEFAULT_CHUNK_SIZE: int
    
    
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int 
    POSTGRES_MAIN_DATABASE: str
    # ================================= LLM Config ================================
    GENERATION_BACKEND : str
    EMBEDDING_BACKEND : str

    OPENAI_API_KEY: str = None
    OPENAI_BASE_URL: str = None
    COHERE_API_KEY: str = None


    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: int = None

    INPUT_DEFAULT_MAX_CHARACTERS: int = None
    GENERATION_DEFAULT_MAX_TOKENS: int = None
    GENERATION_DEFAULT_TEMPERATURE: float = None

    # Max number of prior chat-history messages sent after the system prompt
    CHAT_HISTORY_LIMIT: int = 10
    
    # ================================= OCR ============================================
    OCR_BACKEND : str            # MISTRAL or GEMENAI
    MISTRAL_API_KEY : str 
    GEMENAI_API_KEY : str
    
    # ================================= VectorDB Config ================================
    VECTOR_DB_BACKEND: str 
    VECTOR_DB_PATH: str 
    VECTOR_DB_DISTANCE_METHOD: str = None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int = 100
    # ================================= Template Configs ================================
    PRIMARY_LANG: str
    DEFAULT_LANG: str 

        
    model_config = SettingsConfigDict(env_file=".env")
    
def get_settings():
    return Settings()
