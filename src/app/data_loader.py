"""
Carga y caché de datos para el dashboard.
Centraliza todos los pd.read_csv y la integración con los modelos.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st
import logging

from src.models.predict_model import ModelArtifacts, predict_scores, get_model_info, MODELS_DIR
from src.ai_agent.claims_agent import get_agent_status

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]

# Rutas canónicas
PATHS = {
    "claims_with_docs": ROOT / "data" / "processed" / "claims_with_documents.csv",
    "claims_scored":    ROOT / "data" / "processed" / "claims_scored.csv",
    "claims_nlp":       ROOT / "data" / "processed" / "claims_nlp.csv",
    "network_edges":    ROOT / "data" / "processed" / "network_edges.csv",
    "model_scores":     ROOT / "models" / "model_scores.csv",
}


@st.cache_data(show_spinner=False)
def load_main_dataframe() -> pd.DataFrame:
    """
    DataFrame principal: claims_with_documents + scores + ML scores + NLP.
    Columnas clave garantizadas: id_siniestro, score_riesgo, nivel_riesgo, etc.
    """
    # Base: datos con documentos
    df = pd.read_csv(PATHS["claims_with_docs"])

    # Scores del motor de reglas
    if PATHS["claims_scored"].exists():
        scored = pd.read_csv(PATHS["claims_scored"])
        score_cols = [c for c in scored.columns if c != "id_siniestro"]
        df = df.merge(scored[["id_siniestro"] + score_cols], on="id_siniestro", how="left")

    # Scores ML del Colab (si existen)
    if PATHS["model_scores"].exists():
        ml = pd.read_csv(PATHS["model_scores"])
        if "score_random_forest" in ml.columns:
            df = df.merge(ml[["id_siniestro", "score_random_forest", "score_isolation_forest"]],
                          on="id_siniestro", how="left")

    # Enriquecimiento con columnas NLP
    if PATHS["claims_nlp"].exists():
        nlp = pd.read_csv(PATHS["claims_nlp"])
        nlp_cols = [c for c in nlp.columns if c.startswith("nlp_") and c not in df.columns]
        if nlp_cols:
            df = df.merge(nlp[["id_siniestro"] + nlp_cols], on="id_siniestro", how="left")

    # Enriquecimiento con scores del modelo (predict_scores integra modelo si está disponible)
    arts = _load_artifacts_cached()
    if arts.available:
        df = predict_scores(df, arts)

    return df


@st.cache_resource(show_spinner=False)
def _load_artifacts_cached() -> ModelArtifacts:
    arts = ModelArtifacts(MODELS_DIR)
    arts.load()
    return arts


@st.cache_data(show_spinner=False)
def load_network_edges() -> pd.DataFrame:
    if PATHS["network_edges"].exists():
        return pd.read_csv(PATHS["network_edges"])
    return pd.DataFrame(columns=["source", "target", "weight", "tipo_relacion"])


def get_data_status() -> dict:
    """Estado de disponibilidad de datos para mostrar en sidebar."""
    return {
        "claims_con_docs": PATHS["claims_with_docs"].exists(),
        "claims_scored":   PATHS["claims_scored"].exists(),
        "claims_nlp":      PATHS["claims_nlp"].exists(),
        "network_edges":   PATHS["network_edges"].exists(),
        "model_artifacts": (MODELS_DIR / "fraud_model.pkl").exists(),
        "model_scores":    PATHS["model_scores"].exists(),
        "agent":           get_agent_status(),
    }
