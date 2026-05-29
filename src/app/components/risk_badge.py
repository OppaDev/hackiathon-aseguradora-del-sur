"""Componentes reutilizables para el dashboard."""

import streamlit as st


NIVEL_COLORS = {
    "ALTO":  ("#dc2626", "#fee2e2"),   # rojo
    "MEDIO": ("#d97706", "#fef3c7"),   # ámbar
    "BAJO":  ("#16a34a", "#dcfce7"),   # verde
}


def risk_badge(nivel: str) -> str:
    """HTML de badge coloreado para nivel de riesgo."""
    color, bg = NIVEL_COLORS.get(nivel, ("#6b7280", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{color};padding:3px 10px;'
        f'border-radius:12px;font-weight:700;font-size:0.85em;">{nivel}</span>'
    )


def score_gauge_html(score: float, nivel: str) -> str:
    """Barra de progreso HTML coloreada según nivel."""
    color, _ = NIVEL_COLORS.get(nivel, ("#6b7280", "#f3f4f6"))
    return (
        f'<div style="background:#e5e7eb;border-radius:8px;height:18px;width:100%;">'
        f'<div style="background:{color};border-radius:8px;height:18px;width:{score:.0f}%;'
        f'transition:width 0.3s ease;"></div></div>'
        f'<p style="text-align:center;font-weight:700;font-size:1.1em;margin:4px 0;">'
        f'{score:.0f}/100</p>'
    )


def metric_card(title: str, value: str, delta: str = "", color: str = "#1e3a5f") -> None:
    """Tarjeta de métrica estilizada."""
    st.markdown(
        f"""<div style="background:#f8fafc;border-left:4px solid {color};
        padding:12px 16px;border-radius:6px;margin-bottom:8px;">
        <p style="color:#6b7280;font-size:0.8em;margin:0;">{title}</p>
        <p style="color:{color};font-size:1.6em;font-weight:700;margin:4px 0;">{value}</p>
        {'<p style="color:#6b7280;font-size:0.75em;margin:0;">'+delta+'</p>' if delta else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def agent_mode_pill(mode: str) -> None:
    """Indicador del modo del agente IA."""
    if "api" in mode.lower() or "claude" in mode.lower():
        st.markdown(
            '<span style="background:#dbeafe;color:#1d4ed8;padding:3px 10px;'
            'border-radius:12px;font-size:0.8em;">🤖 Claude API activo</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="background:#f3f4f6;color:#6b7280;padding:3px 10px;'
            'border-radius:12px;font-size:0.8em;">⚙️ Modo fallback (sin API)</span>',
            unsafe_allow_html=True,
        )
