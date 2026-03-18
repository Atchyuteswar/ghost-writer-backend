"""Tests for the Upload endpoint."""
import os
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sample_exports")


def test_upload_whatsapp_valid():
    """Valid WhatsApp file upload returns 200 and parsed messages."""
    filepath = os.path.join(SAMPLE_DIR, "sample_whatsapp.txt")
    with open(filepath, "rb") as f:
        resp = client.post("/upload", files={"file": ("chat.txt", f, "text/plain")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] > 0
    assert "whatsapp" in data["platform_breakdown"]
    assert isinstance(data["messages"], list)


def test_upload_discord_valid():
    """Valid Discord JSON file upload returns 200."""
    filepath = os.path.join(SAMPLE_DIR, "sample_discord.json")
    with open(filepath, "rb") as f:
        resp = client.post("/upload", files={"file": ("export.json", f, "application/json")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] > 0
    assert "discord" in data["platform_breakdown"]


def test_upload_wrong_file_type():
    """Wrong file type returns 415."""
    resp = client.post("/upload", files={"file": ("test.pdf", b"fake content", "application/pdf")})
    assert resp.status_code == 415


def test_upload_empty_file():
    """Empty file returns 422."""
    resp = client.post("/upload", files={"file": ("chat.txt", b"", "text/plain")})
    assert resp.status_code == 422


def test_whatsapp_media_omitted_skipped():
    """WhatsApp 'Media omitted' lines are skipped."""
    content = b"[18/03/2025, 09:00:00] Aryan: hello\n[18/03/2025, 09:01:00] Aryan: <Media omitted>\n[18/03/2025, 09:02:00] Priya: hey"
    resp = client.post("/upload", files={"file": ("chat.txt", content, "text/plain")})
    data = resp.json()
    # Should have 2 messages (media omitted skipped)
    assert data["total_count"] == 2
    texts = [m["text"] for m in data["messages"]]
    assert not any("media omitted" in t.lower() for t in texts)


def test_whatsapp_multibubble_stitched():
    """WhatsApp multi-bubble messages are stitched correctly."""
    content = b"[18/03/2025, 09:00:00] Aryan: hey listen\nthis is very important\nlike actually\n[18/03/2025, 09:01:00] Priya: ok"
    resp = client.post("/upload", files={"file": ("chat.txt", content, "text/plain")})
    data = resp.json()
    assert data["total_count"] == 2
    first_msg = data["messages"][0]
    assert "this is very important" in first_msg["text"]
    assert "like actually" in first_msg["text"]
