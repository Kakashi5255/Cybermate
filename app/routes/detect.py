# app/routes/detect.py
# API endpoint for ScamBot detection.
# Accepts input text, evaluates with ML model and rule engine,
# and returns a classification verdict with supporting details.

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.storage import load_artifacts
from app.services.rules import eval_rules
import numpy as np

router = APIRouter(prefix="/detect", tags=["detect"])

# Load the trained model and vectorizer from storage
MODEL, VECT = load_artifacts()

class DetectIn(BaseModel):
    """Request body schema for the detection endpoint."""
    text: str

@router.post("")
def detect(inp: DetectIn):
    """
    Detect potential scams in a given text.
    Combines machine learning score with rule-based heuristics
    and applies thresholds to return a final verdict.
    """
    t = (inp.text or "").strip()
    if not t:
        return {
            "verdict": "Unclear",
            "score_ml": 0.0,
            "score_rules": 0,
            "highlights": [],
            "reasons": ["No text provided."]
        }

    # Generate ML score
    X = VECT.transform([t])
    if hasattr(MODEL, "predict_proba"):
        score_ml = float(MODEL.predict_proba(X)[0, 1])
    elif hasattr(MODEL, "decision_function"):
        raw = float(MODEL.decision_function(X)[0])
        score_ml = 1 / (1 + np.exp(-raw))
    else:
        # Fallback to binary prediction
        score_ml = float(MODEL.predict(X)[0])

    # Apply rule-based evaluation
    rule_score, hits, reasons = eval_rules(t)

    # Combine results with threshold policy (precision-first)
    if (score_ml >= 0.80) and (rule_score >= 3):
        verdict = "Likely Scam"
    elif (0.55 <= score_ml < 0.80) or (2 <= rule_score < 3):
        verdict = "Unclear"
    else:
        verdict = "Unlikely"

    return {
        "verdict": verdict,
        "score_ml": round(score_ml, 3),
        "score_rules": int(rule_score),
        "highlights": hits,
        "reasons": reasons
    }
