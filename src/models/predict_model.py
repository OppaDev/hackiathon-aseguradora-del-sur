"""
Fase 9 — Integración del modelo ML en la app.

Carga los artefactos exportados desde el notebook de Colab.
Si los artefactos no existen → fallback silencioso a score de reglas.

Artefactos esperados en models/:
  fraud_model.pkl          → RandomForestClassifier
  isolation_forest.pkl     → IsolationForest
  scaler.pkl               → StandardScaler
  model_columns.json       → lista de feature columns
  metrics.json             → métricas del modelo
  shap_feature_importance.json → importancia SHAP
"""

import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

log = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


# ---------------------------------------------------------------------------
# Carga de artefactos
# ---------------------------------------------------------------------------

class ModelArtifacts:
    """Carga lazy de todos los artefactos del modelo."""

    def __init__(self, models_dir: Path = MODELS_DIR):
        self._dir   = models_dir
        self._rf    = None
        self._isof  = None
        self._scaler = None
        self._cols   = None
        self._metrics = None
        self._shap    = None
        self._loaded  = False
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        required = ["fraud_model.pkl", "scaler.pkl", "model_columns.json"]
        return all((self._dir / f).exists() for f in required)

    def load(self) -> bool:
        if self._loaded:
            return True
        if not self._available:
            log.info("Artefactos de modelo no encontrados — usando fallback por reglas")
            return False
        try:
            self._rf     = joblib.load(self._dir / "fraud_model.pkl")
            self._scaler = joblib.load(self._dir / "scaler.pkl")
            self._cols   = json.loads((self._dir / "model_columns.json").read_text())

            isof_path = self._dir / "isolation_forest.pkl"
            if isof_path.exists():
                self._isof = joblib.load(isof_path)

            metrics_path = self._dir / "metrics.json"
            if metrics_path.exists():
                self._metrics = json.loads(metrics_path.read_text())

            shap_path = self._dir / "shap_feature_importance.json"
            if shap_path.exists():
                self._shap = json.loads(shap_path.read_text())

            self._loaded = True
            log.info(f"Modelo cargado — F1={self._metrics.get('f1', '?')} AUC={self._metrics.get('auc_roc', '?')}")
            return True
        except Exception as e:
            log.warning(f"Error cargando modelo: {e} — usando fallback")
            self._loaded = False
            return False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def rf(self):
        return self._rf

    @property
    def isof(self):
        return self._isof

    @property
    def scaler(self):
        return self._scaler

    @property
    def columns(self) -> list[str]:
        return self._cols or []

    @property
    def metrics(self) -> dict:
        return self._metrics or {}

    @property
    def shap_importance(self) -> dict:
        return self._shap or {}


# Singleton global
_artifacts = ModelArtifacts()


def load_artifacts(models_dir: Optional[str] = None) -> ModelArtifacts:
    """Carga (o recarga) los artefactos del modelo."""
    global _artifacts
    if models_dir:
        _artifacts = ModelArtifacts(Path(models_dir))
    _artifacts.load()
    return _artifacts


# ---------------------------------------------------------------------------
# Predicción
# ---------------------------------------------------------------------------

