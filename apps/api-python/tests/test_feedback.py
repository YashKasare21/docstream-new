"""Tests for POST /api/v2/feedback and GET /api/v2/feedback/stats."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with a fresh isolated SQLite DB for every test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)

    # Reload database so DB_PATH is picked up fresh
    from docstream_api import database  # noqa: PLC0415

    importlib.reload(database)
    database.init_db()

    # Patch database functions used by routes.feedback
    from docstream_api.routes import feedback as fb  # noqa: PLC0415

    fb.insert_feedback = database.insert_feedback
    fb.get_stats = database.get_stats

    from docstream_api import main  # noqa: PLC0415

    return TestClient(main.app)


# ── helper ────────────────────────────────────────────────────────────────────


def _post_feedback(client, *, emoji_rating=4, comment=None, job_id="job-1"):
    payload: dict = {"job_id": job_id, "emoji_rating": emoji_rating}
    if comment is not None:
        payload["comment"] = comment
    return client.post("/api/v2/feedback", json=payload)


# ── submission tests ──────────────────────────────────────────────────────────


def test_submit_feedback_success(client):
    resp = _post_feedback(client, emoji_rating=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["feedback_id"] is not None


def test_submit_feedback_all_emoji_ratings(client):
    for rating in range(1, 6):
        resp = _post_feedback(client, emoji_rating=rating, job_id=f"job-{rating}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


def test_submit_feedback_without_comment(client):
    resp = _post_feedback(client, comment=None)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_submit_feedback_with_comment(client):
    resp = _post_feedback(client, comment="Great tool!")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_submit_invalid_rating_rejected(client):
    resp = client.post("/api/v2/feedback", json={"job_id": "j", "emoji_rating": 6})
    assert resp.status_code == 422


def test_submit_invalid_rating_zero_rejected(client):
    resp = client.post("/api/v2/feedback", json={"job_id": "j", "emoji_rating": 0})
    assert resp.status_code == 422


# ── stats tests ───────────────────────────────────────────────────────────────


def test_get_stats_empty(client):
    resp = client.get("/api/v2/feedback/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 0
    assert data["average_rating"] == 0.0


def test_get_stats_after_submissions(client):
    for rating in (3, 4, 5):
        _post_feedback(client, emoji_rating=rating, job_id=f"job-{rating}")

    resp = client.get("/api/v2/feedback/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert data["average_rating"] == 4.0


def test_get_stats_distribution(client):
    for rating in (1, 1, 5, 5, 5):
        _post_feedback(client, emoji_rating=rating)

    resp = client.get("/api/v2/feedback/stats")
    dist = resp.json()["rating_distribution"]
    assert dist["1"] == 2
    assert dist["5"] == 3


def test_get_stats_recent_comments(client):
    for i in range(3):
        _post_feedback(client, comment=f"Comment {i}", job_id=f"job-{i}")

    resp = client.get("/api/v2/feedback/stats")
    comments = resp.json()["recent_comments"]
    assert len(comments) == 3
