from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.exception_handlers import (
    http_exception_handler,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from speaches.dependencies import ApiKeyDependency, get_config, get_executor_registry
from speaches.logger import setup_logger
from speaches.routers.chat import (
    router as chat_router,
)
from speaches.routers.misc import (
    router as misc_router,
)
from speaches.routers.models import (
    router as models_router,
)
from speaches.routers.realtime.rtc import (
    router as realtime_rtc_router,
)
from speaches.routers.realtime.ws import (
    router as realtime_ws_router,
)
from speaches.routers.speech import (
    router as speech_router,
)
from speaches.routers.speech_embedding import (
    router as speech_embedding_router,
)
from speaches.routers.stt import (
    router as stt_router,
)
from speaches.routers.vad import (
    router as vad_router,
)
from speaches.utils import APIProxyError

# https://swagger.io/docs/specification/v3_0/grouping-operations-with-tags/
# https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-tags
TAGS_METADATA = [
    {"name": "automatic-speech-recognition"},
    {"name": "speech-to-text"},
    {"name": "speaker-embedding"},
    {"name": "realtime"},
    {"name": "models"},
    {"name": "diagnostic"},
    {
        "name": "experimental",
        "description": "Not meant for public use yet. May change or be removed at any time.",
    },
]

DEFAULT_MODELS = [
    "speaches-ai/Kokoro-82M-v1.0-ONNX",
    "Systran/faster-whisper-large-v3",
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger = logging.getLogger(__name__)
    logger.info("Downloading default models on startup...")
    executor_registry = get_executor_registry()
    for model_id in DEFAULT_MODELS:
        for executor in executor_registry.all_executors():
            if model_id in [model.id for model in executor.model_registry.list_remote_models()]:
                try:
                    was_downloaded = executor.model_registry.download_model_files_if_not_exist(model_id)
                    if was_downloaded:
                        logger.info(f"Downloaded default model: {model_id}")
                    else:
                        logger.info(f"Default model already exists: {model_id}")
                    break
                except Exception:
                    logger.exception(f"Failed to download default model: {model_id}")
    logger.info("Startup complete")
    yield
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    config = get_config()  # HACK
    setup_logger(config.log_level)
    logger = logging.getLogger(__name__)

    logger.debug(f"Config: {config}")

    # Create main app WITHOUT global authentication
    app = FastAPI(
        title="Speaches",
        version="0.8.3",  # TODO: update this on release
        license_info={"name": "MIT License", "identifier": "MIT"},
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # Register global exception handler for APIProxyError
    @app.exception_handler(APIProxyError)
    async def _api_proxy_error_handler(_request: Request, exc: APIProxyError) -> JSONResponse:
        error_id = str(uuid.uuid4())
        logger.exception(f"[{{error_id}}] {exc.message}")
        content = {
            "detail": exc.message,
            "hint": exc.hint,
            "suggested_fixes": exc.suggestions,
            "error_id": error_id,
        }

        # HACK: replace with something else
        log_level = os.getenv("SPEACHES_LOG_LEVEL", "INFO").upper()
        if log_level == "DEBUG" and exc.debug:
            content["debug"] = exc.debug
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(StarletteHTTPException)
    async def _custom_http_exception_handler(request: Request, exc: HTTPException) -> Response:
        logger.error(f"HTTP error: {exc}")
        return await http_exception_handler(request, exc)

    # HTTP routers WITH authentication (if API key is configured)
    http_dependencies = []
    if config.api_key is not None:
        http_dependencies.append(ApiKeyDependency)

    app.include_router(chat_router, dependencies=http_dependencies)
    app.include_router(stt_router, dependencies=http_dependencies)
    app.include_router(models_router, dependencies=http_dependencies)
    app.include_router(misc_router, dependencies=http_dependencies)
    app.include_router(realtime_rtc_router, dependencies=http_dependencies)
    app.include_router(speech_router, dependencies=http_dependencies)
    app.include_router(speech_embedding_router, dependencies=http_dependencies)
    app.include_router(vad_router, dependencies=http_dependencies)

    # WebSocket router WITHOUT authentication (handles its own)
    app.include_router(realtime_ws_router)

    if config.allow_origins is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return app
