"""
Tests para src/rules/fraud_rules.py — usan claims_with_documents.csv real.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.rules.fraud_rules import apply_rules, apply_rules_df, _is_madrugada

ROOT   = Path(__file__).resolve().parents[1]
DF_PATH = ROOT / "data" / "processed" / "claims_with_documents.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(DF_PATH)


@pytest.fixture(scope="module")
def df_ruled(df) -> pd.DataFrame:
    return apply_rules_df(df)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

class TestIsMarugada:
    def test_hora_02_es_madrugada(self):
        assert _is_madrugada("02:30") is True

    def test_hora_05_es_madrugada(self):
        assert _is_madrugada("05:59") is True

    def test_hora_06_no_madrugada(self):
        assert _is_madrugada("06:00") is False

    def test_hora_none(self):
        assert _is_madrugada(None) is False

    def test_hora_vacia(self):
        assert _is_madrugada("") is False


# ---------------------------------------------------------------------------
# apply_rules sobre datos sintéticos controlados
# ---------------------------------------------------------------------------

class TestApplyRulesControlados:
    def _make_row(self, **kwargs) -> dict:
        defaults = {
            "dias_desde_inicio_poliza": 200,
            "dias_hasta_fin_poliza": 200,
            "dias_ocurrencia_reporte": 2,
            "historial_siniestros_asegurado": 0,
            "n_reclamos_12_meses": 0,
            "n_reclamos_historico": 0,
            "reclamos_rc_sin_tercero": 0,
            "ratio_monto_suma": 0.5,
            "delta_monto_proveedor": 0,
            "promedio_monto_proveedor": 1000,
            "monto_reclamado": 800,
            "similitud_narrativa": 0.0,
            "proveedor_lista_restrictiva": False,
            "docs_completos": True,
            "doc_factura_alterada": False,
            "doc_ruc_invalido": False,
            "doc_caso_fraude": False,
            "doc_parte_tardio_dias": None,
            "doc_sin_denuncia_previa": False,
            "doc_robo": False,
            "doc_perdida_total": False,
            "doc_tercero_identificado": True,
            "doc_sin_testigos": False,
            "doc_sin_intervencion": False,
            "doc_hora_accidente": None,
            "doc_fecha_factura_min": None,
            "fecha_ocurrencia": "2025-06-15",
        }
        defaults.update(kwargs)
        return defaults

    def test_sin_alertas_score_cero(self):
        r = apply_rules(self._make_row())
        assert r["rule_points"] == 0
        assert r["alerts"] == []
        assert r["severity_max"] == "NINGUNA"

    def test_r001_inicio_póliza(self):
        r = apply_rules(self._make_row(dias_desde_inicio_poliza=5))
        assert "R001" in r["alerts"]
        assert r["rule_points"] == 8

    def test_r002_inicio_póliza_alto(self):
        r = apply_rules(self._make_row(dias_desde_inicio_poliza=20))
        assert "R002" in r["alerts"]
        assert "R001" not in r["alerts"]

    def test_r003_fin_póliza(self):
        r = apply_rules(self._make_row(dias_hasta_fin_poliza=5))
        assert "R003" in r["alerts"]
        assert r["rule_points"] == 8

    def test_r004b_borde_extremo(self):
        r = apply_rules(self._make_row(dias_desde_inicio_poliza=1))
        assert "R004b" in r["alerts"]
        assert r["rule_points"] >= 10

    def test_r005_reporte_tardio(self):
        r = apply_rules(self._make_row(dias_ocurrencia_reporte=10))
        assert "R005" in r["alerts"]

    def test_r006_robo_parte_tardio(self):
        r = apply_rules(self._make_row(doc_robo=True, doc_parte_tardio_dias=8))
        assert "R006" in r["alerts"]

    def test_r007_robo_parte_medio(self):
        r = apply_rules(self._make_row(doc_robo=True, doc_parte_tardio_dias=3))
        assert "R007" in r["alerts"]
        assert "R006" not in r["alerts"]

    def test_r008_alta_frecuencia(self):
        r = apply_rules(self._make_row(historial_siniestros_asegurado=4))
        assert "R008" in r["alerts"]

    def test_r011_proveedor_lista(self):
        r = apply_rules(self._make_row(proveedor_lista_restrictiva=True))
        assert "R011" in r["alerts"]
        assert r["severity_max"] == "CRÍTICO"

    def test_r012_factura_alterada(self):
        r = apply_rules(self._make_row(doc_factura_alterada=True))
        assert "R012" in r["alerts"]
        assert r["rule_points"] == 15

    def test_r013_ruc_invalido(self):
        r = apply_rules(self._make_row(doc_ruc_invalido=True))
        assert "R013" in r["alerts"]

    def test_r014_narrativa_clonada(self):
        r = apply_rules(self._make_row(similitud_narrativa=0.90))
        assert "R014" in r["alerts"]
        assert "R015" not in r["alerts"]

    def test_r015_narrativa_similar(self):
        r = apply_rules(self._make_row(similitud_narrativa=0.75))
        assert "R015" in r["alerts"]
        assert "R014" not in r["alerts"]

    def test_r016_monto_alto(self):
        r = apply_rules(self._make_row(ratio_monto_suma=0.97))
        assert "R016" in r["alerts"]

    def test_r019_robo_sin_denuncia(self):
        r = apply_rules(self._make_row(doc_robo=True, doc_sin_denuncia_previa=True))
        assert "R019" in r["alerts"]
        assert r["rule_points"] >= 12

    def test_r021_perdida_total_robo(self):
        r = apply_rules(self._make_row(doc_robo=True, doc_perdida_total=True))
        assert "R021" in r["alerts"]

    def test_r022_madrugada_sin_testigos(self):
        r = apply_rules(self._make_row(doc_hora_accidente="02:30", doc_sin_testigos=True))
        assert "R022" in r["alerts"]

    def test_r023_docs_incompletos(self):
        r = apply_rules(self._make_row(docs_completos=False))
        assert "R023" in r["alerts"]
        assert r["severity_max"] == "BAJO"

    def test_r024_factura_previa(self):
        r = apply_rules(self._make_row(
            doc_fecha_factura_min="2025-06-10",
            fecha_ocurrencia="2025-06-15"
        ))
        assert "R024" in r["alerts"]

    def test_multiple_reglas_acumulan_puntos(self):
        r = apply_rules(self._make_row(
            doc_factura_alterada=True,     # R012: 15
            doc_ruc_invalido=True,         # R013: 10
            proveedor_lista_restrictiva=True,  # R011: 10
        ))
        assert r["rule_points"] == 35
        assert r["n_critical"] >= 3

    def test_severity_max_critico_con_r012(self):
        r = apply_rules(self._make_row(doc_factura_alterada=True))
        assert r["severity_max"] == "CRÍTICO"


# ---------------------------------------------------------------------------
# apply_rules_df sobre datos reales
# ---------------------------------------------------------------------------

class TestApplyRulesDf:
    def test_shape_igual(self, df, df_ruled):
        assert len(df_ruled) == len(df)

    def test_columnas_rule_presentes(self, df_ruled):
        for col in ["rule_points", "rule_alerts", "rule_critical_flags",
                    "rule_explanations", "rule_severity_max",
                    "rule_n_rules_fired", "rule_n_critical"]:
            assert col in df_ruled.columns, f"Falta: {col}"

    def test_sin0005_puntos_altos(self, df_ruled):
        row = df_ruled[df_ruled["id_siniestro"] == "SIN-0005"].iloc[0]
        # R012(15) + R013(10) + R019(12) + R021(8) = 45 mínimo
        assert row["rule_points"] >= 45

    def test_sin0005_reglas_criticas(self, df_ruled):
        row = df_ruled[df_ruled["id_siniestro"] == "SIN-0005"].iloc[0]
        alerts = row["rule_alerts"].split("|")
        assert "R012" in alerts  # factura alterada
        assert "R013" in alerts  # RUC inválido
        assert "R019" in alerts  # robo sin denuncia

    def test_sin0005_severidad_critica(self, df_ruled):
        row = df_ruled[df_ruled["id_siniestro"] == "SIN-0005"].iloc[0]
        assert row["rule_severity_max"] == "CRÍTICO"

    def test_siniestros_sin_alertas(self, df_ruled):
        sin_alertas = df_ruled[df_ruled["rule_alerts"] == ""]
        assert len(sin_alertas) >= 10  # algunos siniestros legítimos sin alertas

    def test_no_hay_puntos_negativos(self, df_ruled):
        assert (df_ruled["rule_points"] >= 0).all()

    def test_siniestros_con_criticos(self, df_ruled):
        criticos = df_ruled[df_ruled["rule_severity_max"] == "CRÍTICO"]
        assert len(criticos) >= 50  # al menos 10% de 500

    def test_rule_points_max_razonable(self, df_ruled):
        # Ningún siniestro debería superar 150 puntos
        assert df_ruled["rule_points"].max() <= 150

    def test_explanaciones_en_espanol(self, df_ruled):
        # Los siniestros con alertas deben tener explicaciones
        con_alertas = df_ruled[df_ruled["rule_alerts"] != ""]
        assert (con_alertas["rule_explanations"] != "").all()
