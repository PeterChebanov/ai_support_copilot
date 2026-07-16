from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.config import settings
from api.routes.ask import router as ask_router
from api.routes.health import router as health_router
from api.routes.ingest import router as ingest_router
from api.routes.retrieve import router as retrieve_router
from db.session import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(settings.database_url)
    yield


app = FastAPI(
    title="AI Support Copilot",
    description="Local RAG support knowledge assistant",
    version="0.7.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(retrieve_router)
app.include_router(ask_router)
