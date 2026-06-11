"""
SQLAlchemy ORM models for the DocStream API.

Tables are created automatically via ``Base.metadata.create_all(engine)``
on application startup — no Alembic migrations needed. The SQLite file
lives at a project-relative path (``DOCSTREAM_DB_PATH`` or the default
``docstream.db`` in the API package directory) so data survives container
restarts.

User model
----------
Users are created on first interaction (when a JWT-authenticated request
hits a protected endpoint). The relationship between ``User`` and ``Job``
is implicit via ``User.email == Job.user_id`` — there is no foreign key
constraint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC ``now`` for default column values."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class User(Base):
    """Registered user linked to a Stripe subscription.

    ``email`` is the join key to ``Job.user_id`` — no FK constraint.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    plan: Mapped[str] = mapped_column(String(16), nullable=False, default="free")
    monthly_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reset_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"User(id={self.id!r}, email={self.email!r}, "
            f"plan={self.plan!r}, monthly_usage={self.monthly_usage})"
        )


class Job(Base):
    """Persistent record for a single conversion request.

    Status transitions:
        ``processing`` -> ``completed`` on success
        ``processing`` -> ``failed``    on error

    ``user_id`` is a plain string (the user's email). The implicit
    relationship with ``User`` is via ``User.email == Job.user_id``.
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(256), nullable=False, default="anonymous")
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
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
            "user_id": self.user_id,
            "input_filename": self.input_filename,
            "template": self.template,
            "output_format": self.output_format,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "output_pdf_path": self.output_pdf_path,
            "output_tex_path": self.output_tex_path,
            "error_message": self.error_message,
            "page_count": self.page_count,
            "token_count": self.token_count,
        }


__all__ = ["Base", "User", "Job", "utcnow"]
