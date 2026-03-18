"""Tests for the Analyze endpoint."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLE_MESSAGES = [
    {
        "id": "1",
        "timestamp": "2025-03-18T10:00:00",
        "sender": "Aryan",
        "text": "hey whats up bro lol this is actually pretty cool ngl",
        "platform": "whatsapp",
        "word_count": 11,
        "char_count": 52,
    },
    {
        "id": "2",
        "timestamp": "2025-03-18T11:00:00",
        "sender": "Priya",
        "text": "omg yes literally this is so fire bestie frfr",
        "platform": "whatsapp",
        "word_count": 9,
        "char_count": 46,
    },
    {
        "id": "3",
        "timestamp": "2025-03-19T14:30:00",
        "sender": "Aryan",
        "text": "I think we should discuss this tomorrow at the meeting tbh",
        "platform": "discord",
        "word_count": 10,
        "char_count": 57,
    },
]


def test_analyze_empty_messages():
    """Empty messages array returns 422."""
    resp = client.post("/analyze", json={"messages": []})
    assert resp.status_code == 422


def test_analyze_valid_messages():
    """Valid messages return all expected fields."""
    resp = client.post("/analyze", json={"messages": SAMPLE_MESSAGES})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_messages" in data
    assert "avg_sentiment" in data
    assert "sentiment_by_day" in data
    assert "vocabulary_richness" in data
    assert "top_words" in data
    assert "top_slang" in data
    assert "platform_stats" in data
    assert "most_active_hour" in data
    assert "most_active_day" in data
    assert data["total_messages"] == 3


def test_analyze_sentiment_by_day_valid_keys():
    """sentiment_by_day keys are valid date strings."""
    resp = client.post("/analyze", json={"messages": SAMPLE_MESSAGES})
    data = resp.json()
    for key in data["sentiment_by_day"]:
        # Should be YYYY-MM-DD format
        parts = key.split("-")
        assert len(parts) == 3


def test_analyze_vocabulary_richness_range():
    """vocabulary_richness is between 0 and 1."""
    resp = client.post("/analyze", json={"messages": SAMPLE_MESSAGES})
    data = resp.json()
    assert 0 <= data["vocabulary_richness"] <= 1


def test_analyze_top_words_limit():
    """top_words list has at most 20 items."""
    resp = client.post("/analyze", json={"messages": SAMPLE_MESSAGES})
    data = resp.json()
    assert len(data["top_words"]) <= 20


def test_analyze_slang_frequency_range():
    """slang_frequency is between 0 and 1."""
    resp = client.post("/analyze", json={"messages": SAMPLE_MESSAGES})
    data = resp.json()
    assert 0 <= data["slang_frequency"] <= 1
