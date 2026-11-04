from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.account import router
from config.settings import Database, Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            await database.engine.dispose()

    application = FastAPI(title="Account API", lifespan=lifespan)
    application.state.settings = settings
    application.state.database = database
    application.include_router(router)
    return application


app = create_app()
