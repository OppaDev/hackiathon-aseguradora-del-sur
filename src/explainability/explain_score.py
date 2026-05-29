"""
Fase 12 — Explicabilidad narrativa del score de riesgo.

Genera justificaciones en lenguaje natural para el score de riesgo,
integrando reglas disparadas, señales documentales y SHAP values.

Dos modos:
  Modo A (Claude API): narrativa detallada y personalizada.
  Modo B (fallback):   plantillas determinísticas estructuradas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

# Importación lazy del agente para evitar dependencias circulares
def _get_agent():
    from src.ai_agent.claims_agent import _API_AVAILABLE, _call_claude, SYSTEM_PROMPT
    return _API_AVAILABLE, _call_claude, SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Generación de narrativa — Modo B (fallback determinístico)
# ---------------------------------------------------------------------------

_NIVEL_INTRO = {
    "ALTO": (
        "El análisis automatizado ha identificado múltiples posibles señales de riesgo "
        "que podrían requerir atención prioritaria por parte del equipo especializado."
    ),
    "MEDIO": (
        "El análisis automatizado ha detectado algunos indicadores que podrían justificar "
        "una revisión adicional por parte de la Unidad Antifraude."
    ),
    "BAJO": (
        "El análisis automatizado no ha identificado señales de riesgo significativas "
        "en este siniestro."
    ),
}

_REGLA_NARRATIVAS = {
    "R001": "La siniestralidad ocurrió en una fecha muy próxima al inicio de la póliza, lo que podría indicar una contratación dirigida.",
    "R002": "Se detecta proveedor en lista de restricción, lo que requiere verificación de la relación comercial.",
    "R003": "El monto reclamado supera significativamente el monto estimado, sugiriendo posible sobrevaloración.",
    "R004": "Se registran múltiples siniestros previos en el historial del asegurado.",
    "R005": "El reporte del siniestro presenta demoras que exceden el plazo reglamentario.",
    "R006": "La narrativa del siniestro presenta alta similitud con otro caso registrado en el sistema.",
    "R007": "El asegurado registra reclamos de responsabilidad civil sin terceros involucrados.",
    "R008": "El siniestro se registra próximo a la fecha de vencimiento de la póliza.",
    "R009": "El monto reclamado representa una proporción elevada de la suma asegurada.",
    "R010": "La declaración presenta elementos que podrían requerir corroboración adicional.",
    "R011": "Se identifican señales documentales que podrían indicar alteración de documentos.",
    "R012": "El parte policial fue presentado fuera del plazo habitual.",
    "R013": "Los documentos no incluyen testigos del siniestro.",
    "R014": "El número RUC del proveedor presenta posibles inconsistencias de validación.",
    "R015": "No se registra denuncia previa al reporte del siniestro de robo.",
    "R016": "El proveedor tiene un volumen de siniestros atípicamente alto en el período.",
    "R017": "El monto promedio facturado por el proveedor es inusualmente elevado.",
    "R018": "Se registran múltiples reclamos del mismo asegurado en el último año.",
    "R019": "La narrativa del siniestro es idéntica a la de otro caso registrado.",
    "R020": "El siniestro ocurrió en horario de madrugada con características atípicas.",
    "R021": "Se detecta ausencia simultánea de denuncia y reporte de robo.",
    "R022": "La hora del accidente registrada presenta inconsistencias con la documentación.",
    "R023": "La combinación de señales documentales configura un patrón que podría requerir revisión.",
    "R024": "La fecha de factura no coincide con la fecha del siniestro declarada.",
}


def _fallback_explanation(row: pd.Series) -> str:
    """Genera explicación narrativa determinística."""
    nivel = str(row.get("nivel_riesgo", "BAJO"))
    score = float(row.get("score_riesgo", 0) or 0)
    sin_id = row.get("id_siniestro", "N/D")

    partes = [
        f"**Siniestro {sin_id} — Nivel {nivel} (Score {score:.0f}/100)**\n",
        _NIVEL_INTRO.get(nivel, ""),
        "",
    ]

    # Contribución de cada componente
    partes.append("**Análisis por componente:**\n")

    s_reg = float(row.get("score_reglas", 0) or 0)
    s_doc = float(row.get("score_documental", 0) or 0)
    s_ml  = float(row.get("score_modelo", 0) or 0)
    s_nlp = float(row.get("score_nlp", 0) or 0)

    if s_reg > 0:
        partes.append(
            f"- **Motor de reglas ({s_reg:.0f}/100, peso 40%):** "
            f"{int(row.get('rule_n_rules_fired', 0) or 0)} regla(s) activada(s), "
            f"{int(row.get('rule_n_critical', 0) or 0)} crítica(s)."
        )
    if s_doc > 0:
        partes.append(
            f"- **Señales documentales ({s_doc:.0f}/100, peso 25%):** "
            "Los documentos aportados presentan indicadores que requieren verificación."
        )
    if s_ml > 0:
        fb = row.get("modelo_fallback", True)
        source = "proxy por reglas" if fb else "modelo RandomForest"
        partes.append(f"- **Modelo ML ({s_ml:.0f}/100, peso 20%):** Score calculado via {source}.")
    if s_nlp > 0:
        sim = float(row.get("similitud_narrativa", 0) or 0)
        partes.append(
            f"- **Análisis NLP ({s_nlp:.0f}/100, peso 15%):** "
            f"Similitud narrativa con otro siniestro: {sim:.1%}."
        )

    # Detalle de reglas activadas
    alerts = str(row.get("rule_alerts", "") or "")
    if alerts.strip():
        partes.append("\n**Posibles señales identificadas:**\n")
        for rule_code in alerts.split("|"):
            rule_code = rule_code.strip()
            if rule_code in _REGLA_NARRATIVAS:
                partes.append(f"- *{rule_code}:* {_REGLA_NARRATIVAS[rule_code]}")

    # Recomendación
    recom = str(row.get("recomendacion", "") or "")
    if recom:
        partes.append(f"\n**Recomendación:** {recom}")

    partes.append(
        "\n---\n*Análisis generado automáticamente. "
        "Todas las conclusiones deben ser validadas por el equipo humano de la Unidad Antifraude.*"
    )

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Generación de narrativa — Modo A (Claude API)
# ---------------------------------------------------------------------------

def _api_explanation(row: pd.Series, shap_items: list[dict] = None) -> str:
    """Genera explicación narrativa via Claude API."""
    _API_AVAILABLE, _call_claude, SYSTEM_PROMPT = _get_agent()

    sin_id = row.get("id_siniestro", "N/D")
    nivel  = row.get("nivel_riesgo", "BAJO")
    score  = float(row.get("score_riesgo", 0) or 0)
    alerts = str(row.get("rule_alerts", "") or "")
    n_reg  = int(row.get("rule_n_rules_fired", 0) or 0)
    n_crit = int(row.get("rule_n_critical", 0) or 0)
    sim    = float(row.get("similitud_narrativa", 0) or 0)

    reglas_narr = []
    for code in alerts.split("|"):
        code = code.strip()
        if code in _REGLA_NARRATIVAS:
            reglas_narr.append(f"  - {code}: {_REGLA_NARRATIVAS[code]}")

    shap_text = ""
    if shap_items:
        shap_text = "\nFactores más influyentes (SHAP):\n" + "\n".join(
            f"  - {it['feature']}: {it['shap_value']:+.4f} ({it.get('direction', '')})"
            for it in shap_items[:5]
        )

    prompt = f"""Genera una justificación narrativa de riesgo para el siguiente siniestro.

