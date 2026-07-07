from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, repositories
from app.core.config import SQLITE_DB_PATH
from app.core.database import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database(SQLITE_DB_PATH)
    yield


app = FastAPI(title="AI Repository Assistant", lifespan=lifespan)

app.include_router(health.router)
app.include_router(repositories.router)
