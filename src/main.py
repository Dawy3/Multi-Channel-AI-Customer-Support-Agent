from fastapi import FastAPI
from routes import base_router, data_router, nlp_router
from helpers.config import get_settings
from stores.llm.llm_provider_factory import LLMProviderFactor
from stores.vectorDB.vectorDB_factory import VectorDBFactory
from stores.llm.templates.template_parser import TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from utils.metrics import setup_metrics

app = FastAPI()

# Setup Prometheus metrics
setup_metrics(app)

async def startup_span():
    settings = get_settings()
    
    # DB Client
    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    
    app.db_engine = create_async_engine(postgres_conn)
    
    app.db_client = sessionmaker(
        app.db_engine, class_=AsyncSession, expire_on_commit=False,
    )
    
    # LLM Factory
    llm_provider_factor = LLMProviderFactor(settings)
    
    # VectorDB Factory
    vector_db_factory = VectorDBFactory(config=settings, db_client=app.db_client) 
    
    # Generation client
    app.generation_client = llm_provider_factor.create(settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(settings.GENERATION_MODEL_ID)
    
    # Embedding client
    app.embedding_client = llm_provider_factor.create(settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(settings.EMBEDDING_MODEL_ID, settings.EMBEDDING_MODEL_SIZE)
    
    # Vector db client
    app.vectordb_client = vector_db_factory.create(provider=settings.VECTOR_DB_BACKEND)
    await app.vectordb_client.connect()
    
    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )
    
    
async def shutdown_span():
    await app.db_engine.dispose()
    await app.vectordb_client.disconnect()
    
app.add_event_handler("startup", startup_span)
app.add_event_handler("shutdown", shutdown_span)


app.include_router(base_router.base_router)
app.include_router(data_router.data_router)
app.include_router(nlp_router.nlp_router)
