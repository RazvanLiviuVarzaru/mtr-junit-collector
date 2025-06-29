import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.logger import logger as fastapi_logger
from prometheus_fastapi_instrumentator import Instrumentator
from sqlmodel import SQLModel

from app.api.endpoints import router
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
Instrumentator().instrument(app).expose(app)

# Configure logging
if os.getenv("GUNICORN_HOST"):
    root_logger = logging.getLogger()
    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    log_level = gunicorn_error_logger.level

    # Use gunicorn error handlers for root, uvicorn, and fastapi loggers
    root_logger.handlers = gunicorn_error_logger.handlers
    uvicorn_access_logger.handlers = gunicorn_error_logger.handlers
    fastapi_logger.handlers = gunicorn_error_logger.handlers

    # Pass on logging levels for root, uvicorn, and fastapi loggers
    root_logger.setLevel(log_level)
    uvicorn_access_logger.setLevel(log_level)
    fastapi_logger.setLevel(log_level)
