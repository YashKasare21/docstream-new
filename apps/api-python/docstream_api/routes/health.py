import os

from fastapi import APIRouter

from docstream_api.models.schemas import HealthResponse


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the current API health status."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/v2/providers")
async def list_providers() -> dict:
    """Return AI provider status."""
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))

    providers: list[dict] = []
    if has_gemini:
        providers.append(
            {
                "name": "Gemini",
                "model": "gemini-2.0-flash",
                "available": True,
                "priority": 1,
            }
        )
    if has_groq:
        providers.append(
            {
                "name": "Groq",
                "model": "llama-3.3-70b-versatile",
                "available": True,
                "priority": 2,
            }
        )

    active = next((p["name"] for p in providers if p["available"]), None)
    return {"providers": providers, "active": active}
