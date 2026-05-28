import logging
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # noqa: E402

from docstream_api.database import init_db  # noqa: E402
from docstream_api.routes.convert import router as convert_router  # noqa: E402
from docstream_api.routes.feedback import router as feedback_router  # noqa: E402
from docstream_api.routes.health import router as health_router  # noqa: E402
from docstream_api.utils.file_handler import cleanup_old_jobs  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    cleanup_old_jobs()
    result = subprocess.run(["which", "xelatex"], capture_output=True, text=True)
    logger.info(f"xelatex location: {result.stdout.strip()}")
    logger.info(f"xelatex found: {bool(result.stdout.strip())}")
    yield


app = FastAPI(
    title="Docstream API",
    description="AI-powered PDF to LaTeX conversion API.",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(convert_router)
app.include_router(feedback_router)
app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "Docstream API", "docs": "/docs"}
