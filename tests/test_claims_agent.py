"""
Tests para src/ai_agent/claims_agent.py.

Cubren:
  - Estado del agente (API disponible o no)
  - analyze_claim en modo fallback
  - answer_question en modo fallback
  - generate_executive_summary en modo fallback
  - Cumplimiento de restricciones éticas (lenguaje prohibido ausente)
  - Funciones de construcción de contexto

Los tests siempre corren en modo fallback (mock de la API).
Si hay API key real, se usa mock igualmente para reproducibilidad.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Garantizamos modo fallback para todos los tests
import src.ai_agent.claims_agent as agent_module
_original_available = agent_module._API_AVAILABLE


@pytest.fixture(autouse=True)
def force_fallback(monkeypatch):
    monkeypatch.setattr(agent_module, "_API_AVAILABLE", False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ROOT        = Path(__file__).resolve().parents[1]
SCORED_PATH = ROOT / "data" / "processed" / "claims_scored.csv"
DOCS_PATH   = ROOT / "data" / "processed" / "claims_with_documents.csv"


@pytest.fixture(scope="module")
def df_scored() -> pd.DataFrame:
    return pd.read_csv(SCORED_PATH)


@pytest.fixture(scope="module")
def df_docs() -> pd.DataFrame:
    return pd.read_csv(DOCS_PATH)


@pytest.fixture(scope="module")
def df_full(df_docs, df_scored) -> pd.DataFrame:
    merge_cols = [c for c in [
        "id_siniestro", "score_riesgo", "nivel_riesgo",
        "score_reglas", "score_documental", "score_modelo", "score_nlp",
        "rule_alerts", "rule_explanations", "rule_n_rules_fired", "rule_n_critical",
    ] if c in df_scored.columns]
    return df_docs.merge(df_scored[merge_cols], on="id_siniestro", how="left")


# ---------------------------------------------------------------------------
# get_agent_status
# ---------------------------------------------------------------------------

class TestGetAgentStatus:
    def test_retorna_dict(self):
        status = agent_module.get_agent_status()
        assert isinstance(status, dict)

    def test_keys_presentes(self):
        status = agent_module.get_agent_status()
        for k in ["api_available", "mode", "model", "message"]:
            assert k in status

    def test_fallback_mode_texto(self):
        status = agent_module.get_agent_status()
        assert "Fallback" in status["mode"] or "fallback" in status["mode"].lower()

    def test_api_available_false(self):
        assert agent_module.get_agent_status()["api_available"] is False


# ---------------------------------------------------------------------------
# analyze_claim — modo fallback
# ---------------------------------------------------------------------------

class TestAnalyzeClaim:
    def test_estructura_resultado(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        for k in ["id_siniestro", "analysis", "mode", "score_riesgo", "nivel_riesgo"]:
            assert k in result

    def test_modo_fallback(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        assert result["mode"] == "fallback"

    def test_id_no_encontrado(self, df_full):
        result = agent_module.analyze_claim("SIN-9999", df_full)
        assert result["mode"] == "error"
        assert "SIN-9999" in result["analysis"]

    def test_score_es_float(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        assert isinstance(result["score_riesgo"], float)

    def test_nivel_valido(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        assert result["nivel_riesgo"] in {"BAJO", "MEDIO", "ALTO", "N/D"}

    def test_analysis_no_vacio(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        assert len(result["analysis"]) > 50

    def test_analiza_siniestro_alto_riesgo(self, df_full):
        alto = df_full[df_full["nivel_riesgo"] == "ALTO"]
        if not alto.empty:
            sin_id = alto.iloc[0]["id_siniestro"]
            result = agent_module.analyze_claim(sin_id, df_full)
            assert result["nivel_riesgo"] == "ALTO"
            assert result["score_riesgo"] > 65

    def test_con_shap_explanation(self, df_full):
        shap = [
            {"feature": "proveedor_lista_restrictiva", "shap_value": 0.091, "direction": "aumenta riesgo"},
            {"feature": "similitud_narrativa",         "shap_value": 0.085, "direction": "aumenta riesgo"},
        ]
        result = agent_module.analyze_claim("SIN-0001", df_full, shap_explanation=shap)
        assert result["mode"] == "fallback"


# ---------------------------------------------------------------------------
# Cumplimiento ético — lenguaje prohibido
# ---------------------------------------------------------------------------

FRASES_PROHIBIDAS = [
    "es fraude",
    "es fraudulento",
    "cometió fraude",
    "rechazado",
    "rechazar el siniestro",
    "culpable",
    "culpa del asegurado",
    "se rechaza",
    "definitivamente fraude",
]

class TestEthicalCompliance:
    def test_no_fraude_definitivo(self, df_full):
        alto = df_full[df_full["nivel_riesgo"] == "ALTO"]
        if not alto.empty:
            for _, row in alto.head(3).iterrows():
                result = agent_module.analyze_claim(row["id_siniestro"], df_full)
                texto = result["analysis"].lower()
                for frase in FRASES_PROHIBIDAS:
                    assert frase.lower() not in texto, (
                        f"Frase prohibida '{frase}' encontrada en análisis de {row['id_siniestro']}"
                    )

    def test_contiene_lenguaje_cauteloso(self, df_full):
        alto = df_full[df_full["nivel_riesgo"] == "ALTO"]
        if not alto.empty:
            sin_id = alto.iloc[0]["id_siniestro"]
            result = agent_module.analyze_claim(sin_id, df_full)
            texto = result["analysis"].lower()
            frases_ok = [
                "posible", "podría", "requiere", "revisión", "recomend",
                "indica", "señal", "verificar",
            ]
            assert any(f in texto for f in frases_ok), (
                "El análisis debe contener lenguaje condicional/cauteloso"
            )

    def test_contiene_accion_humana(self, df_full):
        result = agent_module.analyze_claim("SIN-0001", df_full)
        texto  = result["analysis"].lower()
        keywords = ["recomend", "revisión", "flujo", "escalar", "equipo", "humano", "unidad"]
        assert any(k in texto for k in keywords), (
            "El análisis debe incluir una recomendación de acción humana"
        )


# ---------------------------------------------------------------------------
# answer_question — modo fallback
# ---------------------------------------------------------------------------

class TestAnswerQuestion:
    def test_estructura_resultado(self, df_full):
        result = agent_module.answer_question("¿Cuántos siniestros hay?", df_full)
        assert "answer" in result
        assert "mode"   in result

    def test_modo_fallback(self, df_full):
        result = agent_module.answer_question("¿Cuántos siniestros hay?", df_full)
        assert result["mode"] == "fallback"

    def test_respuesta_no_vacia(self, df_full):
        result = agent_module.answer_question("Resumen del portafolio", df_full)
        assert len(result["answer"]) > 20

    def test_con_id_siniestro(self, df_full):
        result = agent_module.answer_question(
            "¿Qué alertas tiene este siniestro?", df_full, id_siniestro="SIN-0001"
        )
        assert "answer" in result


# ---------------------------------------------------------------------------
# generate_executive_summary — modo fallback
# ---------------------------------------------------------------------------

class TestExecutiveSummary:
    def test_estructura_resultado(self, df_full):
        result = agent_module.generate_executive_summary(df_full)
        for k in ["summary", "mode", "stats"]:
            assert k in result

    def test_modo_fallback(self, df_full):
        result = agent_module.generate_executive_summary(df_full)
        assert result["mode"] == "fallback"

    def test_stats_completos(self, df_full):
        stats = agent_module.generate_executive_summary(df_full)["stats"]
        for k in ["total", "alto", "medio", "bajo", "score_med", "score_max"]:
            assert k in stats

    def test_total_correcto(self, df_full):
        stats = agent_module.generate_executive_summary(df_full)["stats"]
        assert stats["total"] == len(df_full)

    def test_suma_niveles_igual_total(self, df_full):
        stats = agent_module.generate_executive_summary(df_full)["stats"]
        assert stats["alto"] + stats["medio"] + stats["bajo"] == stats["total"]

    def test_summary_no_vacio(self, df_full):
        result = agent_module.generate_executive_summary(df_full)
        assert len(result["summary"]) > 100

    def test_no_fraude_definitivo_en_summary(self, df_full):
        result = agent_module.generate_executive_summary(df_full)
        texto  = result["summary"].lower()
        for frase in FRASES_PROHIBIDAS:
            assert frase.lower() not in texto


# ---------------------------------------------------------------------------
# _build_claim_context (función interna)
# ---------------------------------------------------------------------------

class TestBuildClaimContext:
    def test_contexto_contiene_id(self, df_full):
        row    = df_full[df_full["id_siniestro"] == "SIN-0005"].iloc[0]
        ctx    = agent_module._build_claim_context(row)
        assert "SIN-0005" in ctx

    def test_contexto_contiene_score(self, df_full):
        row = df_full[df_full["id_siniestro"] == "SIN-0001"].iloc[0]
        ctx = agent_module._build_claim_context(row)
        assert "score" in ctx.lower() or "Score" in ctx

    def test_contexto_con_shap(self, df_full):
        row  = df_full.iloc[0]
        shap = [{"feature": "proveedor_lista_restrictiva", "shap_value": 0.09, "direction": "aumenta riesgo"}]
        ctx  = agent_module._build_claim_context(row, shap)
        assert "proveedor_lista_restrictiva" in ctx

    def test_contexto_es_string(self, df_full):
        row = df_full.iloc[0]
        ctx = agent_module._build_claim_context(row)
        assert isinstance(ctx, str)
        assert len(ctx) > 100


# ---------------------------------------------------------------------------
# Modo API — mock
# ---------------------------------------------------------------------------

class TestApiMode:
    def test_analyze_claim_con_api(self, df_full, monkeypatch):
        monkeypatch.setattr(agent_module, "_API_AVAILABLE", True)
        mock_resp_text = (
            "## Análisis SIN-0001\n\n"
            "Se observan posibles señales de riesgo que requieren revisión.\n\n"
            "### Acción recomendada\nEscalar a la Unidad Antifraude."
        )
        with patch.object(agent_module, "_call_claude", return_value=mock_resp_text):
            result = agent_module.analyze_claim("SIN-0001", df_full)
        assert result["mode"] == "api"
        assert "posibles señales" in result["analysis"]

    def test_api_error_usa_fallback(self, df_full, monkeypatch):
        monkeypatch.setattr(agent_module, "_API_AVAILABLE", True)
        with patch.object(agent_module, "_call_claude", side_effect=Exception("timeout")):
            result = agent_module.analyze_claim("SIN-0001", df_full)
        assert result["mode"] == "fallback"

    def test_executive_summary_con_api(self, df_full, monkeypatch):
        monkeypatch.setattr(agent_module, "_API_AVAILABLE", True)
        mock_text = "El portafolio presenta posibles señales de riesgo en el 1% de los casos."
        with patch.object(agent_module, "_call_claude", return_value=mock_text):
            result = agent_module.generate_executive_summary(df_full)
        assert result["mode"] == "api"
        assert "portafolio" in result["summary"].lower()
