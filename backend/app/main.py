import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1 import jobs, system
from backend.app.config.settings import settings
from backend.app.core.errors import BrollForgeException, brollforge_exception_handler, generic_exception_handler
from backend.app.core.logging import correlation_id_ctx, logger
from backend.app.db.session import Base, engine
from backend.app.services.footage.local_pack import LocalLicensedFootageProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and local verified media pack is ready
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.APP_ENV})")
    Base.metadata.create_all(bind=engine)
    try:
        LocalLicensedFootageProvider()
    except Exception as e:
        logger.warning(f"Could not pre-initialize local pack: {e}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title="BrollForge API",
    version=settings.APP_VERSION,
    description="Enterprise Script and Voiceover to B-roll Video Engine (IncuBrix Engineering Assessment 3)",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID and Request Logging Middleware
@app.middleware("http")
async def correlation_and_logging_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    token = correlation_id_ctx.set(corr_id)
    start_time = time.time()

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Correlation-Id"] = corr_id
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)")
        return response
    finally:
        correlation_id_ctx.reset(token)


# Exception Handlers
app.add_exception_handler(BrollForgeException, brollforge_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Mount Routes
app.include_router(system.router)
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="")  # allows /broll/jobs as well


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API v{settings.APP_VERSION}",
        "documentation": "/docs",
        "health": "/health",
    }
