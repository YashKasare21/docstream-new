import asyncio
import logging
import os
import shutil
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # noqa: E402

from docstream_api.database import init_db  # noqa: E402
from docstream_api.routes.compile import router as compile_router  # noqa: E402
from docstream_api.routes.convert import router as convert_router  # noqa: E402
from docstream_api.routes.feedback import router as feedback_router  # noqa: E402
from docstream_api.routes.health import router as health_router  # noqa: E402
from docstream_api.utils.file_handler import cleanup_old_jobs  # noqa: E402
from docstream_api.utils.rate_limit import limiter  # noqa: E402

logger = logging.getLogger(__name__)

TEMP_BASE = Path("/tmp/docstream")


async def _cleanup_loop():
    """Background task: delete /tmp/docstream jobs older than 1 hour."""
    while True:
        await asyncio.sleep(3600)
        if not TEMP_BASE.exists():
            continue
        now = time.time()
        for job_dir in TEMP_BASE.iterdir():
            if job_dir.is_dir():
                age = now - job_dir.stat().st_mtime
                if age > 3600:
                    shutil.rmtree(job_dir, ignore_errors=True)
                    logger.info("Cleaned up expired job: %s", job_dir.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    cleanup_old_jobs()
    result = subprocess.run(["which", "xelatex"], capture_output=True, text=True)
    logger.info(f"xelatex location: {result.stdout.strip()}")
    logger.info(f"xelatex found: {bool(result.stdout.strip())}")
    if not result.stdout.strip():
        raise RuntimeError("xelatex binary not found. DocStream cannot start.")

    # Attach rate limiter to app state
    app.state.limiter = limiter

    # Start background cleanup task
    cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("Background cleanup task started (every 3600s)")

    yield

    # Shutdown: cancel cleanup task
    cleanup_task.cancel()
    logger.info("Background cleanup task cancelled")


app = FastAPI(
    title="Docstream API",
    description="AI-powered PDF to LaTeX conversion API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(compile_router)
app.include_router(convert_router)
app.include_router(feedback_router)
app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "Docstream API", "docs": "/docs"}
