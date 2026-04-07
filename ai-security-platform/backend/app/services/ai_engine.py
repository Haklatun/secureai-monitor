"""
AI Detection Engine
===================
- Generates text embeddings from log events (sentence-transformers)
- Detects anomalies using Isolation Forest
- Classifies severity based on anomaly score + heuristics
- Designed for async use; model is loaded once at startup
"""

from __future__ import annotations
import asyncio
import json
import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

MODEL_PATH = Path("/app/models/isolation_forest.pkl")
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

# Lazy-loaded globals
_embedder = None
_iforest: IsolationForest | None = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}. Using fallback.")
            _embedder = "fallback"
    return _embedder


def _fallback_embedding(text: str) -> np.ndarray:
    """Simple hash-based embedding when sentence-transformers unavailable."""
    rng = np.random.default_rng(abs(hash(text)) % (2**31))
    return rng.random(384).astype(np.float32)


def embed_log(event_type: str, payload: dict[str, Any]) -> np.ndarray:
    text = f"{event_type} {json.dumps(payload, default=str)[:256]}"
    embedder = _get_embedder()
    if embedder == "fallback":
        return _fallback_embedding(text)
    return embedder.encode(text, normalize_embeddings=True)


def _load_or_init_model() -> IsolationForest:
    global _iforest
    if _iforest is not None:
        return _iforest
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            _iforest = pickle.load(f)
        logger.info("Isolation Forest loaded from disk")
    else:
        _iforest = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1,
        )
        # Warm-start with random normal data so model is usable immediately
        warm_data = np.random.default_rng(42).normal(size=(500, 384))
        _iforest.fit(warm_data)
        _save_model(_iforest)
        logger.info("Isolation Forest initialized with warm-start data")
    return _iforest


def _save_model(model: IsolationForest) -> None:
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)


def score_embedding(embedding: np.ndarray) -> float:
    """Returns anomaly score in [0, 1]. Higher = more anomalous."""
    model = _load_or_init_model()
    vec = embedding.reshape(1, -1)
    raw = model.score_samples(vec)[0]          # negative: more anomalous = more negative
    # Normalise to [0, 1]
    score = float(1 / (1 + np.exp(raw * 5)))   # sigmoid transform
    return round(min(max(score, 0.0), 1.0), 4)


def classify_severity(
    anomaly_score: float,
    event_type: str,
    status_code: int | None,
    source_ip: str | None,
) -> str:
    # Rule-based overrides first
    high_keywords = {"injection", "brute", "privilege", "escalation", "exploit", "rce", "xss", "csrf"}
    if any(k in event_type.lower() for k in high_keywords):
        return "high"
    if status_code in (401, 403) and anomaly_score > 0.5:
        return "high"

    # Score-based classification
    if anomaly_score >= 0.80:
        return "critical"
    if anomaly_score >= 0.65:
        return "high"
    if anomaly_score >= 0.40:
        return "medium"
    return "low"


async def process_log(
    event_type: str,
    payload: dict[str, Any],
    source_ip: str | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: embed → score → classify.
    Returns dict with embedding, anomaly_score, severity, is_anomaly.
    Runs CPU work in executor to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()

    embedding = await loop.run_in_executor(
        None, embed_log, event_type, payload
    )
    anomaly_score = await loop.run_in_executor(
        None, score_embedding, embedding
    )

    from app.core.config import get_settings
    threshold = get_settings().anomaly_threshold
    is_anomaly = anomaly_score >= threshold
    severity = classify_severity(anomaly_score, event_type, status_code, source_ip)

    return {
        "embedding": embedding.tolist(),
        "anomaly_score": anomaly_score,
        "is_anomaly": is_anomaly,
        "severity": severity,
    }


async def retrain(embeddings: list[list[float]]) -> None:
    """Retrain model on recent embeddings."""
    if len(embeddings) < 50:
        logger.info("Not enough samples to retrain (%d)", len(embeddings))
        return

    data = np.array(embeddings, dtype=np.float32)

    def _fit():
        model = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(data)
        return model

    loop = asyncio.get_event_loop()
    new_model = await loop.run_in_executor(None, _fit)

    global _iforest
    _iforest = new_model
    _save_model(new_model)
    logger.info("Isolation Forest retrained on %d samples", len(embeddings))
