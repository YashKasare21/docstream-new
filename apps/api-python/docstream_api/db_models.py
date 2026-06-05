"""SQLAlchemy ORM models for the DocStream API.

Tables are created automatically via ``Base.metadata.create_all(engine)``
on application startup — no Alembic migrations needed. The SQLite file
lives at a project-relative path (``DOCSTREAM_DB_PATH`` or the default
``docstream.db`` in the API package directory) so jobs survive container
restarts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC ``now`` for default column values."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class Job(Base):
    """Persistent record for a single conversion request.

    Status transitions:
        ``processing`` -> ``completed`` on success
        ``processing`` -> ``failed``    on error
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    input_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    output_format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processing")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    output_pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_tex_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"Job(id={self.id!r}, status={self.status!r}, "
            f"template={self.template!r}, output_format={self.output_format!r})"
        )

    def to_dict(self) -> dict:
        """Serialise the job to a JSON-friendly dict.

        Download URLs are not included here — the route layer adds them
        once it knows whether the file paths exist on disk.
        """
        return {
            "id": self.id,
            "input_filename": self.input_filename,
            "template": self.template,
            "output_format": self.output_format,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "output_pdf_path": self.output_pdf_path,
            "output_tex_path": self.output_tex_path,
            "error_message": self.error_message,
        }


__all__ = ["Base", "Job", "utcnow"]
