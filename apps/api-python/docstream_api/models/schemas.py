"""Pydantic schemas for API request/response models."""

from typing import Optional

from pydantic import BaseModel, Field


class ConvertResponse(BaseModel):
    """Response from conversion endpoint."""

    success: bool
    job_id: str = ""
    tex_url: Optional[str] = None
    pdf_url: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    template_used: Optional[str] = None
    document_type: Optional[str] = None
    quality_score: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class FeedbackCreate(BaseModel):
    """Feedback submission request."""

    job_id: str
    emoji_rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    template_used: Optional[str] = None
    document_type: Optional[str] = None
    processing_time: Optional[float] = None


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    success: bool
    message: str
    feedback_id: Optional[str] = None


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics."""

    total_count: int
    average_rating: float
    rating_distribution: dict
    recent_comments: list[str]
