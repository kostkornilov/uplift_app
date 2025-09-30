from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Literal
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import warnings

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Data"

DISCOUNT_MODEL_PATH = DATA_DIR / "s_learner_discount_model.pkl"
BOGO_MODEL_PATH = DATA_DIR / "s_learner_bogo_model.pkl"

REQUIRED_MODEL_KEYS = {"model"}

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


class CustomerFeatures(BaseModel):
    recency: float = Field(..., ge=0, description="Months since the last purchase")
    history: float = Field(..., ge=0, description="Total spend over the last year")
    zip_code: str = Field(..., description="Customer zip-code cluster")
    channel: str = Field(..., description="Primary communication channel")
    is_referral: bool = Field(..., description="Came from referral program")
    used_discount: bool = Field(..., description="Used discounts in the past")
    used_bogo: bool = Field(..., description="Used buy-one-get-one offers in the past")


def _load_pickled_model(model_path: Path):
    """Load pickled model with multiple fallback strategies."""
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    try:
        model_obj = joblib.load(model_path)
        print(f"✓ Loaded {model_path.name} with joblib")
        return model_obj
    except Exception as e:
        print(f"✗ Joblib failed for {model_path.name}: {e}")
        raise RuntimeError(f"Failed to load model from {model_path}")



def _prepare_base_frame(payload: CustomerFeatures) -> pd.DataFrame:
    row: Dict[str, object] = {
        "recency": float(payload.recency),
        "history": float(payload.history),
        "zip_code": payload.zip_code,
        "channel": payload.channel,
        "is_referral": int(payload.is_referral),
        "used_discount": int(payload.used_discount),
        "used_bogo": int(payload.used_bogo),
    }

    df = pd.DataFrame([row])
    df["recency_log"] = np.log1p(df["recency"].astype(float))
    df["history_log"] = np.log1p(df["history"].astype(float))
    return df


def _score_s_learner(model, base_df: pd.DataFrame) -> Dict[str, float]:
    features = base_df[
        [
            "recency_log",
            "history_log",
            "zip_code",
            "channel",
            "is_referral",
            "used_discount",
            "used_bogo",
        ]
    ].copy()

    treated = features.copy()
    treated["treat"] = 1
    control = features.copy()
    control["treat"] = 0

    try:
        treated_proba = float(model.predict_proba(treated)[:, 1][0])
        control_proba = float(model.predict_proba(control)[:, 1][0])
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Model prediction failed") from exc

    uplift = treated_proba - control_proba
    return {
        "treated_probability": treated_proba,
        "control_probability": control_proba,
        "uplift": uplift,
    }


def _decide_best_offer(discount_scores: Dict[str, float], bogo_scores: Dict[str, float]) -> Dict[str, object]:
    uplift_discount = discount_scores["uplift"]
    uplift_bogo = bogo_scores["uplift"]

    best_offer: Literal["Discount", "Buy One Get One", "No Offer"]

    if uplift_discount <= 0 and uplift_bogo <= 0:
        best_offer = "No Offer"
        best_uplift = 0.0
    elif uplift_discount >= uplift_bogo:
        best_offer = "Discount"
        best_uplift = uplift_discount
    else:
        best_offer = "Buy One Get One"
        best_uplift = uplift_bogo

    return {
        "best_offer": best_offer,
        "best_uplift": best_uplift,
        "uplift_discount": uplift_discount,
        "uplift_bogo": uplift_bogo,
    }


app = FastAPI(title="Marketing Uplift API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    try:
        app.state.discount_model = _load_pickled_model(DISCOUNT_MODEL_PATH)
        app.state.bogo_model = _load_pickled_model(BOGO_MODEL_PATH)
    except Exception as exc:  # pragma: no cover - deployment-time error visibility
        raise RuntimeError(f"Failed to load models: {exc}") from exc


@app.post("/predict")
def predict_offer(payload: CustomerFeatures):
    discount_model = getattr(app.state, "discount_model", None)
    bogo_model = getattr(app.state, "bogo_model", None)

    if discount_model is None or bogo_model is None:
        startup_event()
        discount_model = app.state.discount_model
        bogo_model = app.state.bogo_model

    base_df = _prepare_base_frame(payload)

    discount_scores = _score_s_learner(discount_model, base_df)
    bogo_scores = _score_s_learner(bogo_model, base_df)

    decision = _decide_best_offer(discount_scores, bogo_scores)

    return {
        "decision": decision,
        "offers": {
            "Discount": discount_scores,
            "Buy One Get One": bogo_scores,
        },
        "features": {
            "recency": payload.recency,
            "history": payload.history,
            "zip_code": payload.zip_code,
            "channel": payload.channel,
            "is_referral": int(payload.is_referral),
            "used_discount": int(payload.used_discount),
            "used_bogo": int(payload.used_bogo),
            "recency_log": base_df["recency_log"].iloc[0],
            "history_log": base_df["history_log"].iloc[0],
        },
    }
