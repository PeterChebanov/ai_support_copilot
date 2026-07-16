from fastapi import FastAPI

from api.routes.health import router as health_router

app = FastAPI(
    title="AI Support Copilot",
    description="Local RAG support knowledge assistant",
    version="0.1.0",
)

app.include_router(health_router)