def _prepare_features(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Prepara la matriz de features para predicción."""
    X = pd.DataFrame(index=df.index)
    for col in columns:
        if col in df.columns:
            X[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            X[col] = 0.0

    # Booleanos → int
    for col in X.select_dtypes(include="bool").columns:
        X[col] = X[col].astype(int)

    # Imputar nulos con 0, forzar float64 limpio
    X = X.fillna(0).astype(float)
    return X


def predict_scores(df: pd.DataFrame, arts: Optional[ModelArtifacts] = None) -> pd.DataFrame:
    """
    Añade columnas de predicción ML al DataFrame.

    Columnas añadidas:
      - model_rf_score:    probabilidad RF de ser sospechoso (0-100)
      - model_isof_score:  score de anomalía Isolation Forest (0-100)
      - model_score:       score combinado (promedio RF + IsoF si ambos disponibles)
      - model_available:   True si se usó el modelo entrenado

    Si los modelos no están disponibles, score = score_reglas (fallback).
    """
    if arts is None:
        arts = _artifacts
        arts.load()

    df = df.copy()

    if not arts.available or not arts._loaded:
        # Fallback: usar score_reglas normalizado
        if "score_reglas" in df.columns:
            df["model_rf_score"]   = df["score_reglas"].clip(0, 100)
            df["model_isof_score"] = df["score_reglas"].clip(0, 100)
            df["model_score"]      = df["score_reglas"].clip(0, 100)
        else:
            df["model_rf_score"]   = 0.0
            df["model_isof_score"] = 0.0
            df["model_score"]      = 0.0
        df["model_available"] = False
        return df

    X = _prepare_features(df, arts.columns)

    # Random Forest score
    rf_proba = arts.rf.predict_proba(X)[:, 1] * 100
    df["model_rf_score"] = rf_proba.round(1)

    # Isolation Forest score
    if arts.isof is not None:
        X_scaled = arts.scaler.transform(X)
        # Eliminar NaN/Inf producidos por features con varianza cero en el scaler
        X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
        raw_scores = arts.isof.score_samples(X_scaled)
        s_min, s_max = raw_scores.min(), raw_scores.max()
        if s_max > s_min:
            isof_scores = ((s_min - raw_scores) / (s_min - s_max) * 100).clip(0, 100)
        else:
            isof_scores = np.zeros(len(df))
        df["model_isof_score"] = isof_scores.round(1)
        df["model_score"] = ((df["model_rf_score"] * 0.7 + df["model_isof_score"] * 0.3)
                             .clip(0, 100).round(1))
    else:
        df["model_isof_score"] = df["model_rf_score"]
        df["model_score"]      = df["model_rf_score"]

    df["model_available"] = True
    return df


def get_shap_explanation(id_siniestro: str, df: pd.DataFrame,
                         arts: Optional[ModelArtifacts] = None) -> list[dict]:
    """
    Devuelve las top-5 features que más contribuyen al score de este siniestro.
    Útil para el panel de explicabilidad en el dashboard.

    Requiere que 'shap' esté instalado y los artefactos cargados.
    """
    if arts is None:
        arts = _artifacts

    if not arts.available or not arts._loaded or not arts.shap_importance:
        # Fallback: devolver feature importance global del RF si existe
        return []

    row = df[df["id_siniestro"] == id_siniestro]
    if row.empty:
        return []

    try:
        import shap as shap_lib
        X = _prepare_features(row, arts.columns)
        explainer   = shap_lib.TreeExplainer(arts.rf)
        shap_vals   = explainer.shap_values(X)
        if isinstance(shap_vals, list):
            sv = shap_vals[1][0]
        else:
            sv = shap_vals[0]

        pairs = sorted(zip(arts.columns, sv), key=lambda x: abs(x[1]), reverse=True)
        return [
            {"feature": feat, "shap_value": round(float(val), 4),
             "direction": "aumenta riesgo" if val > 0 else "reduce riesgo"}
            for feat, val in pairs[:5]
        ]
    except Exception as e:
        log.warning(f"SHAP no disponible para {id_siniestro}: {e}")
        # Fallback: top-5 de importancia global
        top = sorted(arts.shap_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        return [{"feature": f, "shap_value": v, "direction": "global"} for f, v in top]


# ---------------------------------------------------------------------------
# Utilidades para el dashboard
# ---------------------------------------------------------------------------

def get_model_info(arts: Optional[ModelArtifacts] = None) -> dict:
    """Devuelve metadatos del modelo para mostrar en el dashboard."""
    if arts is None:
        arts = _artifacts
        arts.load()

    if not arts.available:
        return {
            "disponible": False,
            "mensaje": "Modelo no entrenado. Ejecuta el notebook de Colab para entrenar.",
            "instrucciones": "notebooks/entrenamiento_colab.ipynb",
        }

    return {
        "disponible":   arts._loaded,
        "metricas":     arts.metrics,
        "n_features":   len(arts.columns),
        "top_features": list(arts.shap_importance.items())[:10] if arts.shap_importance else [],
    }


if __name__ == "__main__":
    import sys
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    claims_path = root / "data" / "processed" / "claims_with_documents.csv"

    arts = load_artifacts()
    info = get_model_info(arts)
    print(f"\n{'='*55}")
    print(f"  Modelo disponible: {info['disponible']}")
    if not info['disponible']:
        print(f"  {info.get('mensaje', '')}")
    else:
        print(f"  Métricas: {info['metricas']}")

    df = pd.read_csv(claims_path)
    df = predict_scores(df, arts)

    print(f"\n  score_modelo (fallback={not arts._loaded}):")
    print(f"    Media:  {df['model_score'].mean():.1f}")
    print(f"    Máximo: {df['model_score'].max():.1f}")
    print(f"\n  Top 5 por model_score:")
    for _, r in df.nlargest(5, "model_score")[["id_siniestro", "model_score"]].iterrows():
        print(f"    {r['id_siniestro']}: {r['model_score']:.1f}")
