"""
Fase 5 — Score de riesgo final (0-100).

Fórmula:
  score_final = 40% × score_reglas + 25% × score_documental
              + 20% × score_modelo  + 15% × score_nlp

MVP sin modelo entrenado: score_modelo = score_reglas (fallback explícito).
NLP score deriva de similitud_narrativa ya calculada en el Excel.

Niveles de riesgo:
  0-40   → BAJO    (flujo normal)
  41-75  → MEDIO   (escalar a Unidad Antifraude)
  76-100 → ALTO    (revisión especializada de campo)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

from src.rules.fraud_rules import apply_rules_df
from src.features.build_features import build_features

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalización de sub-scores
# ---------------------------------------------------------------------------

# Puntos de referencia para la normalización.
# Se usa el percentil 95 del dataset real (~46 pts) como ancla de 100%,
# lo que da una distribución de riesgo realista sin inflar casos leves.
# El valor 60 se eligió observando que SIN-0005 (máximo real) tiene 61 pts.
MAX_RULE_POINTS = 60.0


def _normalize_rules(rule_points: pd.Series) -> pd.Series:
    """Normaliza puntos de reglas a 0-100."""
    return (rule_points / MAX_RULE_POINTS * 100).clip(0, 100)


def _normalize_documental(score_doc_raw: pd.Series) -> pd.Series:
    """score_documental_raw ya está en 0-100."""
    return score_doc_raw.clip(0, 100)


def _score_nlp(similitud: pd.Series) -> pd.Series:
    """
    Score NLP basado en similitud narrativa del Excel.
    similitud_narrativa ∈ [0, 1] → score_nlp ∈ [0, 100].
    """
    return (pd.to_numeric(similitud, errors="coerce").fillna(0) * 100).clip(0, 100)


def _score_modelo(score_reglas_norm: pd.Series, modelo_scores: pd.Series = None) -> pd.Series:
    """
    Score del modelo ML.
    Si no hay modelo entrenado (modelo_scores=None), usa score_reglas como proxy.
    El fallback se documenta explícitamente en la explicación.
    """
    if modelo_scores is not None and modelo_scores.notna().any():
        return modelo_scores.clip(0, 100)
    return score_reglas_norm.copy()


# ---------------------------------------------------------------------------
# Clasificación de nivel
# ---------------------------------------------------------------------------

def _classify(score: float) -> str:
    if score <= 30:
        return "BAJO"
    elif score <= 65:
        return "MEDIO"
    else:
        return "ALTO"


def _recomendacion(nivel: str) -> str:
    recs = {
        "BAJO":  "Continuar flujo normal de liquidación. Sin señales de riesgo significativas.",
        "MEDIO": "Escalar a la Unidad Antifraude para revisión documental.",
        "ALTO":  "Detener pago. Revisión especializada de campo requerida.",
    }
    return recs.get(nivel, "")


def _build_explicacion(row: pd.Series) -> str:
    """Genera una explicación breve del score para el dashboard."""
    partes = []
    partes.append(
        f"Score de riesgo: {row['score_riesgo']:.0f}/100 "
        f"(Nivel {row['nivel_riesgo']}). "
    )

    if row.get("rule_n_rules_fired", 0) > 0:
        partes.append(
            f"Motor de reglas: {row['rule_n_rules_fired']} regla(s) activada(s), "
            f"{row.get('rule_n_critical', 0)} crítica(s). "
        )

    score_doc = row.get("score_documental_raw", 0)
    if score_doc > 0:
        partes.append(f"Señales documentales PDF: score {score_doc:.0f}/100. ")

    sim = float(row.get("similitud_narrativa", 0) or 0)
    if sim > 0.7:
        partes.append(f"Narrativa con similitud {sim:.0%} respecto a otro siniestro. ")

    if row.get("modelo_fallback", True):
        partes.append("(Modelo ML no disponible — score calculado con reglas y señales documentales.)")

    return "".join(partes)


# ---------------------------------------------------------------------------
# Pipeline de scoring
# ---------------------------------------------------------------------------

def compute_scores(
    df: pd.DataFrame,
    modelo_scores: pd.Series = None,
    w_reglas: float = 0.40,
    w_doc: float = 0.25,
    w_modelo: float = 0.20,
    w_nlp: float = 0.15,
) -> pd.DataFrame:
    """
    Calcula el score final de riesgo para cada siniestro.

    Parámetros:
        df:            DataFrame claims_with_documents con columnas rule_*.
                       Si faltan columnas rule_*, las calcula internamente.
        modelo_scores: pd.Series con scores ML (0-100) indexada por posición.
                       Si es None, usa fallback por reglas.
        w_*:           Pesos del score final (deben sumar 1.0).

    Devuelve df con columnas score_* y nivel_riesgo añadidas.
    """
    df = df.copy()

    # Aplicar reglas si no están presentes
    if "rule_points" not in df.columns:
        log.info("Aplicando motor de reglas...")
        df = apply_rules_df(df)

    # Sub-scores normalizados (0-100)
    score_reglas = _normalize_rules(pd.to_numeric(df["rule_points"], errors="coerce").fillna(0))
    score_doc    = _normalize_documental(
        pd.to_numeric(df.get("score_documental_raw", 0), errors="coerce").fillna(0)
    )
    score_nlp    = _score_nlp(df.get("similitud_narrativa", 0))
    modelo_fb    = modelo_scores is None
    score_ml     = _score_modelo(score_reglas, modelo_scores)

    # Score final ponderado
    score_final = (
        w_reglas  * score_reglas +
        w_doc     * score_doc    +
        w_modelo  * score_ml     +
        w_nlp     * score_nlp
    ).clip(0, 100).round(1)

    df["score_reglas"]        = score_reglas.round(1)
    df["score_documental"]    = score_doc.round(1)
    df["score_nlp"]           = score_nlp.round(1)
    df["score_modelo"]        = score_ml.round(1)
    df["modelo_fallback"]     = modelo_fb
    df["score_riesgo"]        = score_final
    df["nivel_riesgo"]        = score_final.apply(_classify)
    df["recomendacion"]       = df["nivel_riesgo"].apply(_recomendacion)
    df["explicacion_score"]   = df.apply(_build_explicacion, axis=1)

    return df


def save_scored(df: pd.DataFrame, output_path: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Columnas del archivo final
    cols_out = [
        "id_siniestro", "score_riesgo", "nivel_riesgo",
        "recomendacion", "explicacion_score",
        "score_reglas", "score_documental", "score_nlp", "score_modelo",
        "modelo_fallback", "rule_points", "rule_alerts", "rule_critical_flags",
        "rule_severity_max", "rule_n_rules_fired", "rule_n_critical",
    ]
    cols_present = [c for c in cols_out if c in df.columns]
    df[cols_present].to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info(f"Guardado: {output_path} ({len(df)} filas)")


def run(
    claims_with_docs_path: str,
    output_path: str,
    modelo_scores: pd.Series = None,
) -> pd.DataFrame:
    """Pipeline completo: cargar → puntuar → guardar."""
    df = pd.read_csv(claims_with_docs_path)
    df = compute_scores(df, modelo_scores=modelo_scores)
    save_scored(df, output_path)
    return df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    claims_path = root / "data" / "processed" / "claims_with_documents.csv"
    output_path = root / "data" / "processed" / "claims_scored.csv"

    df = run(str(claims_path), str(output_path))

    print(f"\n{'='*60}")
    print(f"  Siniestros evaluados: {len(df)}")
    print(f"\n  Distribución de nivel de riesgo:")
    for nivel, cnt in df["nivel_riesgo"].value_counts().items():
        pct = cnt / len(df) * 100
        print(f"    {nivel}: {cnt} ({pct:.1f}%)")

    print(f"\n  Estadísticas del score final:")
    print(f"    Media:  {df['score_riesgo'].mean():.1f}")
    print(f"    Mediana:{df['score_riesgo'].median():.1f}")
    print(f"    Máximo: {df['score_riesgo'].max():.1f}")

    print(f"\n  Top 10 por score de riesgo:")
    top = df.nlargest(10, "score_riesgo")[
        ["id_siniestro", "score_riesgo", "nivel_riesgo", "rule_alerts"]
    ]
    for _, r in top.iterrows():
        alerts = str(r["rule_alerts"])[:50] if r["rule_alerts"] else ""
        print(f"    {r['id_siniestro']}: {r['score_riesgo']:.1f} | {r['nivel_riesgo']} | {alerts}")
