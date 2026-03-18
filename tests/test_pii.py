"""Tests for the PII endpoint."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

MESSAGES_WITH_PII = [
    {
        "id": "1",
        "timestamp": "2025-03-18T10:00:00",
        "sender": "Aryan",
        "text": "call me at 555-123-4567 or email me at aryan@example.com",
        "platform": "whatsapp",
        "word_count": 10,
        "char_count": 55,
    },
    {
        "id": "2",
        "timestamp": "2025-03-18T11:00:00",
        "sender": "Priya",
        "text": "sure my number is +1-555-987-6543",
        "platform": "whatsapp",
        "word_count": 7,
        "char_count": 33,
    },
]


def test_pii_mask_phone_enabled():
    """Phone numbers are masked when setting is True."""
    resp = client.post("/pii/mask", json={
        "messages": MESSAGES_WITH_PII,
        "settings": {
            "mask_phone_numbers": True,
            "mask_email_addresses": False,
            "mask_real_names": False,
            "mask_locations": False,
            "mask_financial_info": False,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    # At least one message should have been masked
    assert data["masked_count"] > 0
    # Phone numbers should be replaced
    for msg in data["messages"]:
        assert "555-123-4567" not in msg["text"]


def test_pii_mask_phone_disabled():
    """Phone numbers are NOT masked when setting is False."""
    resp = client.post("/pii/mask", json={
        "messages": MESSAGES_WITH_PII,
        "settings": {
            "mask_phone_numbers": False,
            "mask_email_addresses": False,
            "mask_real_names": False,
            "mask_locations": False,
            "mask_financial_info": False,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    # No masking should happen
    assert data["masked_count"] == 0


def test_pii_mask_email_enabled():
    """Email addresses are masked when setting is True."""
    resp = client.post("/pii/mask", json={
        "messages": MESSAGES_WITH_PII,
        "settings": {
            "mask_phone_numbers": False,
            "mask_email_addresses": True,
            "mask_real_names": False,
            "mask_locations": False,
            "mask_financial_info": False,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["masked_count"] > 0
    for msg in data["messages"]:
        assert "aryan@example.com" not in msg["text"]


def test_pii_mask_breakdown_keys():
    """Mask breakdown dict keys match entity types."""
    resp = client.post("/pii/mask", json={
        "messages": MESSAGES_WITH_PII,
        "settings": {
            "mask_phone_numbers": True,
            "mask_email_addresses": True,
            "mask_real_names": False,
            "mask_locations": False,
            "mask_financial_info": False,
        },
    })
    data = resp.json()
    valid_keys = {"PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "LOCATION", "GPE", "MONEY", "CREDIT_CARD"}
    for key in data["mask_breakdown"]:
        assert key in valid_keys


def test_pii_status_endpoint():
    """GET /pii/status returns expected fields."""
    resp = client.get("/pii/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "presidio_loaded" in data
    assert "supported_entities" in data
    assert isinstance(data["supported_entities"], list)