Datos del siniestro {sin_id}:
- Nivel de riesgo: {nivel}
- Score final: {score:.0f}/100
- Reglas disparadas: {n_reg} ({n_crit} críticas)
- Similitud narrativa: {sim:.1%}
- Score reglas: {float(row.get('score_reglas', 0) or 0):.0f}/100
- Score documental: {float(row.get('score_documental', 0) or 0):.0f}/100
- Score modelo ML: {float(row.get('score_modelo', 0) or 0):.0f}/100

Señales detectadas:
{chr(10).join(reglas_narr) if reglas_narr else '  Ninguna'}
{shap_text}

Recomendación del sistema: {row.get('recomendacion', '')}

Escribe una justificación narrativa clara en 3-4 párrafos que:
1. Explique el nivel de riesgo y su justificación.
2. Describa las posibles señales más relevantes.
3. Indique qué aspectos requieren verificación humana.
4. Concluya con la acción recomendada.
Usa lenguaje cauteloso y profesional. Máximo 250 palabras."""

    return _call_claude(prompt, system=SYSTEM_PROMPT, max_tokens=500)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def generate_explanation(
    row: pd.Series,
    shap_items: list[dict] = None,
) -> dict:
    """
    Genera justificación narrativa del score para un siniestro.

    Parámetros:
        row:        fila del DataFrame con scores y reglas.
        shap_items: lista de dicts {feature, shap_value, direction}.

    Devuelve:
        {"explanation": str, "mode": "api" | "fallback"}
    """
    try:
        _API_AVAILABLE, _call_claude, _ = _get_agent()
    except Exception:
        _API_AVAILABLE = False

    if _API_AVAILABLE:
        try:
            text = _api_explanation(row, shap_items)
            return {"explanation": text, "mode": "api"}
        except Exception as e:
            log.warning(f"API error en explicabilidad: {e} — usando fallback")

    return {"explanation": _fallback_explanation(row), "mode": "fallback"}


def generate_batch_explanations(
    df: pd.DataFrame,
    max_rows: int = 20,
    only_alto: bool = True,
) -> pd.DataFrame:
    """
    Genera explicaciones para un subconjunto del DataFrame.

    Parámetros:
        df:        DataFrame con scores.
        max_rows:  máximo de filas a procesar.
        only_alto: si True, solo siniestros de nivel ALTO.

    Devuelve el DataFrame con columna 'explicacion_narrativa' añadida.
    """
    df = df.copy()

    if only_alto and "nivel_riesgo" in df.columns:
        mask = df["nivel_riesgo"] == "ALTO"
    else:
        mask = pd.Series([True] * len(df), index=df.index)

    target = df[mask].nlargest(max_rows, "score_riesgo") if "score_riesgo" in df.columns else df[mask].head(max_rows)

    explanations = {}
    for _, row in target.iterrows():
        result = generate_explanation(row)
        explanations[row["id_siniestro"]] = result["explanation"]

    df["explicacion_narrativa"] = df["id_siniestro"].map(explanations)
    return df


def get_rule_explanation(rule_code: str) -> str:
    """Devuelve la narrativa de una regla específica."""
    return _REGLA_NARRATIVAS.get(rule_code, f"Regla {rule_code}: sin descripción disponible.")


def get_all_rule_explanations() -> dict[str, str]:
    """Devuelve todas las narrativas de reglas."""
    return dict(_REGLA_NARRATIVAS)


if __name__ == "__main__":
    import sys
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    scored_path = root / "data" / "processed" / "claims_scored.csv"
    docs_path   = root / "data" / "processed" / "claims_with_documents.csv"

    scored = pd.read_csv(scored_path)
    docs   = pd.read_csv(docs_path)
    df = docs.merge(
        scored[["id_siniestro", "score_riesgo", "nivel_riesgo",
                "score_reglas", "score_documental", "score_modelo", "score_nlp",
                "rule_alerts", "rule_n_rules_fired", "rule_n_critical",
                "recomendacion", "modelo_fallback"]],
        on="id_siniestro", how="left",
    )

    alto = df[df["nivel_riesgo"] == "ALTO"].nlargest(3, "score_riesgo")
    for _, row in alto.iterrows():
        print(f"\n{'='*65}")
        result = generate_explanation(row)
        print(result["explanation"])
        print(f"\n[Modo: {result['mode']}]")
