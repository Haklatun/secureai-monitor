"""
Tests for AI detection engine.
"""
import pytest
import numpy as np
from app.services.ai_engine import (
    score_embedding,
    classify_severity,
    embed_log,
    _load_or_init_model,
)


def test_model_loads():
    model = _load_or_init_model()
    assert model is not None


def test_score_range():
    embedding = np.random.default_rng(0).random(384).astype(np.float32)
    score = score_embedding(embedding)
    assert 0.0 <= score <= 1.0


def test_embed_log_shape():
    vec = embed_log("brute_force_attempt", {"attempts": 50, "ip": "1.2.3.4"})
    assert vec.shape == (384,)


def test_classify_severity_high_keyword():
    sev = classify_severity(0.3, "sql_injection_attempt", 200, "1.2.3.4")
    assert sev == "high"


def test_classify_severity_score_based():
    assert classify_severity(0.85, "login_event", 200, None) == "critical"
    assert classify_severity(0.70, "login_event", 200, None) == "high"
    assert classify_severity(0.50, "login_event", 200, None) == "medium"
    assert classify_severity(0.20, "login_event", 200, None) == "low"


def test_classify_severity_401_escalates():
    sev = classify_severity(0.55, "auth_failure", 401, "5.6.7.8")
    assert sev == "high"


@pytest.mark.asyncio
async def test_process_log_pipeline():
    from app.services.ai_engine import process_log
    result = await process_log(
        event_type="login_failure",
        payload={"attempts": 3},
        source_ip="10.0.0.1",
        status_code=401,
    )
    assert "embedding" in result
    assert "anomaly_score" in result
    assert "severity" in result
    assert "is_anomaly" in result
    assert isinstance(result["embedding"], list)
    assert len(result["embedding"]) == 384
