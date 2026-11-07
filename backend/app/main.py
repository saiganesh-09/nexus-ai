from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.ratelimit import RateLimitMiddleware

logger = get_logger("nexus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    logger.info(
        "service_starting",
        service=settings.app_name,
        environment=settings.environment,
        version=__version__,
    )
    from app.database.session import async_session_factory
    from app.services.chat import seed_model_catalog

    async with async_session_factory() as session:
        added = await seed_model_catalog(session)
        if added:
            logger.info("model_catalog_seeded", added=added)
    yield
    logger.info("service_stopping")


class MaxBodySizeMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def limited_receive():
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if len(body) > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "payload_too_large",
                                "message": "Request body exceeds the allowed size",
                                "details": None,
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, limited_receive, send)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Intelligent LLM Gateway & AI Operations Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
