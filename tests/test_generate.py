"""Tests for the Generate endpoint."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_generate_empty_prompt():
    """Empty prompt returns 422."""
    resp = client.post("/generate", json={
        "prompt": "",
        "vibe_level": 50,
        "personality_type": "casual-bro",
    })
    assert resp.status_code == 422


def test_generate_invalid_vibe_too_low():
    """vibe_level < 0 returns 422."""
    resp = client.post("/generate", json={
        "prompt": "hello",
        "vibe_level": -1,
        "personality_type": "casual-bro",
    })
    assert resp.status_code == 422


def test_generate_invalid_vibe_too_high():
    """vibe_level > 100 returns 422."""
    resp = client.post("/generate", json={
        "prompt": "hello",
        "vibe_level": 101,
        "personality_type": "casual-bro",
    })
    assert resp.status_code == 422


def test_generate_invalid_personality():
    """Invalid personality_type returns 422."""
    resp = client.post("/generate", json={
        "prompt": "hello",
        "vibe_level": 50,
        "personality_type": "invalid-type",
    })
    assert resp.status_code == 422


def test_generate_valid_request():
    """Valid request returns response with all expected fields."""
    resp = client.post("/generate", json={
        "prompt": "Tell me about your weekend",
        "vibe_level": 75,
        "personality_type": "casual-bro",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "match_percent" in data
    assert "vibe_applied" in data
    assert "tokens_used" in data
    assert 0 <= data["match_percent"] <= 100
    assert data["vibe_applied"] == 75


def test_generate_prompts_endpoint():
    """GET /generate/prompts returns a list of prompts."""
    resp = client.get("/generate/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 10
