"""
Tests para src/features/build_features.py — usan los CSVs reales generados
en Fase 1 (claims_master.csv) y Fase 2 (documents_extracted.csv).
"""

import pytest
import pandas as pd
from pathlib import Path

from src.features.build_features import (
    _agg_docs,
    _add_combined_features,
    build_features,
    validate_features,
)

ROOT        = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "data" / "processed" / "claims_master.csv"
DOCS_PATH   = ROOT / "data" / "processed" / "documents_extracted.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "claims_with_documents.csv"


# ---------------------------------------------------------------------------
# Fixtures reales
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def claims() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


@pytest.fixture(scope="module")
def docs() -> pd.DataFrame:
    return pd.read_csv(DOCS_PATH)


@pytest.fixture(scope="module")
def df_agg(docs) -> pd.DataFrame:
    return _agg_docs(docs)


@pytest.fixture(scope="module")
def df_final() -> pd.DataFrame:
    return build_features(str(CLAIMS_PATH), str(DOCS_PATH), str(OUTPUT_PATH))


# ---------------------------------------------------------------------------
# Tests de _agg_docs
# ---------------------------------------------------------------------------

class TestAggDocs:
    def test_una_fila_por_siniestro(self, docs, df_agg):
        assert len(df_agg) == docs["id_siniestro"].nunique()

    def test_sin0005_factura_alterada(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["doc_factura_alterada"] == True

    def test_sin0005_ruc_invalido(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["doc_ruc_invalido"] == True

    def test_sin0005_caso_fraude(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["doc_caso_fraude"] == True

    def test_sin0005_robo(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["doc_robo"] == True

    def test_sin0005_sin_denuncia(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["doc_sin_denuncia_previa"] == True

    def test_sin0001_legitimo(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0001"].iloc[0]
        assert row["doc_factura_alterada"] == False
        assert row["doc_ruc_invalido"] == False
        assert row["doc_caso_fraude"] == False

    def test_sin0344_parte_tardio(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0344"].iloc[0]
        assert row["doc_parte_tardio_dias"] == 11

    def test_partes_tardios_mayores_7(self, df_agg):
        tardios = df_agg[
            pd.to_numeric(df_agg["doc_parte_tardio_dias"], errors="coerce") > 7
        ]
        assert len(tardios) == 4  # SIN-0022(17), SIN-0120(13), SIN-0217(12), SIN-0344(11)

    def test_sin0378_tercero_identificado(self, df_agg):
        row = df_agg[df_agg["id_siniestro"] == "SIN-0378"].iloc[0]
        assert row["doc_tercero_identificado"] == True

    def test_tipos_pdf_presentes(self, df_agg):
        tipos = set()
        for t in df_agg["tipos_pdf"]:
            tipos.update(t.split("|"))
        assert "Factura" in tipos
        assert "Parte Policial" in tipos
        assert "Declaración Accidente" in tipos


# ---------------------------------------------------------------------------
# Tests del pipeline completo
# ---------------------------------------------------------------------------

class TestBuildFeatures:
    def test_shape_500_filas(self, df_final):
        assert len(df_final) == 500

    def test_columnas_doc_presentes(self, df_final):
        for col in ["doc_factura_alterada", "doc_ruc_invalido", "doc_caso_fraude",
                    "doc_sin_denuncia_previa", "doc_parte_tardio_dias",
                    "doc_tercero_identificado", "doc_sin_testigos"]:
            assert col in df_final.columns, f"Falta columna: {col}"

    def test_columnas_alertas_presentes(self, df_final):
        for col in ["alerta_robo_sin_denuncia", "alerta_similitud_sin_testigos",
                    "alerta_proveedor_fraude_documental", "doc_parte_tardio"]:
            assert col in df_final.columns, f"Falta columna: {col}"

    def test_score_documental_existe(self, df_final):
        assert "score_documental_raw" in df_final.columns

    def test_score_documental_rango(self, df_final):
        scores = df_final["score_documental_raw"]
        assert scores.min() >= 0
        assert scores.max() <= 100

    def test_sin0005_score_alto(self, df_final):
        row = df_final[df_final["id_siniestro"] == "SIN-0005"].iloc[0]
        # SIN-0005: factura_alterada(25) + ruc_invalido(20) + caso_fraude(30) + sin_denuncia(15) = 90
        assert row["score_documental_raw"] >= 70

    def test_sin0001_score_cero(self, df_final):
        row = df_final[df_final["id_siniestro"] == "SIN-0001"].iloc[0]
        assert row["score_documental_raw"] == 0.0

    def test_siniestros_sin_pdf_score_cero(self, df_final):
        sin_pdf = df_final[df_final["n_pdfs_extraidos"] == 0]
        assert (sin_pdf["score_documental_raw"] == 0).all()

    def test_sin_pdf_no_tiene_alertas(self, df_final):
        sin_pdf = df_final[df_final["n_pdfs_extraidos"] == 0]
        assert sin_pdf["doc_factura_alterada"].sum() == 0
        assert sin_pdf["doc_ruc_invalido"].sum() == 0

    def test_alerta_robo_sin_denuncia_sin0005(self, df_final):
        row = df_final[df_final["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["alerta_robo_sin_denuncia"] == True

    def test_n_pdfs_extraidos_correctos(self, df_final):
        # Sabemos que hay 26 PDFs para siniestros distintos (algunos tienen >1 PDF)
        total_pdfs = df_final["n_pdfs_extraidos"].sum()
        assert total_pdfs == 26

    def test_validacion_ok(self, df_final):
        issues = validate_features(df_final)
        assert issues == [], f"Problemas: {issues}"

    def test_csv_guardado(self):
        assert OUTPUT_PATH.exists()
        df_saved = pd.read_csv(OUTPUT_PATH)
        assert len(df_saved) == 500
