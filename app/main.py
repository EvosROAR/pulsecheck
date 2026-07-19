from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.core.config import get_settings
from app.core.database import init_db
from app.routers import auth_router, monitors_router
from app.schemas import HealthResponse
from app.services.scheduler import scheduler_loop
from app.web import router as web_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    settings = get_settings()
    stop_event = asyncio.Event()
    scheduler_task: asyncio.Task | None = None
    if settings.scheduler_enabled:
        scheduler_task = asyncio.create_task(scheduler_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        if scheduler_task is not None:
            await scheduler_task


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Async website uptime & performance monitoring API. "
            "Register monitors, trigger checks, and track uptime statistics."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    application.include_router(web_router)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(monitors_router, prefix="/api/v1")

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name, version=__version__)

    return application


app = create_app()


def run() -> None:
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
