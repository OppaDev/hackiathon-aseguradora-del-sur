"""
Tests para src/models/predict_model.py.

Como los artefactos de modelo se generan en Colab, los tests cubren:
- La interfaz y el modo fallback (sin artefactos)
- La carga y validación de artefactos cuando existen (simulados)
- Las funciones de utilidad para el dashboard
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json
import joblib
import tempfile

from src.models.predict_model import (
    ModelArtifacts,
    load_artifacts,
    predict_scores,
    get_model_info,
    MODELS_DIR,
)

ROOT        = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "data" / "processed" / "claims_with_documents.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


@pytest.fixture(scope="module")
def arts_no_model() -> ModelArtifacts:
    """Artefactos sin modelo (directorio vacío)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ModelArtifacts(Path(tmpdir))


@pytest.fixture(scope="session")
def fake_models_dir(tmp_path_factory):
    """
    Crea artefactos simulados mínimos para probar la carga.
    Usa un RandomForestClassifier real entrenado sobre datos sintéticos.
    """
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler

    tmpdir = tmp_path_factory.mktemp("models")

    feature_cols = [
        "monto_reclamado", "dias_desde_inicio_poliza",
        "similitud_narrativa", "ratio_monto_suma",
        "doc_factura_alterada", "proveedor_lista_restrictiva",
    ]

    # Datos sintéticos mínimos
    np.random.seed(42)
    X = pd.DataFrame(
        np.random.rand(100, len(feature_cols)),
        columns=feature_cols
    )
    y = (X["monto_reclamado"] > 0.7).astype(int)

    rf     = RandomForestClassifier(n_estimators=10, random_state=42)
    isof   = IsolationForest(n_estimators=10, random_state=42)
    scaler = StandardScaler()

    rf.fit(X, y)
    scaler.fit(X)
    isof.fit(scaler.transform(X))

    joblib.dump(rf,     tmpdir / "fraud_model.pkl")
    joblib.dump(isof,   tmpdir / "isolation_forest.pkl")
    joblib.dump(scaler, tmpdir / "scaler.pkl")

    (tmpdir / "model_columns.json").write_text(
        json.dumps(feature_cols)
    )
    (tmpdir / "metrics.json").write_text(json.dumps(
        {"precision": 0.80, "recall": 0.75, "f1": 0.77, "auc_roc": 0.85,
         "cv_f1_mean": 0.76}
    ))
    (tmpdir / "shap_feature_importance.json").write_text(json.dumps(
        {col: round(np.random.rand(), 4) for col in feature_cols}
    ))

    return tmpdir


@pytest.fixture(scope="session")
def arts_with_model(fake_models_dir):
    arts = ModelArtifacts(fake_models_dir)
    arts.load()
    return arts


# ---------------------------------------------------------------------------
# ModelArtifacts — modo sin modelo
# ---------------------------------------------------------------------------

class TestModelArtifactsNoModel:
    def test_not_available(self, arts_no_model):
        assert arts_no_model.available is False

    def test_load_returns_false(self, arts_no_model):
        assert arts_no_model.load() is False

    def test_columns_empty(self, arts_no_model):
        assert arts_no_model.columns == []

    def test_metrics_empty(self, arts_no_model):
        assert arts_no_model.metrics == {}


# ---------------------------------------------------------------------------
# ModelArtifacts — modo con modelo simulado
# ---------------------------------------------------------------------------

class TestModelArtifactsWithModel:
    def test_available(self, arts_with_model):
        assert arts_with_model.available is True

    def test_loaded(self, arts_with_model):
        assert arts_with_model._loaded is True

    def test_columns_present(self, arts_with_model):
        assert len(arts_with_model.columns) > 0

    def test_metrics_present(self, arts_with_model):
        assert "f1" in arts_with_model.metrics
        assert "auc_roc" in arts_with_model.metrics

    def test_shap_present(self, arts_with_model):
        assert len(arts_with_model.shap_importance) > 0

    def test_rf_is_sklearn_model(self, arts_with_model):
        from sklearn.ensemble import RandomForestClassifier
        assert isinstance(arts_with_model.rf, RandomForestClassifier)


# ---------------------------------------------------------------------------
# predict_scores — fallback
# ---------------------------------------------------------------------------

class TestPredictScoresFallback:
    def test_columnas_presentes(self, df, arts_no_model):
        result = predict_scores(df, arts_no_model)
        for col in ["model_rf_score", "model_isof_score", "model_score", "model_available"]:
            assert col in result.columns

    def test_model_available_false(self, df, arts_no_model):
        result = predict_scores(df, arts_no_model)
        assert (result["model_available"] == False).all()

    def test_shape_igual(self, df, arts_no_model):
        result = predict_scores(df, arts_no_model)
        assert len(result) == len(df)

    def test_scores_en_rango(self, df, arts_no_model):
        result = predict_scores(df, arts_no_model)
        assert (result["model_score"] >= 0).all()
        assert (result["model_score"] <= 100).all()


# ---------------------------------------------------------------------------
# predict_scores — con modelo simulado
# ---------------------------------------------------------------------------

class TestPredictScoresWithModel:
    def test_model_available_true(self, df, arts_with_model):
        result = predict_scores(df, arts_with_model)
        assert (result["model_available"] == True).all()

    def test_rf_scores_en_rango(self, df, arts_with_model):
        result = predict_scores(df, arts_with_model)
        assert (result["model_rf_score"] >= 0).all()
        assert (result["model_rf_score"] <= 100).all()

    def test_isof_scores_en_rango(self, df, arts_with_model):
        result = predict_scores(df, arts_with_model)
        assert (result["model_isof_score"] >= 0).all()
        assert (result["model_isof_score"] <= 100).all()

    def test_shape_igual(self, df, arts_with_model):
        result = predict_scores(df, arts_with_model)
        assert len(result) == len(df)


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------

class TestGetModelInfo:
    def test_sin_modelo(self, arts_no_model):
        info = get_model_info(arts_no_model)
        assert info["disponible"] is False
        assert "mensaje" in info

    def test_con_modelo(self, arts_with_model):
        info = get_model_info(arts_with_model)
        assert info["disponible"] is True
        assert "metricas" in info
        assert "f1" in info["metricas"]
