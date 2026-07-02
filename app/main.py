from fastapi import FastAPI

from app.api.routes import health, repositories

app = FastAPI(title="AI Repository Assistant")

app.include_router(health.router)
app.include_router(repositories.router)
