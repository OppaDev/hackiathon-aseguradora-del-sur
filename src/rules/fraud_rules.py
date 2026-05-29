"""
Fase 4 — Motor de reglas antifraude.

Aplica 24 reglas sobre una fila de claims_with_documents para generar
puntos de riesgo, alertas y explicaciones en español para el analista.

IMPORTANTE: Ninguna regla acusa fraude directamente. El sistema genera
señales de revisión que deben ser evaluadas por un analista humano.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tipos de datos
# ---------------------------------------------------------------------------

SEVERIDADES = {"CRÍTICO": 4, "ALTO": 3, "MEDIO": 2, "BAJO": 1}


@dataclass
class RuleResult:
    code: str
    fired: bool
    points: int
    severity: str
    alert_text: str       # texto corto para UI
    explanation: str      # texto largo para el analista


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if pd.notna(val) else default
    except (TypeError, ValueError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if pd.notna(val) else default
    except (TypeError, ValueError):
        return default


def _safe_bool(val) -> bool:
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "sí", "si")
    try:
        return bool(val) if pd.notna(val) else False
    except Exception:
        return False


def _is_madrugada(hora_str: Optional[str]) -> bool:
    """Devuelve True si la hora está entre 00:00 y 05:59."""
    if not hora_str or not isinstance(hora_str, str):
        return False
    try:
        h = int(hora_str.split(":")[0])
        return 0 <= h < 6
    except (ValueError, IndexError):
        return False


# ---------------------------------------------------------------------------
# Definición de reglas
# ---------------------------------------------------------------------------

def _eval_rules(row: dict) -> list[RuleResult]:
    results = []

    dias_inicio    = _safe_float(row.get("dias_desde_inicio_poliza"))
    dias_fin       = _safe_float(row.get("dias_hasta_fin_poliza"))
    dias_reporte   = _safe_float(row.get("dias_ocurrencia_reporte"))
    historial_sin  = _safe_int(row.get("historial_siniestros_asegurado"))
    reclamos_12m   = _safe_int(row.get("n_reclamos_12_meses"))
    reclamos_hist  = _safe_int(row.get("n_reclamos_historico"))
    rc_sin_tercero = _safe_int(row.get("reclamos_rc_sin_tercero"))
    ratio_monto    = _safe_float(row.get("ratio_monto_suma"))
    delta_prov     = _safe_float(row.get("delta_monto_proveedor"))
    prom_prov      = _safe_float(row.get("promedio_monto_proveedor"))
    monto_rec      = _safe_float(row.get("monto_reclamado"))
    similitud      = _safe_float(row.get("similitud_narrativa"))
    prov_restric   = _safe_bool(row.get("proveedor_lista_restrictiva"))
    docs_ok        = _safe_bool(row.get("docs_completos"))

    # Señales documentales
    factura_alt    = _safe_bool(row.get("doc_factura_alterada"))
    ruc_inv        = _safe_bool(row.get("doc_ruc_invalido"))
    caso_fraude    = _safe_bool(row.get("doc_caso_fraude"))
    parte_tardio_d = _safe_float(row.get("doc_parte_tardio_dias"), default=None)
    sin_denuncia   = _safe_bool(row.get("doc_sin_denuncia_previa"))
    doc_robo       = _safe_bool(row.get("doc_robo"))
    perdida_total  = _safe_bool(row.get("doc_perdida_total"))
    tercero_id     = _safe_bool(row.get("doc_tercero_identificado"))
    sin_testigos   = _safe_bool(row.get("doc_sin_testigos"))
    sin_interv     = _safe_bool(row.get("doc_sin_intervencion"))
    hora_acc       = row.get("doc_hora_accidente")
    fecha_fac_min  = row.get("doc_fecha_factura_min")
    fecha_ocurr    = row.get("fecha_ocurrencia")

    # --- R001: Reclamo en primeros 10 días de vigencia ---
    fired = dias_inicio is not None and 0 <= dias_inicio <= 10
    results.append(RuleResult(
        code="R001", fired=fired, points=8 if fired else 0,
        severity="CRÍTICO",
        alert_text="Siniestro en primeros 10 días de póliza",
        explanation=(
            f"El siniestro ocurrió {_safe_int(dias_inicio)} día(s) después del inicio de la póliza. "
            "Un siniestro en los primeros 10 días es una señal de posible fraude premeditado "
            "(contratación de póliza con conocimiento previo del evento)."
        ) if fired else "",
    ))

    # --- R002: Reclamo entre 11-30 días de vigencia ---
    fired = dias_inicio is not None and 11 <= dias_inicio <= 30
    results.append(RuleResult(
        code="R002", fired=fired, points=4 if fired else 0,
        severity="ALTO",
        alert_text="Siniestro entre 11-30 días de inicio de póliza",
        explanation=(
            f"El siniestro ocurrió {_safe_int(dias_inicio)} día(s) después del inicio de la póliza. "
            "Los siniestros en las primeras semanas merecen verificación adicional."
        ) if fired else "",
    ))

    # --- R003: Reclamo en últimos 10 días de vigencia ---
    fired = dias_fin is not None and 0 <= dias_fin <= 10
    results.append(RuleResult(
        code="R003", fired=fired, points=8 if fired else 0,
        severity="CRÍTICO",
        alert_text="Siniestro en últimos 10 días de póliza",
        explanation=(
            f"El siniestro ocurrió cuando faltaban {_safe_int(dias_fin)} día(s) para el vencimiento. "
            "Un siniestro al borde del fin de vigencia puede indicar aprovechamiento "
            "deliberado de la cobertura antes de su expiración."
        ) if fired else "",
    ))

    # --- R004: Reclamo entre 11-30 días del fin ---
    fired = dias_fin is not None and 11 <= dias_fin <= 30
    results.append(RuleResult(
        code="R004", fired=fired, points=4 if fired else 0,
        severity="ALTO",
        alert_text="Siniestro entre 11-30 días del vencimiento de póliza",
        explanation=(
            f"El siniestro ocurrió con {_safe_int(dias_fin)} días restantes de vigencia. "
            "Se recomienda verificación del contexto del siniestro."
        ) if fired else "",
    ))

    # --- R004b: Borde extremo < 48h (inicio o fin) ---
    fired = (
        (dias_inicio is not None and dias_inicio < 2) or
        (dias_fin is not None and dias_fin < 2)
    )
    results.append(RuleResult(
        code="R004b", fired=fired, points=10 if fired else 0,
        severity="CRÍTICO",
        alert_text="Siniestro en borde extremo de vigencia (<48h)",
        explanation=(
            "El siniestro ocurrió dentro de las 48 horas del inicio o fin de la póliza. "
            "Este patrón es altamente inusual y requiere revisión prioritaria."
        ) if fired else "",
    ))

    # --- R005: Reporte tardío > 7 días ---
    fired = dias_reporte > 7
    results.append(RuleResult(
        code="R005", fired=fired, points=5 if fired else 0,
        severity="MEDIO",
        alert_text=f"Reporte tardío ({_safe_int(dias_reporte)} días)",
        explanation=(
            f"El siniestro fue reportado {_safe_int(dias_reporte)} días después de ocurrido. "
            "Un reporte con más de 7 días de demora puede indicar preparación o coordinación "
            "posterior al evento."
        ) if fired else "",
    ))

    # --- R006: Robo con denuncia > 4 días ---
    parte_tardio_d_int = _safe_float(row.get("doc_parte_tardio_dias")) if parte_tardio_d is not None else 0
    fired = doc_robo and parte_tardio_d is not None and parte_tardio_d_int > 4
    results.append(RuleResult(
        code="R006", fired=fired, points=8 if fired else 0,
        severity="CRÍTICO",
        alert_text=f"Robo con parte policial tardío ({_safe_int(parte_tardio_d_int)} días)",
        explanation=(
            f"Se reporta robo pero el parte policial se elaboró {_safe_int(parte_tardio_d_int)} "
            "días después del hecho. Una denuncia tardía de robo es inconsistente con "
            "el comportamiento esperado de una víctima real."
        ) if fired else "",
    ))

    # --- R007: Robo con denuncia en 1-4 días ---
    fired = doc_robo and parte_tardio_d is not None and 1 <= parte_tardio_d_int <= 4
    results.append(RuleResult(
        code="R007", fired=fired, points=4 if fired else 0,
        severity="ALTO",
        alert_text=f"Robo con parte policial con {_safe_int(parte_tardio_d_int)} días de demora",
        explanation=(
            f"El parte policial de robo tiene {_safe_int(parte_tardio_d_int)} día(s) de retraso. "
            "Se recomienda verificar la coherencia del relato con la fecha del hecho."
        ) if fired else "",
    ))

    # --- R008: Alta frecuencia de reclamos del asegurado ---
    max_rec = max(historial_sin, reclamos_hist)
    fired = max_rec >= 3
    results.append(RuleResult(
        code="R008", fired=fired, points=8 if fired else 0,
        severity="ALTO",
        alert_text=f"Asegurado con historial alto ({max_rec} reclamos previos)",
        explanation=(
            f"El asegurado registra {max_rec} reclamo(s) previos. "
            "Una frecuencia de siniestros significativamente superior al promedio "
            "del portafolio amerita revisión del perfil de riesgo."
        ) if fired else "",
    ))

    # --- R009: Alta frecuencia en últimos 12 meses ---
    fired = reclamos_12m >= 3
    results.append(RuleResult(
        code="R009", fired=fired, points=6 if fired else 0,
        severity="ALTO",
        alert_text=f"Alta frecuencia en 12 meses ({reclamos_12m} reclamos)",
        explanation=(
            f"El asegurado registra {reclamos_12m} reclamo(s) en los últimos 12 meses. "
            "Esta concentración temporal es un indicador de posible uso indebido de la póliza."
        ) if fired else "",
    ))

    # --- R010: Alta frecuencia RC sin tercero identificado ---
    fired = rc_sin_tercero > 2
    results.append(RuleResult(
        code="R010", fired=fired, points=6 if fired else 0,
        severity="MEDIO",
        alert_text=f"Múltiples reclamos RC sin tercero ({rc_sin_tercero} eventos)",
        explanation=(
            f"El asegurado registra {rc_sin_tercero} reclamos por RC sin tercero identificado. "
            "Este patrón puede indicar reclamos fabricados o sin contrapartes verificables."
        ) if fired else "",
    ))

    # --- R011: Proveedor en lista restrictiva ---
    fired = prov_restric
    results.append(RuleResult(
        code="R011", fired=fired, points=10 if fired else 0,
        severity="CRÍTICO",
        alert_text="Proveedor en lista restrictiva",
        explanation=(
            "El proveedor asociado a este siniestro se encuentra en la lista restrictiva "
            "de la aseguradora. Esto implica antecedentes de irregularidades documentadas."
        ) if fired else "",
    ))

    # --- R012: Factura alterada detectada ---
    fired = factura_alt
    results.append(RuleResult(
        code="R012", fired=fired, points=15 if fired else 0,
        severity="CRÍTICO",
        alert_text="Factura con señal de alteración documental",
        explanation=(
            "El análisis del PDF de factura detectó indicadores de alteración documental. "
            "Una factura adulterada invalida el soporte del reclamo y constituye "
            "una señal crítica que requiere investigación inmediata."
        ) if fired else "",
    ))

    # --- R013: RUC inválido en factura ---
    fired = ruc_inv
    results.append(RuleResult(
        code="R013", fired=fired, points=10 if fired else 0,
        severity="CRÍTICO",
        alert_text="Factura con RUC inválido",
        explanation=(
            "La factura presenta un RUC marcado como inválido o no registrado. "
            "Un proveedor con RUC inválido no puede emitir facturas legalmente válidas, "
            "lo que invalida el soporte del reclamo."
        ) if fired else "",
    ))

    # --- R014: Narrativa clonada (≥ 85% similitud) ---
    fired = similitud >= 0.85
    results.append(RuleResult(
        code="R014", fired=fired, points=8 if fired else 0,
        severity="CRÍTICO",
        alert_text=f"Narrativa prácticamente idéntica a otro reclamo ({similitud:.0%})",
        explanation=(
            f"La descripción del evento tiene una similitud del {similitud:.0%} con otro siniestro. "
            "Una similitud tan alta sugiere que la narrativa fue copiada, lo que apunta "
            "a un reclamo fabricado o coordinado."
        ) if fired else "",
    ))

    # --- R015: Narrativa similar (70-84%) ---
    fired = 0.70 <= similitud < 0.85
    results.append(RuleResult(
        code="R015", fired=fired, points=4 if fired else 0,
        severity="ALTO",
        alert_text=f"Narrativa similar a otro reclamo ({similitud:.0%})",
        explanation=(
            f"La descripción del evento tiene una similitud del {similitud:.0%} con otro siniestro. "
            "Se recomienda comparar ambos reclamos para descartar coordinación."
        ) if fired else "",
    ))

    # --- R016: Monto > 95% de la suma asegurada ---
    fired = ratio_monto > 0.95
    results.append(RuleResult(
        code="R016", fired=fired, points=5 if fired else 0,
        severity="ALTO",
        alert_text=f"Monto reclamado supera el 95% de la suma asegurada ({ratio_monto:.0%})",
        explanation=(
            f"El monto reclamado representa el {ratio_monto:.0%} de la suma asegurada. "
            "Reclamos cercanos al límite máximo de cobertura pueden indicar inflación "
            "deliberada del valor del daño."
        ) if fired else "",
    ))

    # --- R017: Monto > 50% sobre promedio del proveedor ---
    fired = prom_prov > 0 and monto_rec > prom_prov * 1.5
    results.append(RuleResult(
        code="R017", fired=fired, points=4 if fired else 0,
        severity="MEDIO",
        alert_text=f"Monto 50% sobre promedio del proveedor",
        explanation=(
            f"El monto reclamado (${monto_rec:,.0f}) supera en más del 50% el promedio "
            f"de este proveedor (${prom_prov:,.0f}). Puede indicar sobrefacturación."
        ) if fired else "",
    ))

    # --- R018: Parte policial tardío > 7 días ---
    parte_d = _safe_float(row.get("doc_parte_tardio_dias"), default=None)
    fired = parte_d is not None and _safe_float(row.get("doc_parte_tardio_dias")) > 7
    results.append(RuleResult(
        code="R018", fired=fired, points=6 if fired else 0,
        severity="ALTO",
        alert_text=f"Parte policial elaborado con más de 7 días de retraso",
        explanation=(
            f"El parte policial fue elaborado {_safe_int(row.get('doc_parte_tardio_dias'))} "
            "días después del hecho. Un retraso superior a 7 días en la elaboración del "
            "parte es inusual y puede indicar fabricación posterior del documento."
        ) if fired else "",
    ))

    # --- R019: Robo sin denuncia policial previa ---
    fired = doc_robo and sin_denuncia
    results.append(RuleResult(
        code="R019", fired=fired, points=12 if fired else 0,
        severity="CRÍTICO",
        alert_text="Robo declarado sin denuncia policial previa",
        explanation=(
            "El parte policial indica robo pero no existe denuncia policial previa al evento. "
            "En Ecuador, un robo real generalmente genera una denuncia inmediata. "
            "La ausencia de denuncia previa es una señal crítica de posible fraude."
        ) if fired else "",
    ))

    # --- R020: Sin tercero identificado con daño significativo ---
    fired = not tercero_id and sin_interv and monto_rec > 5000
    results.append(RuleResult(
        code="R020", fired=fired, points=5 if fired else 0,
        severity="MEDIO",
        alert_text="Daño significativo sin tercero identificado ni intervención policial",
        explanation=(
            f"El siniestro reporta daño por ${monto_rec:,.0f} sin tercero identificado "
            "y sin intervención policial. Esta combinación dificulta la verificación "
            "independiente de los hechos declarados."
        ) if fired else "",
    ))

    # --- R021: Pérdida total por robo ---
    fired = perdida_total and doc_robo
    results.append(RuleResult(
        code="R021", fired=fired, points=8 if fired else 0,
        severity="CRÍTICO",
        alert_text="Pérdida total declarada por robo",
        explanation=(
            "El siniestro declara pérdida total del vehículo por robo. "
            "Este tipo de reclamo tiene el mayor impacto económico y requiere "
            "verificación exhaustiva de todas las evidencias disponibles."
        ) if fired else "",
    ))

    # --- R022: Accidente de madrugada sin testigos ---
    es_madrugada = _is_madrugada(hora_acc) if hora_acc else False
    fired = es_madrugada and sin_testigos
    results.append(RuleResult(
        code="R022", fired=fired, points=6 if fired else 0,
        severity="MEDIO",
        alert_text=f"Accidente en madrugada ({hora_acc}) sin testigos",
        explanation=(
            f"El accidente ocurrió a las {hora_acc} (madrugada) sin testigos reportados. "
            "Los siniestros nocturnos sin testigos son difíciles de verificar y "
            "presentan mayor riesgo de fabricación."
        ) if fired else "",
    ))

    # --- R023: Documentos incompletos ---
    fired = not docs_ok
    results.append(RuleResult(
        code="R023", fired=fired, points=4 if fired else 0,
        severity="BAJO",
        alert_text="Expediente con documentación incompleta",
        explanation=(
            "El siniestro tiene documentación incompleta según el sistema. "
            "La falta de documentos de soporte puede ser señal de un reclamo "
            "que no puede sustentarse apropiadamente."
        ) if fired else "",
    ))

    # --- R024: Fecha de factura previa al siniestro ---
    fecha_fac_es_previa = False
    if fecha_fac_min and fecha_ocurr:
        try:
            fecha_fac_es_previa = str(fecha_fac_min) < str(fecha_ocurr)
        except Exception:
            pass
    fired = fecha_fac_es_previa
    results.append(RuleResult(
        code="R024", fired=fired, points=10 if fired else 0,
        severity="CRÍTICO",
        alert_text="Fecha de factura anterior a la fecha del siniestro",
        explanation=(
            f"La factura más temprana (fecha: {fecha_fac_min}) es anterior a la fecha "
            f"del siniestro ({fecha_ocurr}). Una factura emitida antes del daño es "
            "una inconsistencia documental grave."
        ) if fired else "",
    ))

    return results


# ---------------------------------------------------------------------------
# Función pública principal
# ---------------------------------------------------------------------------

def apply_rules(row: dict) -> dict:
    """
    Aplica las 24 reglas antifraude a una fila del DataFrame.

    Parámetros:
        row: dict o pd.Series con los campos de claims_with_documents.

    Devuelve:
        dict con rule_points, alerts, critical_flags, explanations, severity_max.
    """
    if isinstance(row, pd.Series):
        row = row.to_dict()

    results = _eval_rules(row)
    fired   = [r for r in results if r.fired]

    rule_points    = sum(r.points for r in fired)
    alerts         = [r.code for r in fired]
    critical_flags = [r.code for r in fired if r.severity == "CRÍTICO"]
    explanations   = [r.explanation for r in fired if r.explanation]

    if fired:
        severity_max = max(fired, key=lambda r: SEVERIDADES.get(r.severity, 0)).severity
    else:
        severity_max = "NINGUNA"

    return {
        "rule_points":    rule_points,
        "alerts":         alerts,
        "critical_flags": critical_flags,
        "explanations":   explanations,
        "severity_max":   severity_max,
        "n_rules_fired":  len(fired),
        "n_critical":     len(critical_flags),
    }


def apply_rules_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica las 24 reglas a todo el DataFrame y añade columnas de resultado.
    Devuelve el DataFrame con columnas rule_* añadidas.
    """
    results = df.apply(apply_rules, axis=1, result_type="expand")

    # Serializar listas como strings separadas por | para CSV
    for col in ["alerts", "critical_flags", "explanations"]:
        if col in results.columns:
            results[col] = results[col].apply(lambda x: "|".join(x) if isinstance(x, list) else "")

    results = results.rename(columns={
        "rule_points":    "rule_points",
        "alerts":         "rule_alerts",
        "critical_flags": "rule_critical_flags",
        "explanations":   "rule_explanations",
        "severity_max":   "rule_severity_max",
        "n_rules_fired":  "rule_n_rules_fired",
        "n_critical":     "rule_n_critical",
    })

    return pd.concat([df, results], axis=1)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    root = Path(__file__).resolve().parents[2]

    df = pd.read_csv(root / "data" / "processed" / "claims_with_documents.csv")
    df_scored = apply_rules_df(df)

    print(f"\n{'='*55}")
    print(f"  Siniestros evaluados: {len(df_scored)}")
    print(f"  Columnas de reglas:   {[c for c in df_scored.columns if c.startswith('rule_')]}")

    print(f"\n  Distribución de severidad máxima:")
    for sev, cnt in df_scored["rule_severity_max"].value_counts().items():
        print(f"    {sev}: {cnt}")

    print(f"\n  Top 10 por puntos de reglas:")
    top = df_scored.nlargest(10, "rule_points")[
        ["id_siniestro", "rule_points", "rule_severity_max", "rule_n_critical", "rule_alerts"]
    ]
    for _, r in top.iterrows():
        print(f"    {r['id_siniestro']}: {r['rule_points']} pts | {r['rule_severity_max']} | {r['rule_alerts'][:60]}")
