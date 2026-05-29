"""
Fase 10 — Agente IA con Claude API.

Modos de operación:
  Modo A (principal): usa Anthropic Claude API via ANTHROPIC_API_KEY.
  Modo B (fallback):  genera análisis determinístico basado en reglas cuando
                      la API key no está disponible.

El agente NUNCA:
  - Acusa a un asegurado de cometer fraude.
  - Rechaza automáticamente un siniestro.
  - Emite juicios legales ni definitivos.

El agente SIEMPRE:
  - Usa frases como "posible señal de riesgo", "requiere revisión".
  - Recomienda acción humana como paso final.
  - Indica el nivel de confianza y las limitaciones del análisis.
"""

import os
import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Carga de API key  (dotenv local  →  st.secrets en Cloud)
# ---------------------------------------------------------------------------

def _load_api_key() -> Optional[str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # Buscar .env recorriendo hacia arriba desde el archivo actual y desde cwd
    try:
        from dotenv import load_dotenv
        candidates = []
        try:
            candidates.append(Path(__file__).resolve().parents[2] / ".env")
        except Exception:
            pass
        candidates.append(Path.cwd() / ".env")
        # Buscar subiendo desde cwd
        p = Path.cwd()
        for _ in range(5):
            candidates.append(p / ".env")
            p = p.parent
        for env_path in candidates:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                key = os.environ.get("ANTHROPIC_API_KEY", "")
                if key:
                    return key
    except ImportError:
        pass
    # Intentar st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        pass
    return None


ANTHROPIC_API_KEY = _load_api_key()
_API_AVAILABLE = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "sk-ant-your-key-here")


# ---------------------------------------------------------------------------
# System prompt — directrices éticas obligatorias
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""
    Eres un asistente especializado en análisis antifraude para seguros en Ecuador,
    desarrollado por el equipo de datos de Aseguradora del Sur.

    ## Tu rol
    Analizar siniestros y señalar posibles indicadores de riesgo para que el equipo
    humano de la Unidad Antifraude realice la revisión correspondiente.

    ## Normas éticas OBLIGATORIAS — sin excepciones
    1. NUNCA afirmes que un siniestro es fraudulento. Solo identifies "posibles señales
       de riesgo" o "indicadores que requieren revisión".
    2. NUNCA rechaces ni apruebes un siniestro. Eso es competencia exclusiva del equipo
       humano.
    3. NUNCA hagas afirmaciones sobre la culpabilidad del asegurado o del proveedor.
    4. Usa SIEMPRE lenguaje condicional y cauteloso:
       - "posible señal de riesgo"
       - "podría indicar"
       - "requiere revisión adicional"
       - "se recomienda verificar"
       - "el análisis sugiere"
    5. Concluye SIEMPRE con una recomendación de acción humana.

    ## Formato de respuesta
    - Responde en español, de forma clara y estructurada.
    - Para análisis de siniestros: usa secciones con viñetas.
    - Para preguntas generales: respuesta directa y concisa.
    - Para reportes: incluye tabla de resumen cuando corresponda.
    - Máximo 500 palabras salvo que se solicite explícitamente más detalle.

    ## Contexto del sistema
    - Dataset: 500 siniestros analizados
    - Motor de reglas: 24 reglas antifraude (R001–R024)
    - Modelo ML: RandomForest + IsolationForest (AUC-ROC 1.0, CV F1 0.951)
    - Score final: 40% reglas + 25% documental + 20% modelo + 15% NLP
    - Niveles: BAJO (≤30), MEDIO (31–65), ALTO (>65)
