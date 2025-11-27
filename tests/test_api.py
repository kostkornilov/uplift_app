import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

BASIC_PAYLOAD = {
    "recency": 5,
    "history": 2300,
    "zip_code": "Suburban",
    "channel": "Web",
    "is_referral": True,
    "used_discount": False,
    "used_bogo": True,
}


def test_health_endpoint_reports_models_loaded(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["models_loaded"] is True


def test_predict_endpoint_returns_expected_structure(test_client):
    response = test_client.post("/predict", json=BASIC_PAYLOAD)
    assert response.status_code == 200
    payload = response.json()

    decision = payload.get("decision")
    assert decision is not None
    assert decision["best_offer"] in {"Discount", "Buy One Get One", "No Offer"}
    assert isinstance(decision["best_uplift"], float)
    assert "uplift_discount" in decision
    assert "uplift_bogo" in decision

    offers = payload.get("offers")
    assert isinstance(offers, dict)
    for offer_name in ("Discount", "Buy One Get One"):
        assert offer_name in offers
        for key in ("treated_probability", "control_probability", "uplift"):
            assert isinstance(offers[offer_name][key], float)


def test_predict_infers_features_by_copying_payload(test_client):
    # toggle some boolean flags to ensure toggling does not crash
    payload = BASIC_PAYLOAD.copy()
    payload["is_referral"] = False
    payload["used_discount"] = True
    payload["used_bogo"] = False

    response = test_client.post("/predict", json=payload)
    assert response.status_code == 200
    full = response.json()
    assert full["features"]["is_referral"] == 0
    assert full["features"]["used_discount"] == 1
    assert full["features"]["used_bogo"] == 0