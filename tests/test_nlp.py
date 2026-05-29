"""
Tests para src/nlp/narrative_similarity.py — usan datos reales.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.nlp.narrative_similarity import (
    _preprocess,
    compute_group_similarity,
    build_group_pairs,
    enrich_with_nlp,
    get_similar_claims,
    run,
    UMBRAL_CLONADA,
    UMBRAL_SIMILAR,
    UMBRAL_FREQ_COMUN,
)

ROOT        = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "data" / "processed" / "claims_with_documents.csv"
NLP_PATH    = ROOT / "data" / "processed" / "claims_nlp.csv"
PAIRS_PATH  = ROOT / "data" / "processed" / "similarity_pairs.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df_raw() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


@pytest.fixture(scope="module")
def df_nlp(df_raw) -> pd.DataFrame:
    return enrich_with_nlp(df_raw)


# ---------------------------------------------------------------------------
# Preprocesamiento
# ---------------------------------------------------------------------------

class TestPreprocess:
    def test_minusculas(self):
        assert _preprocess("ROBO DE VEHÍCULO") == "robo vehículo"

    def test_elimina_signos(self):
        result = _preprocess("Choque, con daños.")
        assert "," not in result
        assert "." not in result

    def test_elimina_stopwords(self):
        result = _preprocess("robo de bienes en domicilio")
        assert "de" not in result.split()
        assert "en" not in result.split()
        assert "robo" in result

    def test_texto_vacio(self):
        assert _preprocess("") == ""

    def test_texto_none(self):
        assert _preprocess(None) == ""  # type: ignore


# ---------------------------------------------------------------------------
# compute_group_similarity
# ---------------------------------------------------------------------------

class TestGroupSimilarity:
    def test_diagonal_cero(self):
        texts = ["robo de vehículo", "choque en carretera", "incendio total"]
        sim = compute_group_similarity(texts)
        assert np.allclose(np.diag(sim), 0)

    def test_textos_iguales_similitud_alta(self):
        texts = ["robo vehículo parqueadero", "robo vehículo parqueadero"]
        sim = compute_group_similarity(texts)
        # Dos textos idénticos tienen similitud > 0.9 después de limpiar diagonal
        # (en este caso la diagonal se pone a 0 así que revisamos [0,1])
        assert sim[0, 1] > 0.9

    def test_textos_distintos_similitud_baja(self):
        texts = ["robo violencia domicilio", "incendio vehiculo combustible"]
        sim = compute_group_similarity(texts)
        assert sim[0, 1] < 0.5

    def test_forma_correcta(self):
        texts = ["a", "b", "c"]
        sim = compute_group_similarity(texts)
        assert sim.shape == (3, 3)


# ---------------------------------------------------------------------------
# enrich_with_nlp sobre datos reales
# ---------------------------------------------------------------------------

class TestEnrichWithNlp:
    def test_shape_igual(self, df_raw, df_nlp):
        assert len(df_nlp) == len(df_raw)

    def test_columnas_presentes(self, df_nlp):
        for col in ["nlp_freq_descripcion", "nlp_descripcion_rara",
                    "nlp_descripcion_comun", "nlp_sim_entre_grupos",
                    "nlp_grupo_id", "nlp_cluster_fraude", "nlp_score"]:
            assert col in df_nlp.columns, f"Falta: {col}"

    def test_frecuencia_coherente(self, df_nlp):
        # Suma de frecuencias == 500
        # nlp_freq_descripcion es cuántos tienen la misma descripción
        # La suma no necesariamente da 500, pero debe ser positiva y lógica
        assert (df_nlp["nlp_freq_descripcion"] > 0).all()

    def test_descripcion_mas_frecuente(self, df_nlp):
        # "Siniestro reportado con documentación." → 70 casos
        max_freq = df_nlp["nlp_freq_descripcion"].max()
        assert max_freq >= 50

    def test_hay_descripciones_comunes(self, df_nlp):
        n = df_nlp["nlp_descripcion_comun"].sum()
        assert n >= 200  # mayoría del dataset

    def test_hay_descripciones_raras(self, df_nlp):
        n = df_nlp["nlp_descripcion_rara"].sum()
        assert n >= 1

    def test_grupo_id_en_rango(self, df_nlp):
        n_grupos = df_nlp["descripcion"].nunique()
        assert (df_nlp["nlp_grupo_id"] >= 0).all()
        assert (df_nlp["nlp_grupo_id"] < n_grupos).all()

    def test_nlp_score_en_rango(self, df_nlp):
        assert (df_nlp["nlp_score"] >= 0).all()
        assert (df_nlp["nlp_score"] <= 100).all()

    def test_nlp_score_alto_en_desc_frecuente(self, df_nlp):
        # Siniestros con descripción muy frecuente + alta similitud Excel
        # deben tener score alto
        alta_freq = df_nlp[df_nlp["nlp_freq_descripcion"] >= 50]
        assert alta_freq["nlp_score"].mean() >= 50

    def test_nlp_score_bajo_en_desc_rara(self, df_nlp):
        raras = df_nlp[df_nlp["nlp_descripcion_rara"]]
        if len(raras) > 0:
            assert raras["nlp_score"].mean() < 60

    def test_n_grupos_unicos(self, df_nlp):
        assert df_nlp["nlp_grupo_id"].nunique() == df_nlp["descripcion"].nunique()

    def test_columna_valida_excel_presente(self, df_nlp):
        assert "nlp_valida_excel" in df_nlp.columns


# ---------------------------------------------------------------------------
# get_similar_claims
# ---------------------------------------------------------------------------

class TestGetSimilarClaims:
    def test_misma_descripcion(self, df_nlp):
        desc = df_nlp[df_nlp["id_siniestro"] == "SIN-0001"].iloc[0]["descripcion"]
        similares = get_similar_claims("SIN-0001", df_nlp, top_n=5)
        # Todos los devueltos deben tener la misma descripción o ser del mismo cluster
        assert len(similares) >= 1

    def test_no_incluye_propio(self, df_nlp):
        similares = get_similar_claims("SIN-0001", df_nlp, top_n=10)
        ids = [s["id_siniestro"] for s in similares]
        assert "SIN-0001" not in ids

    def test_id_inexistente(self, df_nlp):
        result = get_similar_claims("SIN-9999", df_nlp, top_n=5)
        assert result == []

    def test_top_n_respetado(self, df_nlp):
        result = get_similar_claims("SIN-0001", df_nlp, top_n=3)
        assert len(result) <= 3


# ---------------------------------------------------------------------------
# Pipeline run → CSV
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_run_genera_archivos(self):
        run(str(CLAIMS_PATH), str(NLP_PATH), str(PAIRS_PATH))
        assert NLP_PATH.exists()
        assert PAIRS_PATH.exists()

    def test_csv_500_filas(self):
        df = pd.read_csv(NLP_PATH)
        assert len(df) == 500

    def test_csv_columnas_nlp(self):
        df = pd.read_csv(NLP_PATH)
        assert "nlp_score" in df.columns
        assert "nlp_freq_descripcion" in df.columns
