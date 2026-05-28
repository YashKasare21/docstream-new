"""SQLite database helpers for the feedback system."""

import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "/tmp/docstream/feedback.db")


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB file if needed."""
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict-like row access
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id               TEXT PRIMARY KEY,
                job_id           TEXT NOT NULL,
                emoji_rating     INTEGER NOT NULL CHECK(emoji_rating BETWEEN 1 AND 5),
                comment          TEXT,
                template_used    TEXT,
                document_type    TEXT,
                processing_time  REAL,
                created_at       TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_created_at
            ON feedback(created_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_emoji_rating
            ON feedback(emoji_rating)
        """)

        conn.commit()
    finally:
        conn.close()


def insert_feedback(feedback: dict) -> str:
    """Insert a feedback record and return the generated UUID."""
    import uuid
    from datetime import datetime, timezone

    feedback_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO feedback
                (id, job_id, emoji_rating, comment,
                 template_used, document_type, processing_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                feedback["job_id"],
                feedback["emoji_rating"],
                feedback.get("comment"),
                feedback.get("template_used"),
                feedback.get("document_type"),
                feedback.get("processing_time"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return feedback_id
    finally:
        conn.close()


def get_stats() -> dict:
    """Return aggregated feedback statistics."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) AS total, AVG(emoji_rating) AS avg_rating
            FROM feedback
        """).fetchone()

        total: int = row["total"] or 0
        avg_rating: float = round(row["avg_rating"] or 0.0, 2)

        dist_rows = conn.execute("""
            SELECT emoji_rating, COUNT(*) AS count
            FROM feedback
            GROUP BY emoji_rating
            ORDER BY emoji_rating
        """).fetchall()

        distribution = {str(r["emoji_rating"]): r["count"] for r in dist_rows}

        comment_rows = conn.execute("""
            SELECT comment FROM feedback
            WHERE comment IS NOT NULL AND length(trim(comment)) > 0
            ORDER BY created_at DESC
            LIMIT 5
        """).fetchall()

        comments = [r["comment"] for r in comment_rows]

        return {
            "total_count": total,
            "average_rating": avg_rating,
            "rating_distribution": distribution,
            "recent_comments": comments,
        }
    finally:
        conn.close()
