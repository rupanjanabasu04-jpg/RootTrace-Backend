from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import explanations
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.schemas.ai_explanation import AIExplanation
from app.services.ai_explanation import (
    AIExplanationConfigurationError,
    AIExplanationError,
    generate_ai_explanation,
)


INCIDENT_ID = UUID("12960106-adf8-483c-8ef3-fd2d462656c7")
SAMPLE_ANALYSIS = {
    "incident_id": str(INCIDENT_ID),
    "timeline": [],
    "temporal_correlations": [],
    "dependency_graph": [],
    "hypotheses": [
        {
            "id": "hypothesis-1",
            "title": "Checkout deployment regression",
            "final_score": 84,
            "confidence": "high",
        }
    ],
    "probable_cause": {
        "hypothesis_id": "hypothesis-1",
        "title": "Checkout deployment regression",
        "score": 84,
        "confidence": "high",
    },
}
SAMPLE_EXPLANATION = AIExplanation(
    what_happened=["The analyzer recorded a Checkout incident."],
    probable_cause="The analyzer ranked Checkout deployment regression as the probable cause.",
    why_it_was_ranked=["Evidence indicates it had the highest deterministic score."],
    evidence=["The analyzer supplied supporting evidence for the hypothesis."],
    possible_propagation=["Possible propagation should be investigated."],
    what_to_investigate_next=["Review the deployment and affected events."],
    uncertainty_and_limitations=["This is a probable cause, not certainty."],
)


class FakeResponses:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_parsed=self.result)


class FakeOpenAIClient:
    def __init__(self, result=None, error: Exception | None = None):
        self.responses = FakeResponses(result=result, error=error)


def test_generate_ai_explanation_uses_structured_outputs(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    client = FakeOpenAIClient(result=SAMPLE_EXPLANATION)

    explanation = generate_ai_explanation(SAMPLE_ANALYSIS, client=client)

    assert explanation == SAMPLE_EXPLANATION
    call = client.responses.calls[0]
    assert call["text_format"] is AIExplanation
    assert "tools" not in call
    assert "untrusted data" in call["input"][0]["content"]


def test_generate_ai_explanation_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)

    with pytest.raises(AIExplanationConfigurationError):
        generate_ai_explanation(SAMPLE_ANALYSIS, client=FakeOpenAIClient())


def test_generate_ai_explanation_wraps_provider_failure(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    client = FakeOpenAIClient(error=RuntimeError("provider unavailable"))

    with pytest.raises(AIExplanationError, match="provider request failed"):
        generate_ai_explanation(SAMPLE_ANALYSIS, client=client)


def test_generate_ai_explanation_rejects_invalid_structured_response(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    client = FakeOpenAIClient(result={"what_happened": []})

    with pytest.raises(AIExplanationError, match="invalid structured explanation"):
        generate_ai_explanation(SAMPLE_ANALYSIS, client=client)


def test_explanation_endpoint_preserves_deterministic_analysis(monkeypatch):
    def override_db():
        yield object()

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    monkeypatch.setattr(
        explanations,
        "analyze_incident",
        lambda incident_id, db: SAMPLE_ANALYSIS,
    )
    monkeypatch.setattr(
        explanations,
        "generate_ai_explanation",
        lambda analysis: SAMPLE_EXPLANATION,
    )

    client = TestClient(app)
    response = client.get(f"/api/v1/incidents/{INCIDENT_ID}/explanation")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"analysis", "explanation"}
    assert payload["analysis"] == SAMPLE_ANALYSIS
    assert payload["analysis"]["probable_cause"] == SAMPLE_ANALYSIS["probable_cause"]
    assert set(payload["explanation"]) == set(
        AIExplanation.model_fields
    )
