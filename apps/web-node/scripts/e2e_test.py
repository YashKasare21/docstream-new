#!/usr/bin/env python3
"""
Docstream v2 — End-to-end test script.
Tests the full pipeline with real files.

Usage:
  cd docstream-api
  source .venv/bin/activate
  python ../scripts/e2e_test.py

Prerequisites:
  - uvicorn running on port 8000  (uvicorn main:app --reload)
  - At least one AI provider key set in .env
"""

import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"


def test_health() -> None:
    print("Testing health endpoint...")
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.json()["status"] == "ok"
    print("  ✅ Health OK")


def test_providers() -> None:
    print("Testing AI providers...")
    r = requests.get(f"{BASE_URL}/api/v2/providers", timeout=10)
    assert r.status_code == 200
    data = r.json()
    available = [p["name"] for p in data["providers"] if p["available"]]
    print(f"  Available providers: {available}")
    if not available:
        print("  ⚠️  No AI providers available.")
        print("     Set GEMINI_API_KEY or GROQ_API_KEY in .env")
        sys.exit(1)
    print("  ✅ Providers OK")


def test_formats() -> None:
    print("Testing formats endpoint...")
    r = requests.get(f"{BASE_URL}/api/v2/formats", timeout=5)
    assert r.status_code == 200
    formats = [f["extension"] for f in r.json()["formats"]]
    print(f"  Supported: {formats}")
    print("  ✅ Formats OK")


def create_test_pdf() -> Path:
    """Create a minimal multi-paragraph test PDF using PyMuPDF."""
    import fitz  # type: ignore

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        (
            "Test Document\n\n"
            "Abstract\n\n"
            "This is a test document created for the Docstream v2 pipeline.\n\n"
            "Introduction\n\n"
            "This document validates extract → analyze → match → render.\n\n"
            "Methodology\n\n"
            "Each stage of the pipeline is exercised with real content.\n\n"
            "Results\n\n"
            "All conversion stages completed without error.\n\n"
            "Conclusion\n\n"
            "The Docstream v2 pipeline is functioning correctly."
        ),
        fontsize=12,
    )
    path = Path("/tmp/test_docstream_e2e.pdf")
    doc.save(str(path))
    doc.close()
    return path


def test_convert_pdf(template: str = "report") -> bool:
    print(f"\nTesting PDF conversion (template={template})...")
    pdf_path = create_test_pdf()

    start = time.time()
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/v2/convert",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"template": template},
            timeout=120,
        )
    elapsed = time.time() - start

    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()

    if not data["success"]:
        print(f"  ❌ Conversion failed: {data.get('error')}")
        return False

    print(f"  ✅ Converted in {elapsed:.1f}s")
    print(f"     Document type:  {data.get('document_type', 'n/a')}")
    print(f"     Quality score:  {data.get('quality_score', 'n/a')}")
    print(f"     TEX URL:        {data['tex_url']}")
    print(f"     PDF URL:        {data['pdf_url']}")

    job_id = data["job_id"]

    # Verify TEX download
    tex_r = requests.get(f"{BASE_URL}/api/v2/files/{job_id}/document.tex", timeout=10)
    assert tex_r.status_code == 200, "TEX download failed"
    print(f"     TEX download:   {len(tex_r.content)} bytes ✅")

    # Verify PDF download
    pdf_r = requests.get(f"{BASE_URL}/api/v2/files/{job_id}/document.pdf", timeout=10)
    assert pdf_r.status_code == 200, "PDF download failed"
    print(f"     PDF download:   {len(pdf_r.content)} bytes ✅")

    return True


def test_feedback(job_id: str = "test-job-e2e") -> None:
    print("\nTesting feedback system...")
    r = requests.post(
        f"{BASE_URL}/api/v2/feedback",
        json={
            "job_id": job_id,
            "emoji_rating": 5,
            "comment": "E2E test feedback — pipeline working!",
        },
        timeout=5,
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    stats_r = requests.get(f"{BASE_URL}/api/v2/feedback/stats", timeout=5)
    assert stats_r.status_code == 200
    stats = stats_r.json()
    assert stats["total_count"] >= 1
    print(f"  ✅ Feedback OK (total submissions: {stats['total_count']})")


def test_path_traversal_blocked() -> None:
    """Security: ensure ../.. filenames are rejected."""
    print("\nTesting path traversal protection...")
    r = requests.get(
        f"{BASE_URL}/api/v2/files/any-job/../../etc/passwd", timeout=5
    )
    assert r.status_code in (400, 404), f"Expected 400/404, got {r.status_code}"
    print("  ✅ Path traversal blocked")


if __name__ == "__main__":
    print("=" * 55)
    print("  Docstream v2 — End-to-End Test")
    print("=" * 55)

    try:
        test_health()
        test_providers()
        test_formats()
        test_convert_pdf("report")
        test_convert_pdf("ieee")
        test_feedback()
        test_path_traversal_blocked()

        print("\n" + "=" * 55)
        print("  ✅  ALL TESTS PASSED")
        print("=" * 55)

    except AssertionError as exc:
        print(f"\n❌  TEST FAILED: {exc}")
        sys.exit(1)
    except requests.ConnectionError:
        print("\n❌  Cannot connect to backend.")
        print("    Start it with:  uvicorn main:app --reload")
        sys.exit(1)
