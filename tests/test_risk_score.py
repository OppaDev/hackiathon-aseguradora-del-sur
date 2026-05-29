"""
Tests para src/scoring/risk_score.py — usan claims_with_documents.csv real.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.scoring.risk_score import (
    compute_scores,
    _normalize_rules,
    _score_nlp,
    _classify,
    run,
)

ROOT          = Path(__file__).resolve().parents[1]
CLAIMS_PATH   = ROOT / "data" / "processed" / "claims_with_documents.csv"
SCORED_PATH   = ROOT / "data" / "processed" / "claims_scored.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df_raw() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


@pytest.fixture(scope="module")
def df_scored(df_raw) -> pd.DataFrame:
    return compute_scores(df_raw)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

class TestNormalizacion:
    def test_normalize_rules_cero(self):
        s = _normalize_rules(pd.Series([0.0]))
        assert s.iloc[0] == 0.0

    def test_normalize_rules_maximo(self):
        from src.scoring.risk_score import MAX_RULE_POINTS
        s = _normalize_rules(pd.Series([MAX_RULE_POINTS]))
        assert s.iloc[0] == 100.0

    def test_normalize_rules_clip_over_max(self):
        from src.scoring.risk_score import MAX_RULE_POINTS
        s = _normalize_rules(pd.Series([MAX_RULE_POINTS * 2]))
        assert s.iloc[0] == 100.0

    def test_nlp_score_desde_similitud(self):
        s = _score_nlp(pd.Series([0.85]))
        assert abs(s.iloc[0] - 85.0) < 0.1

    def test_nlp_score_cero(self):
        s = _score_nlp(pd.Series([0.0]))
        assert s.iloc[0] == 0.0


class TestClasificacion:
    def test_score_0_es_bajo(self):
        assert _classify(0) == "BAJO"

    def test_score_30_es_bajo(self):
        assert _classify(30) == "BAJO"

    def test_score_31_es_medio(self):
        assert _classify(31) == "MEDIO"

    def test_score_65_es_medio(self):
        assert _classify(65) == "MEDIO"

    def test_score_66_es_alto(self):
        assert _classify(66) == "ALTO"

    def test_score_100_es_alto(self):
        assert _classify(100) == "ALTO"


# ---------------------------------------------------------------------------
# compute_scores con datos reales
# ---------------------------------------------------------------------------

class TestComputeScores:
    def test_shape_igual(self, df_raw, df_scored):
        assert len(df_scored) == len(df_raw)

    def test_columnas_score_presentes(self, df_scored):
        for col in ["score_riesgo", "nivel_riesgo", "recomendacion",
                    "explicacion_score", "score_reglas", "score_documental",
                    "score_nlp", "score_modelo", "modelo_fallback"]:
            assert col in df_scored.columns, f"Falta: {col}"

    def test_scores_en_rango(self, df_scored):
        assert (df_scored["score_riesgo"] >= 0).all()
        assert (df_scored["score_riesgo"] <= 100).all()

    def test_niveles_validos(self, df_scored):
        validos = {"BAJO", "MEDIO", "ALTO"}
        assert set(df_scored["nivel_riesgo"].unique()).issubset(validos)

    def test_sin0005_nivel_alto(self, df_scored):
        row = df_scored[df_scored["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["nivel_riesgo"] == "ALTO"

    def test_sin0005_score_maximo(self, df_scored):
        row = df_scored[df_scored["id_siniestro"] == "SIN-0005"].iloc[0]
        # SIN-0005 debe ser el caso con mayor score
        assert row["score_riesgo"] == df_scored["score_riesgo"].max()

    def test_sin0005_score_sobre_70(self, df_scored):
        row = df_scored[df_scored["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["score_riesgo"] >= 70

    def test_distribución_razonable(self, df_scored):
        # Al menos 5% MEDIO/ALTO (señales de riesgo reales en el dataset)
        alto_medio = (df_scored["nivel_riesgo"].isin(["MEDIO", "ALTO"])).sum()
        assert alto_medio >= 25  # >= 5% de 500

    def test_casos_alto_tienen_alertas(self, df_scored):
        altos = df_scored[df_scored["nivel_riesgo"] == "ALTO"]
        assert len(altos) >= 1
        assert (altos["rule_alerts"] != "").all()

    def test_modelo_fallback_sin_modelo(self, df_scored):
        assert df_scored["modelo_fallback"].all()  # sin modelo entrenado

    def test_explicaciones_no_vacias_en_medio_alto(self, df_scored):
        medio_alto = df_scored[df_scored["nivel_riesgo"].isin(["MEDIO", "ALTO"])]
        assert (medio_alto["explicacion_score"] != "").all()

    def test_sub_scores_consistentes(self, df_scored):
        # score_documental == 0 para siniestros sin PDFs
        sin_pdf = df_scored[df_scored["n_pdfs_extraidos"] == 0]
        assert (sin_pdf["score_documental"] == 0).all()

    def test_recomendacion_bajo(self, df_scored):
        bajos = df_scored[df_scored["nivel_riesgo"] == "BAJO"]
        assert (bajos["recomendacion"].str.contains("flujo normal")).all()

    def test_recomendacion_alto(self, df_scored):
        altos = df_scored[df_scored["nivel_riesgo"] == "ALTO"]
        assert (altos["recomendacion"].str.contains("Detener")).all()


# ---------------------------------------------------------------------------
# Pipeline run → CSV
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_csv_generado(self):
        run(str(CLAIMS_PATH), str(SCORED_PATH))
        assert SCORED_PATH.exists()

    def test_csv_tiene_500_filas(self):
        df = pd.read_csv(SCORED_PATH)
        assert len(df) == 500

    def test_csv_columnas_clave(self):
        df = pd.read_csv(SCORED_PATH)
        for col in ["id_siniestro", "score_riesgo", "nivel_riesgo", "recomendacion"]:
            assert col in df.columns