""").strip()


# ---------------------------------------------------------------------------
# Construcción de contexto para el prompt
# ---------------------------------------------------------------------------

def _build_claim_context(row: pd.Series, shap_top: list[dict] = None) -> str:
    """Serializa los datos de un siniestro a texto estructurado para el prompt."""
    lines = [
        f"## Siniestro: {row.get('id_siniestro', 'N/D')}",
        "",
        "### Datos generales",
        f"- Asegurado: {row.get('id_asegurado', 'N/D')}",
        f"- Proveedor:  {row.get('id_proveedor', 'N/D')}",
        f"- Tipo:       {row.get('tipo_siniestro', 'N/D')}",
        f"- Monto reclamado: ${float(row.get('monto_reclamado', 0) or 0):,.2f}",
        f"- Monto estimado:  ${float(row.get('monto_estimado', 0) or 0):,.2f}",
        f"- Días inicio póliza → siniestro: {row.get('dias_desde_inicio_poliza', 'N/D')}",
        f"- Días ocurrencia → reporte:       {row.get('dias_ocurrencia_reporte', 'N/D')}",
        f"- Descripción: {str(row.get('descripcion', ''))[:200]}",
        "",
        "### Score de riesgo",
        f"- Score final:      {float(row.get('score_riesgo', 0) or 0):.1f} / 100",
        f"- Nivel de riesgo:  {row.get('nivel_riesgo', 'N/D')}",
        f"- Score reglas:     {float(row.get('score_reglas', 0) or 0):.1f}",
        f"- Score documental: {float(row.get('score_documental', 0) or 0):.1f}",
        f"- Score modelo ML:  {float(row.get('score_modelo', 0) or 0):.1f}",
        f"- Score NLP:        {float(row.get('score_nlp', 0) or 0):.1f}",
    ]

    # Reglas disparadas
    alerts = str(row.get("rule_alerts", "") or "")
    if alerts.strip():
        lines += ["", "### Reglas antifraude disparadas"]
        for a in alerts.split("|"):
            a = a.strip()
            if a:
                lines.append(f"- {a}")

    explanations = str(row.get("rule_explanations", "") or "")
    if explanations.strip():
        lines += ["", "### Explicaciones de reglas"]
        for e in explanations.split("|"):
            e = e.strip()
            if e:
                lines.append(f"- {e}")

    # Señales documentales
    doc_flags = []
    for col in ["doc_factura_alterada", "doc_ruc_invalido", "doc_parte_tardio",
                "doc_sin_denuncia_previa", "doc_sin_testigos", "doc_robo",
                "doc_perdida_total"]:
        val = row.get(col, False)
        if val and str(val) not in ("0", "False", "nan"):
            doc_flags.append(col.replace("doc_", "").replace("_", " ").title())
    if doc_flags:
        lines += ["", "### Señales documentales detectadas"]
        for f in doc_flags:
            lines.append(f"- {f}")

    # Historial
    hist = int(row.get("historial_siniestros_asegurado", 0) or 0)
    if hist > 0:
        lines += [
            "",
            "### Historial del asegurado",
            f"- Siniestros anteriores: {hist}",
            f"- Reclamos últimos 12 meses: {row.get('n_reclamos_12_meses', 0)}",
        ]

    # Similitud narrativa
    sim = float(row.get("similitud_narrativa", 0) or 0)
    if sim > 0.5:
        lines += [
            "",
            "### Análisis NLP",
            f"- Similitud narrativa con otro siniestro: {sim:.1%}",
            f"- Narrativa clonada: {bool(row.get('narrativa_clonada', False))}",
            f"- Narrativa similar:  {bool(row.get('narrativa_similar', False))}",
        ]

    # SHAP top features
    if shap_top:
        lines += ["", "### Features con mayor influencia en el modelo (SHAP)"]
        for item in shap_top[:5]:
            feat = item.get("feature", "?")
            val  = item.get("shap_value", 0)
            dire = item.get("direction", "")
            lines.append(f"- {feat}: {val:+.4f}  ({dire})")

    return "\n".join(lines)


def _build_portfolio_context(df: pd.DataFrame) -> str:
    """Resumen estadístico del portafolio para preguntas generales."""
    dist = df["nivel_riesgo"].value_counts().to_dict() if "nivel_riesgo" in df.columns else {}
    top5 = (
        df.nlargest(5, "score_riesgo")[["id_siniestro", "score_riesgo", "nivel_riesgo"]]
        .to_string(index=False)
        if "score_riesgo" in df.columns else "N/D"
    )
    lines = [
        "## Contexto del portafolio",
        f"- Total siniestros: {len(df)}",
        f"- Distribución niveles: {dist}",
        f"- Score medio: {df['score_riesgo'].mean():.1f}" if "score_riesgo" in df.columns else "",
        "",
        "Top 5 por score de riesgo:",
        top5,
    ]
    return "\n".join(l for l in lines if l is not None)


# ---------------------------------------------------------------------------
# Modo A — Claude API
# ---------------------------------------------------------------------------

def _call_claude(
    user_message: str,
    system: str = SYSTEM_PROMPT,
    max_tokens: int = 800,
    model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Llama a la API de Claude y devuelve el texto de respuesta."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Modo B — Fallback determinístico (sin API key)
# ---------------------------------------------------------------------------

def _fallback_analyze_claim(row: pd.Series) -> str:
    """Análisis determinístico cuando la API no está disponible."""
    sin_id    = row.get("id_siniestro", "N/D")
    score     = float(row.get("score_riesgo", 0) or 0)
    nivel     = row.get("nivel_riesgo", "BAJO")
    alerts    = str(row.get("rule_alerts", "") or "")
    n_reglas  = int(row.get("rule_n_rules_fired", 0) or 0)
    n_crit    = int(row.get("rule_n_critical", 0) or 0)

    nivel_desc = {
        "BAJO":  "no presenta señales de riesgo significativas",
        "MEDIO": "presenta indicadores que podrían requerir revisión",
        "ALTO":  "presenta múltiples posibles señales de riesgo",
    }.get(nivel, "")

    accion = {
        "BAJO":  "Se puede continuar el flujo normal de liquidación.",
        "MEDIO": "Se recomienda escalar a la Unidad Antifraude para revisión documental.",
        "ALTO":  "Se recomienda detener el pago y solicitar revisión especializada de campo.",
    }.get(nivel, "")

    lines = [
        f"## Análisis de {sin_id}",
        "",
        f"El siniestro **{sin_id}** {nivel_desc} con un score de riesgo de "
        f"**{score:.0f}/100** (Nivel **{nivel}**).",
        "",
    ]

    if n_reglas > 0:
        lines += [
            "### Posibles señales detectadas por el motor de reglas",
            f"- Se activaron **{n_reglas} regla(s)**, de las cuales **{n_crit}** son de carácter crítico.",
        ]
        for a in alerts.split("|"):
            a = a.strip()
            if a:
                lines.append(f"- {a}")
        lines.append("")

    doc_flags = []
    for col in ["doc_factura_alterada", "doc_ruc_invalido", "doc_parte_tardio",
                "doc_sin_denuncia_previa", "doc_sin_testigos"]:
        val = row.get(col, False)
        if val and str(val) not in ("0", "False", "nan"):
            doc_flags.append(col.replace("doc_", "").replace("_", " ").title())

    if doc_flags:
        lines += [
            "### Posibles señales documentales",
            "Los documentos aportados presentan los siguientes indicadores que requieren verificación:",
        ]
        for f in doc_flags:
            lines.append(f"- {f}")
        lines.append("")

    sim = float(row.get("similitud_narrativa", 0) or 0)
    if sim > 0.7:
        lines += [
            "### Análisis de narrativa",
            f"- La descripción del siniestro presenta una similitud del **{sim:.1%}** "
            f"con otro caso registrado, lo que podría requerir revisión adicional.",
            "",
        ]

    lines += ["### Acción recomendada", accion, "", "---", "_Análisis generado automáticamente. Requiere validación humana._"]
    return "\n".join(lines)


def _fallback_answer(question: str, df: pd.DataFrame) -> str:
    """Respuesta básica a preguntas sobre el portafolio sin API."""
    dist = df["nivel_riesgo"].value_counts().to_dict() if "nivel_riesgo" in df.columns else {}
    alto  = dist.get("ALTO", 0)
    medio = dist.get("MEDIO", 0)
    bajo  = dist.get("BAJO", 0)
    total = len(df)

    return (
        f"**Resumen del portafolio** ({total} siniestros):\n\n"
        f"- **ALTO riesgo:** {alto} ({alto/total:.1%})\n"
        f"- **MEDIO riesgo:** {medio} ({medio/total:.1%})\n"
        f"- **BAJO riesgo:** {bajo} ({bajo/total:.1%})\n\n"
        f"*Nota: El agente IA con Claude no está disponible (sin ANTHROPIC_API_KEY). "
        f"Este es el análisis estadístico básico.*\n\n"
        f"Para análisis más detallados configure la variable ANTHROPIC_API_KEY en el archivo `.env`."
    )


# ---------------------------------------------------------------------------
# API pública del agente
# ---------------------------------------------------------------------------

def analyze_claim(
    id_siniestro: str,
    df: pd.DataFrame,
    shap_explanation: list[dict] = None,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """
    Genera un análisis de riesgo narrativo para un siniestro específico.

    Devuelve:
        {
          "id_siniestro": str,
          "analysis":     str,   # texto Markdown
          "mode":         "api" | "fallback",
          "score_riesgo": float,
          "nivel_riesgo": str,
        }
    """
    rows = df[df["id_siniestro"] == id_siniestro]
    if rows.empty:
        return {
            "id_siniestro": id_siniestro,
            "analysis": f"Siniestro {id_siniestro} no encontrado en el dataset.",
            "mode": "error",
            "score_riesgo": 0.0,
            "nivel_riesgo": "N/D",
        }

    row = rows.iloc[0]
    score = float(row.get("score_riesgo", 0) or 0)
    nivel = row.get("nivel_riesgo", "BAJO")

    if _API_AVAILABLE:
        try:
            context = _build_claim_context(row, shap_explanation)
            prompt = (
                f"Analiza el siguiente siniestro y genera un informe de riesgo estructurado "
                f"siguiendo las normas éticas del sistema.\n\n{context}"
            )
            analysis = _call_claude(prompt, max_tokens=700, model=model)
            mode = "api"
        except Exception as e:
            log.warning(f"API Claude error para {id_siniestro}: {e} — usando fallback")
            analysis = _fallback_analyze_claim(row)
            mode = "fallback"
    else:
        analysis = _fallback_analyze_claim(row)
        mode = "fallback"

    return {
        "id_siniestro": id_siniestro,
        "analysis":     analysis,
        "mode":         mode,
        "score_riesgo": score,
        "nivel_riesgo": nivel,
    }


def answer_question(
    question: str,
    df: pd.DataFrame,
    id_siniestro: str = None,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """
    Responde una pregunta en lenguaje natural sobre el portafolio o un siniestro.

    Devuelve:
        {
          "answer": str,    # texto Markdown
          "mode":   "api" | "fallback",
        }
    """
    if _API_AVAILABLE:
        try:
            # Construir contexto
            if id_siniestro:
                rows = df[df["id_siniestro"] == id_siniestro]
                ctx  = _build_claim_context(rows.iloc[0]) if not rows.empty else ""
            else:
                ctx = _build_portfolio_context(df)

            prompt = f"{ctx}\n\n---\nPregunta del analista: {question}"
            answer = _call_claude(prompt, max_tokens=600, model=model)
            mode = "api"
        except Exception as e:
            log.warning(f"API Claude error: {e} — usando fallback")
            answer = _fallback_answer(question, df)
            mode = "fallback"
    else:
        answer = _fallback_answer(question, df)
        mode = "fallback"

    return {"answer": answer, "mode": mode}


def generate_executive_summary(
    df: pd.DataFrame,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """
    Genera un resumen ejecutivo del portafolio de siniestros para el dashboard principal.

    Devuelve:
        {
          "summary": str,   # texto Markdown
          "mode":    "api" | "fallback",
          "stats":   dict,
        }
    """
    dist  = df["nivel_riesgo"].value_counts().to_dict() if "nivel_riesgo" in df.columns else {}
    stats = {
        "total":     len(df),
        "alto":      dist.get("ALTO", 0),
        "medio":     dist.get("MEDIO", 0),
        "bajo":      dist.get("BAJO", 0),
        "score_med": round(float(df["score_riesgo"].mean()), 1) if "score_riesgo" in df.columns else 0,
        "score_max": round(float(df["score_riesgo"].max()), 1) if "score_riesgo" in df.columns else 0,
    }

    top5 = []
    if "score_riesgo" in df.columns:
        for _, r in df.nlargest(5, "score_riesgo").iterrows():
            top5.append(
                f"{r['id_siniestro']}: {r['score_riesgo']:.0f}/100 ({r['nivel_riesgo']})"
            )

    if _API_AVAILABLE:
        try:
            ctx = _build_portfolio_context(df)
            prompt = (
                f"{ctx}\n\n---\n"
                "Genera un resumen ejecutivo breve (máximo 200 palabras) del estado del portafolio "
                "de siniestros para el Director de Suscripción. Incluye: distribución de riesgo, "
                "patrones relevantes detectados y recomendación de priorización."
            )
            summary = _call_claude(prompt, max_tokens=400, model=model)
            mode = "api"
        except Exception as e:
            log.warning(f"API Claude error en resumen ejecutivo: {e} — usando fallback")
            summary = _fallback_executive_summary(stats, top5)
            mode = "fallback"
    else:
        summary = _fallback_executive_summary(stats, top5)
        mode = "fallback"

    return {"summary": summary, "mode": mode, "stats": stats}


def _fallback_executive_summary(stats: dict, top5: list[str]) -> str:
    total = stats["total"]
    alto  = stats["alto"]
    medio = stats["medio"]
    bajo  = stats["bajo"]

    lines = [
        "## Resumen Ejecutivo — Portafolio de Siniestros",
        "",
        f"Del total de **{total} siniestros** analizados:",
        "",
        f"- **{alto}** ({alto/total:.1%}) presentan posibles señales de riesgo **ALTO** — requieren revisión especializada.",
        f"- **{medio}** ({medio/total:.1%}) presentan indicadores de riesgo **MEDIO** — se recomienda revisión documental.",
        f"- **{bajo}** ({bajo/total:.1%}) no presentan señales significativas (nivel **BAJO**).",
        "",
        f"El score promedio del portafolio es **{stats['score_med']:.1f}/100** "
        f"(máximo observado: {stats['score_max']:.0f}/100).",
    ]

    if top5:
        lines += ["", "**Siniestros que requieren atención prioritaria:**"]
        for t in top5:
            lines.append(f"- {t}")

    lines += [
        "",
        "*Este análisis es orientativo. Las decisiones finales corresponden al equipo humano de la Unidad Antifraude.*",
    ]
    return "\n".join(lines)


def get_agent_status() -> dict:
    """Devuelve el estado del agente para mostrar en el dashboard."""
    return {
        "api_available": _API_AVAILABLE,
        "mode": "Claude API (Haiku)" if _API_AVAILABLE else "Fallback (sin API key)",
        "model": "claude-haiku-4-5-20251001" if _API_AVAILABLE else "N/A",
        "message": (
            "Agente IA activo con Claude API."
            if _API_AVAILABLE
            else "Configure ANTHROPIC_API_KEY en .env para activar el agente IA completo."
        ),
    }


# ---------------------------------------------------------------------------
# Ejecución directa — demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    scored_path = root / "data" / "processed" / "claims_scored.csv"
    docs_path   = root / "data" / "processed" / "claims_with_documents.csv"

    if not scored_path.exists():
        print("ERROR: Ejecuta primero src/scoring/risk_score.py para generar claims_scored.csv")
        sys.exit(1)

    scored = pd.read_csv(scored_path)
    docs   = pd.read_csv(docs_path) if docs_path.exists() else scored
    df     = docs.merge(
        scored[["id_siniestro", "score_riesgo", "nivel_riesgo",
                "score_reglas", "score_documental", "score_modelo", "score_nlp",
                "rule_alerts", "rule_explanations", "rule_n_rules_fired", "rule_n_critical"]],
        on="id_siniestro", how="left",
    )

    status = get_agent_status()
    print(f"\nEstado del agente: {status['mode']}")
    print(f"Mensaje: {status['message']}\n")

    # Resumen ejecutivo
    exec_result = generate_executive_summary(df)
    print("=" * 60)
    print(exec_result["summary"])
    print(f"\n[Modo: {exec_result['mode']}]")

    # Análisis del siniestro más riesgoso
    if "score_riesgo" in df.columns:
        top_sin = df.nlargest(1, "score_riesgo").iloc[0]["id_siniestro"]
        print(f"\n{'=' * 60}")
        print(f"Análisis detallado: {top_sin}")
        result = analyze_claim(top_sin, df)
        print(result["analysis"])
        print(f"\n[Modo: {result['mode']}]")
