"""
FraudIA Claims — Dashboard antifraude de siniestros.
Punto de entrada Streamlit: streamlit run src/app/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="FraudIA Claims — Aseguradora del Sur",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.data_loader import load_main_dataframe, load_network_edges, get_data_status, _load_artifacts_cached
from src.app.components.risk_badge import risk_badge, score_gauge_html
from src.models.predict_model import get_model_info, get_shap_explanation
from src.ai_agent.claims_agent import (
    analyze_claim, answer_question,
    generate_executive_summary, get_agent_status,
)

# ---------------------------------------------------------------------------
# Estilo global
# ---------------------------------------------------------------------------

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1e3a5f; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }
h1, h2, h3 { color: #1e3a5f; }
.stDataFrame { font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — navegación y estado
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🛡️ FraudIA Claims")
    st.markdown("*Sistema de detección de señales de riesgo en siniestros*")
    st.divider()

    PAGES = {
        "📊 Resumen ejecutivo":        "overview",
        "🔍 Explorador de siniestros": "explorer",
        "📋 Detalle de siniestro":     "detail",
        "🕸️ Red de relaciones":         "network",
        "🔤 Análisis NLP":             "nlp",
        "🤖 Modelo ML":                "model",
        "💬 Agente IA":                "agent",
        "📥 Cargar siniestros":        "upload",
    }
    page_label = st.radio("Navegación", list(PAGES.keys()), label_visibility="collapsed")
    page = PAGES[page_label]

    st.divider()
    status = get_data_status()
    st.markdown("**Estado del sistema**")
    icons = {True: "✅", False: "❌"}
    st.markdown(f"{icons[status['claims_con_docs']]} Datos cargados")
    st.markdown(f"{icons[status['claims_scored']]} Scoring ejecutado")
    st.markdown(f"{icons[status['model_artifacts']]} Modelo ML")
    st.markdown(f"{icons[status['claims_nlp']]} Análisis NLP")
    st.markdown(f"{icons[status['network_edges']]} Grafo de red")
    st.divider()
    agent_st = get_agent_status()
    if agent_st["api_available"]:
        st.success("🤖 Claude API activo")
    else:
        st.info("⚙️ Modo fallback (sin API)")

# ---------------------------------------------------------------------------
# Carga de datos (cacheada)
# ---------------------------------------------------------------------------

with st.spinner("Cargando datos..."):
    try:
        df = load_main_dataframe()
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

# Columna de tipo = ramo (Vehículos / Hogar / Salud)
TIPO_COL = "ramo" if "ramo" in df.columns else None

# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

# ── 1. RESUMEN EJECUTIVO ────────────────────────────────────────────────────
if page == "overview":
    st.title("📊 Resumen Ejecutivo")
    st.caption("Vista general del portafolio de siniestros analizados")

    dist  = df["nivel_riesgo"].value_counts() if "nivel_riesgo" in df.columns else {}
    alto  = int(dist.get("ALTO",  0))
    medio = int(dist.get("MEDIO", 0))
    bajo  = int(dist.get("BAJO",  0))
    total = len(df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total siniestros", total)
    with c2:
        st.metric("🔴 ALTO riesgo",  alto,  f"{alto/total:.1%} del total")
    with c3:
        st.metric("🟡 MEDIO riesgo", medio, f"{medio/total:.1%} del total")
    with c4:
        st.metric("🟢 BAJO riesgo",  bajo,  f"{bajo/total:.1%} del total")

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Distribución de riesgo")
        fig_pie = px.pie(
            values=[alto, medio, bajo],
            names=["ALTO", "MEDIO", "BAJO"],
            color=["ALTO", "MEDIO", "BAJO"],
            color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
            hole=0.4,
        )
        fig_pie.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("Distribución del score de riesgo")
        if "score_riesgo" in df.columns:
            fig_hist = px.histogram(
                df, x="score_riesgo", nbins=30,
                color_discrete_sequence=["#1e3a5f"],
                labels={"score_riesgo": "Score de riesgo (0-100)"},
            )
            fig_hist.add_vline(x=30, line_dash="dash", line_color="#16a34a",
                               annotation_text="BAJO/MEDIO")
            fig_hist.add_vline(x=65, line_dash="dash", line_color="#dc2626",
                               annotation_text="MEDIO/ALTO")
            fig_hist.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()
    st.subheader("Top 10 siniestros por score de riesgo")
    if "score_riesgo" in df.columns:
        base_cols = ["id_siniestro", "score_riesgo", "nivel_riesgo", "monto_reclamado",
                     "rule_n_rules_fired"]
        if TIPO_COL:
            base_cols.insert(3, TIPO_COL)
        top10 = df.nlargest(10, "score_riesgo")[[c for c in base_cols if c in df.columns]].copy()
        top10["score_riesgo"] = top10["score_riesgo"].round(1)
        rename_map = {
            "id_siniestro": "Siniestro", "score_riesgo": "Score",
            "nivel_riesgo": "Nivel", "monto_reclamado": "Monto ($)",
            "rule_n_rules_fired": "Reglas",
        }
        if TIPO_COL:
            rename_map[TIPO_COL] = "Ramo"
        st.dataframe(top10.rename(columns=rename_map),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💬 Análisis ejecutivo con IA")
    if st.button("Generar resumen ejecutivo con IA", type="primary"):
        with st.spinner("Consultando agente IA..."):
            result = generate_executive_summary(df)
        st.markdown(result["summary"])
        mode_txt = "🤖 Claude API" if result["mode"] == "api" else "⚙️ Modo fallback"
        st.caption(f"Generado con: {mode_txt}")


# ── 2. EXPLORADOR DE SINIESTROS ─────────────────────────────────────────────
elif page == "explorer":
    st.title("🔍 Explorador de siniestros")
    st.caption("Filtra y ordena el portafolio completo")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        nivel_filter = st.multiselect("Nivel de riesgo",
            ["ALTO", "MEDIO", "BAJO"], default=["ALTO", "MEDIO", "BAJO"])
    with col_f2:
        if TIPO_COL:
            tipos = sorted(df[TIPO_COL].dropna().unique().tolist())
            tipo_filter = st.multiselect("Ramo", tipos, default=tipos)
        else:
            tipo_filter = []
    with col_f3:
        score_range = st.slider("Rango de score", 0, 100, (0, 100))
    with col_f4:
        solo_reglas = st.checkbox("Solo con reglas disparadas", value=False)

    mask = (
        df["nivel_riesgo"].isin(nivel_filter) &
        (df["score_riesgo"] >= score_range[0]) &
        (df["score_riesgo"] <= score_range[1])
    )
    if tipo_filter and TIPO_COL:
        mask &= df[TIPO_COL].isin(tipo_filter)
    if solo_reglas and "rule_n_rules_fired" in df.columns:
        mask &= df["rule_n_rules_fired"] > 0

    df_filt = df[mask].copy()
    st.caption(f"Mostrando {len(df_filt)} de {len(df)} siniestros")

    display_cols = ["id_siniestro", "score_riesgo", "nivel_riesgo",
                    "monto_reclamado", "rule_n_rules_fired", "rule_n_critical"]
    if TIPO_COL:
        display_cols.insert(3, TIPO_COL)
    display_cols = [c for c in display_cols if c in df_filt.columns]

    df_show = df_filt[display_cols].sort_values("score_riesgo", ascending=False).copy()
    df_show["score_riesgo"] = df_show["score_riesgo"].round(1)
    rename_map = {
        "id_siniestro": "Siniestro", "score_riesgo": "Score",
        "nivel_riesgo": "Nivel", "monto_reclamado": "Monto ($)",
        "rule_n_rules_fired": "Reglas", "rule_n_critical": "Críticas",
    }
    if TIPO_COL:
        rename_map[TIPO_COL] = "Ramo"

    st.dataframe(df_show.rename(columns=rename_map),
                 use_container_width=True, hide_index=True, height=460)

    if TIPO_COL and "score_riesgo" in df_filt.columns and len(df_filt) > 0:
        st.subheader("Score por ramo")
        fig = px.box(
            df_filt, x=TIPO_COL, y="score_riesgo",
            color="nivel_riesgo",
            color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
            labels={"score_riesgo": "Score de riesgo", TIPO_COL: "Ramo"},
        )
        fig.update_layout(margin=dict(t=20, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)


# ── 3. DETALLE DE SINIESTRO ──────────────────────────────────────────────────
elif page == "detail":
    st.title("📋 Detalle de siniestro")

    sin_options = (df.sort_values("score_riesgo", ascending=False)["id_siniestro"].tolist()
                   if "score_riesgo" in df.columns else df["id_siniestro"].tolist())
    selected_sin = st.selectbox("Selecciona un siniestro", sin_options)

    if selected_sin:
        row   = df[df["id_siniestro"] == selected_sin].iloc[0]
        nivel = str(row.get("nivel_riesgo", "BAJO"))
        score = float(row.get("score_riesgo", 0) or 0)

        col_head, col_badge = st.columns([3, 1])
        with col_head:
            st.subheader(f"Siniestro {selected_sin}")
            ramo_val = row.get(TIPO_COL, "N/D") if TIPO_COL else "N/D"
            st.markdown(
                f"**Ramo:** {ramo_val} | "
                f"**Asegurado:** {row.get('id_asegurado', 'N/D')} | "
                f"**Proveedor:** {row.get('id_proveedor', 'N/D')}"
            )
        with col_badge:
            st.markdown(risk_badge(nivel), unsafe_allow_html=True)
            st.markdown(f"**Score: {score:.0f}/100**")

        st.divider()
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Scores", "⚠️ Alertas", "📄 Documentos", "🤖 Análisis IA"])

        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            nivel_color = {"ALTO": "inverse", "MEDIO": "off", "BAJO": "normal"}.get(nivel, "off")
            with c1:
                st.metric("Score final",      f"{score:.0f}/100")
            with c2:
                st.metric("Score reglas",     f"{float(row.get('score_reglas', 0) or 0):.0f}/100")
            with c3:
                st.metric("Score documental", f"{float(row.get('score_documental', 0) or 0):.0f}/100")
            with c4:
                st.metric("Score ML",         f"{float(row.get('score_modelo', 0) or 0):.0f}/100")

            st.markdown(score_gauge_html(score, nivel), unsafe_allow_html=True)

            st.markdown("**Recomendación:**")
            st.info(str(row.get("recomendacion", "Sin recomendación disponible") or ""))

            sub_scores = {
                "Reglas (40%)":     float(row.get("score_reglas", 0) or 0),
                "Documental (25%)": float(row.get("score_documental", 0) or 0),
                "Modelo ML (20%)":  float(row.get("score_modelo", 0) or 0),
                "NLP (15%)":        float(row.get("score_nlp", 0) or 0),
            }
            fig_bar = px.bar(
                x=list(sub_scores.keys()), y=list(sub_scores.values()),
                labels={"x": "Componente", "y": "Score (0-100)"},
                color=list(sub_scores.values()),
                color_continuous_scale=["#16a34a", "#d97706", "#dc2626"],
                range_color=[0, 100],
            )
            fig_bar.update_coloraxes(showscale=False)
            fig_bar.update_layout(margin=dict(t=20, b=0), height=260, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            alerts       = str(row.get("rule_alerts", "") or "")
            explanations = str(row.get("rule_explanations", "") or "")
            n_fired = int(row.get("rule_n_rules_fired", 0) or 0)
            n_crit  = int(row.get("rule_n_critical", 0) or 0)

            if n_fired == 0:
                st.success("No se dispararon reglas de alerta para este siniestro.")
            else:
                st.warning(f"Se activaron **{n_fired} regla(s)**, de las cuales **{n_crit}** son críticas.")
                if alerts.strip():
                    st.markdown("**Reglas:**")
                    for a in alerts.split("|"):
                        a = a.strip()
                        if a:
                            st.markdown(f"- `{a}`")
                if explanations.strip():
                    st.markdown("**Explicaciones:**")
                    for e in explanations.split("|"):
                        e = e.strip()
                        if e:
                            st.markdown(f"- {e}")

            st.markdown("---")
            st.markdown("**Datos clave:**")
            data_kv = {
                "Monto reclamado":                f"${float(row.get('monto_reclamado', 0) or 0):,.2f}",
                "Monto estimado":                 f"${float(row.get('monto_estimado', 0) or 0):,.2f}",
                "Días inicio póliza → siniestro": str(row.get("dias_desde_inicio_poliza", "N/D")),
                "Días ocurrencia → reporte":      str(row.get("dias_ocurrencia_reporte", "N/D")),
                "Historial siniestros":           str(row.get("historial_siniestros_asegurado", 0)),
                "Similitud narrativa":            f"{float(row.get('similitud_narrativa', 0) or 0):.1%}",
                "Proveedor lista restrictiva":    str(bool(row.get("proveedor_lista_restrictiva", False))),
            }
            for k, v in data_kv.items():
                st.markdown(f"- **{k}:** {v}")

        with tab3:
            doc_fields = {
                "doc_factura_alterada":    "Factura con posibles alteraciones",
                "doc_ruc_invalido":        "RUC con posibles inconsistencias",
                "doc_parte_tardio":        "Parte policial tardío",
                "doc_sin_denuncia_previa": "Sin denuncia previa",
                "doc_sin_testigos":        "Sin testigos",
                "doc_robo":                "Tipo: robo",
                "doc_perdida_total":       "Pérdida total declarada",
            }
            found_any = False
            for col, label in doc_fields.items():
                val = row.get(col, False)
                if val and str(val) not in ("0", "False", "nan", ""):
                    st.warning(f"⚠️ {label}")
                    found_any = True
            if not found_any:
                st.success("No se detectaron señales documentales de riesgo.")

            st.markdown("---")
            st.markdown(f"**Documentos aportados:** {int(row.get('cantidad_documentos', 0) or 0)}")
            st.markdown(f"**Score documental:** {float(row.get('score_documental', 0) or 0):.0f}/100")

        with tab4:
            agent_info = get_agent_status()
            if agent_info["api_available"]:
                st.success("🤖 Agente IA activo con Claude API")
            else:
                st.info("⚙️ Modo fallback — configure ANTHROPIC_API_KEY para análisis con IA")
            st.caption("*Este análisis es orientativo. Las decisiones finales corresponden al equipo humano.*")

            if st.button("Generar análisis IA", type="primary", key="btn_analyze"):
                with st.spinner("Consultando agente IA..."):
                    from src.models.predict_model import _artifacts
                    shap_exp = get_shap_explanation(selected_sin, df, _artifacts)
                    result   = analyze_claim(selected_sin, df, shap_explanation=shap_exp)
                st.markdown(result["analysis"])
                mode_txt = "🤖 Claude API" if result["mode"] == "api" else "⚙️ Modo fallback"
                st.caption(f"Generado con: {mode_txt}")


# ── 4. RED DE RELACIONES ─────────────────────────────────────────────────────
elif page == "network":
    st.title("🕸️ Red de relaciones")
    st.caption("Grafo asegurado ↔ siniestro ↔ proveedor")

    edges_df = load_network_edges()

    if edges_df.empty:
        st.warning("Grafo de red no disponible. Ejecuta `python -m src.network.relationship_graph`.")
    else:
        n_asegurados  = df["id_asegurado"].nunique()  if "id_asegurado"  in df.columns else 0
        n_proveedores = df["id_proveedor"].nunique()  if "id_proveedor"  in df.columns else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Siniestros",  len(df))
        with c2: st.metric("Asegurados",  n_asegurados)
        with c3: st.metric("Proveedores", n_proveedores)
        with c4: st.metric("Conexiones",  len(edges_df))

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Conexiones por tipo de relación")
            if "tipo_relacion" in edges_df.columns:
                tipo_counts = edges_df["tipo_relacion"].value_counts().reset_index()
                tipo_counts.columns = ["Tipo", "Conexiones"]
                fig = px.bar(tipo_counts, x="Tipo", y="Conexiones",
                             color_discrete_sequence=["#1e3a5f"])
                fig.update_layout(margin=dict(t=20, b=0), height=280)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("Distribución de peso de conexiones")
            if "weight" in edges_df.columns:
                fig2 = px.histogram(edges_df, x="weight", nbins=20,
                                    color_discrete_sequence=["#1e3a5f"],
                                    labels={"weight": "Peso de conexión"})
                fig2.update_layout(margin=dict(t=20, b=0), height=280)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Alertas de red en siniestros")
        net_cols = [c for c in ["net_proveedor_alto_riesgo", "net_asegurado_recurrente",
                                "net_par_concentrado", "net_score"] if c in df.columns]
        if net_cols:
            st.dataframe(
                df[["id_siniestro", "nivel_riesgo"] + net_cols]
                .sort_values("net_score", ascending=False).head(20)
                .rename(columns={"id_siniestro": "Siniestro", "nivel_riesgo": "Nivel",
                                 "net_score": "Score red"}),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Ejecuta el módulo de red para ver métricas de red por siniestro.")

        with st.expander("Ver tabla de aristas (muestra)"):
            st.dataframe(edges_df.head(50), use_container_width=True, hide_index=True)


# ── 5. ANÁLISIS NLP ──────────────────────────────────────────────────────────
elif page == "nlp":
    st.title("🔤 Análisis NLP — Similitud de narrativas")
    st.caption("Detección de narrativas clonadas y patrones textuales sospechosos")

    nlp_cols = [c for c in df.columns if c.startswith("nlp_")]
    if not nlp_cols:
        st.warning("Columnas NLP no disponibles. Ejecuta `python -m src.nlp.narrative_similarity`.")
        st.stop()

    n_comun  = int(df["nlp_descripcion_comun"].sum()) if "nlp_descripcion_comun" in df.columns else 0
    n_clon   = int(df.get("narrativa_clonada", pd.Series([False]*len(df))).sum())
    n_grupos = int(df["nlp_grupo_id"].nunique()) if "nlp_grupo_id" in df.columns else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Descripciones comunes (≥10)", n_comun)
    with c2: st.metric("Narrativas clonadas (sim ≥ 0.85)", n_clon)
    with c3: st.metric("Grupos únicos", n_grupos)

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Score NLP por grupo")
        if "nlp_grupo_id" in df.columns and "nlp_score" in df.columns:
            grupo_stats = (
                df.groupby("nlp_grupo_id")["nlp_score"]
                .agg(["mean", "count"]).reset_index()
                .rename(columns={"nlp_grupo_id": "Grupo", "mean": "Score medio", "count": "N"})
                .sort_values("Score medio", ascending=False).head(15)
            )
            fig = px.bar(grupo_stats, x="Grupo", y="Score medio",
                         color="Score medio",
                         color_continuous_scale=["#16a34a", "#d97706", "#dc2626"],
                         text="N", labels={"Score medio": "Score NLP medio"})
            fig.update_coloraxes(showscale=False)
            fig.update_layout(margin=dict(t=20, b=0), height=320)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Frecuencia de descripciones")
        if "nlp_freq_descripcion" in df.columns:
            freq_vals = df["nlp_freq_descripcion"].value_counts().sort_index()
            fig2 = px.bar(x=freq_vals.index, y=freq_vals.values,
                          labels={"x": "Frecuencia", "y": "Número de siniestros"},
                          color_discrete_sequence=["#1e3a5f"])
            fig2.update_layout(margin=dict(t=20, b=0), height=320)
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Siniestros con narrativa muy frecuente (posibles señales de copia)")
    if "nlp_freq_descripcion" in df.columns:
        high_freq = df[df["nlp_freq_descripcion"] >= 10].sort_values(
            "nlp_freq_descripcion", ascending=False)
        if len(high_freq) > 0:
            show_cols = [c for c in ["id_siniestro", "nivel_riesgo", "nlp_freq_descripcion",
                                     "nlp_score", "similitud_narrativa"] if c in high_freq.columns]
            st.dataframe(
                high_freq[show_cols].head(20).rename(columns={
                    "id_siniestro": "Siniestro", "nivel_riesgo": "Nivel",
                    "nlp_freq_descripcion": "Frecuencia", "nlp_score": "Score NLP",
                    "similitud_narrativa": "Sim. Excel",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No hay grupos con frecuencia ≥ 10.")


# ── 6. MODELO ML ─────────────────────────────────────────────────────────────
elif page == "model":
    st.title("🤖 Modelo ML — RandomForest + IsolationForest")

    info = get_model_info(_load_artifacts_cached())

    if not info.get("disponible"):
        st.warning(info.get("mensaje", "Modelo no disponible."))
        st.info(f"Instrucciones: `{info.get('instrucciones', 'notebooks/entrenamiento_colab.ipynb')}`")
    else:
        metricas = info.get("metricas", {})

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("F1 Score",   f"{metricas.get('f1', 0):.3f}")
        with m2: st.metric("AUC-ROC",    f"{metricas.get('auc_roc', 0):.3f}")
        with m3: st.metric("Precision",  f"{metricas.get('precision', 0):.3f}")
        with m4: st.metric("CV F1 mean", f"{metricas.get('cv_f1_mean', 0):.3f}")

        st.caption(
            f"Entrenado con {metricas.get('n_train', '?')} siniestros | "
            f"Evaluado en {metricas.get('n_test', '?')} | "
            f"{info.get('n_features', '?')} features"
        )

        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("Importancia SHAP de features")
            top_features = info.get("top_features", [])
            if top_features:
                feat_df = pd.DataFrame(top_features, columns=["Feature", "SHAP"])
                feat_df = feat_df.sort_values("SHAP")
                fig = px.bar(feat_df, x="SHAP", y="Feature", orientation="h",
                             color="SHAP",
                             color_continuous_scale=["#16a34a", "#d97706", "#dc2626"],
                             labels={"SHAP": "Importancia media |SHAP|"})
                fig.update_coloraxes(showscale=False)
                fig.update_layout(margin=dict(t=20, b=0, l=0), height=420)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("Score ML vs Score reglas")
            if "score_modelo" in df.columns and "score_reglas" in df.columns:
                fig2 = px.scatter(
                    df, x="score_reglas", y="score_modelo",
                    color="nivel_riesgo",
                    color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
                    labels={"score_reglas": "Score reglas", "score_modelo": "Score ML"},
                    opacity=0.6, hover_data=["id_siniestro"],
                )
                fig2.update_layout(margin=dict(t=20, b=0), height=380)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Distribución de scores ML")
        ml_cols = [c for c in ["model_rf_score", "model_isof_score",
                               "score_random_forest", "score_isolation_forest"] if c in df.columns]
        if ml_cols:
            fig3 = go.Figure()
            colors = ["#1e3a5f", "#d97706"]
            for col, clr in zip(ml_cols[:2], colors):
                fig3.add_trace(go.Histogram(x=df[col], name=col, opacity=0.7,
                                            marker_color=clr, nbinsx=25))
            fig3.update_layout(barmode="overlay", margin=dict(t=20, b=0),
                               height=260, legend=dict(x=0.7, y=1))
            st.plotly_chart(fig3, use_container_width=True)


# ── 7. AGENTE IA ─────────────────────────────────────────────────────────────
elif page == "agent":
    st.title("💬 Agente IA — Análisis conversacional")
    st.caption("Consulta sobre siniestros en lenguaje natural")

    agent_info = get_agent_status()
    if agent_info["api_available"]:
        st.success(f"🤖 {agent_info['mode']}")
    else:
        st.info(f"⚙️ {agent_info['message']}")

    st.markdown(
        "> ⚖️ **Aviso ético:** Este agente identifica posibles señales de riesgo para revisión "
        "humana. No emite juicios definitivos ni rechaza siniestros automáticamente."
    )
    st.divider()

    tab_chat, tab_individual = st.tabs(["💬 Chat libre", "📋 Análisis de siniestro"])

    with tab_chat:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Pregunta sobre el portafolio de siniestros..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analizando..."):
                    result = answer_question(prompt, df)
                st.markdown(result["answer"])
                if result["mode"] == "fallback":
                    st.caption("⚙️ Modo fallback — configure ANTHROPIC_API_KEY para respuestas más ricas")
            st.session_state.chat_history.append(
                {"role": "assistant", "content": result["answer"]}
            )

        if st.session_state.chat_history and st.button("Limpiar historial"):
            st.session_state.chat_history = []
            st.rerun()

    with tab_individual:
        sin_options = (df.sort_values("score_riesgo", ascending=False)["id_siniestro"].tolist()
                       if "score_riesgo" in df.columns else df["id_siniestro"].tolist())
        selected = st.selectbox("Selecciona siniestro para analizar", sin_options, key="agent_sin")

        if st.button("Analizar siniestro con IA", type="primary"):
            with st.spinner(f"Analizando {selected}..."):
                from src.models.predict_model import _artifacts
                shap_exp = get_shap_explanation(selected, df, _artifacts)
                result   = analyze_claim(selected, df, shap_explanation=shap_exp)

            row = df[df["id_siniestro"] == selected].iloc[0]
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(result["analysis"])
            with col_b:
                st.markdown(risk_badge(result["nivel_riesgo"]), unsafe_allow_html=True)
                st.metric("Score", f"{result['score_riesgo']:.0f}/100")

            mode_txt = "🤖 Claude API" if result["mode"] == "api" else "⚙️ Modo fallback"
            st.caption(f"Generado con: {mode_txt}")

            if shap_exp:
                st.markdown("**Top features (SHAP):**")
                for item in shap_exp[:5]:
                    dire = "⬆️" if item.get("direction") == "aumenta riesgo" else "⬇️"
                    st.markdown(f"- {dire} `{item['feature']}`: {item['shap_value']:+.4f}")


# ── 8. CARGAR SINIESTROS (CU01) ───────────────────────────────────────────────
elif page == "upload":
    st.title("📥 Cargar Siniestros")
    st.caption("CU01 — El sistema valida la estructura y puntúa los casos nuevos")

    # ── Columnas requeridas según sección 6.1 del reto ──────────────────────
    REQUIRED_COLS = [
        "id_siniestro", "ramo", "monto_reclamado", "monto_estimado",
        "dias_desde_inicio_poliza", "dias_hasta_fin_poliza",
        "dias_ocurrencia_reporte", "historial_siniestros_asegurado",
    ]
    OPTIONAL_COLS = [
        "id_poliza", "id_asegurado", "id_proveedor", "cobertura",
        "fecha_ocurrencia", "fecha_reporte", "estado", "descripcion",
        "monto_pagado", "similitud_narrativa", "ratio_monto_suma",
        "proveedor_lista_restrictiva", "doc_factura_alterada",
        "doc_ruc_invalido", "narrativa_clonada", "narrativa_similar",
        "reporte_tardio", "alerta_borde_inicio", "alerta_borde_fin",
        "cantidad_documentos", "n_reclamos_12_meses", "n_reclamos_historico",
        "reclamos_rc_sin_tercero", "antiguedad_anios",
        "n_siniestros_proveedor", "promedio_monto_proveedor",
        "doc_sin_denuncia_previa", "doc_sin_testigos",
        "doc_robo", "doc_perdida_total", "doc_parte_tardio",
    ]

    # ── Instrucciones + descarga de plantilla ───────────────────────────────
    with st.expander("📋 Instrucciones y plantilla", expanded=True):
        st.markdown(
            "Sube un archivo **CSV** con siniestros nuevos. "
            "El sistema validará la estructura, detectará señales de riesgo y "
            "asignará un score 0-100 a cada caso.\n\n"
            f"**Columnas obligatorias ({len(REQUIRED_COLS)}):** "
            f"`{'`, `'.join(REQUIRED_COLS)}`\n\n"
            "Las columnas opcionales enriquecen el análisis pero no son necesarias."
        )
        # Plantilla descargable
        template_df = pd.DataFrame(columns=REQUIRED_COLS + ["descripcion", "id_asegurado", "id_proveedor"])
        template_df.loc[0] = {
            "id_siniestro": "SIN-0001", "ramo": "Vehículos",
            "monto_reclamado": 5000.0, "monto_estimado": 4500.0,
            "dias_desde_inicio_poliza": 45, "dias_hasta_fin_poliza": 320,
            "dias_ocurrencia_reporte": 2, "historial_siniestros_asegurado": 0,
            "descripcion": "Choque lateral en intersección con semáforo en verde.",
            "id_asegurado": "ASEG-0001", "id_proveedor": "TALLER-001",
        }
        st.download_button(
            "⬇️ Descargar plantilla CSV",
            data=template_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="plantilla_siniestros.csv",
            mime="text/csv",
        )

    # ── Upload ───────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Selecciona un archivo CSV de siniestros",
        type=["csv"],
        help="Máximo 200 MB. Debe incluir las columnas obligatorias.",
    )

    if uploaded is None:
        st.info("⬆️ Sube un CSV para comenzar el análisis. Puedes usar la plantilla de arriba.")
        st.stop()

    # ── Leer archivo ─────────────────────────────────────────────────────────
    try:
        raw_df = pd.read_csv(uploaded, encoding="utf-8-sig", low_memory=False)
    except Exception:
        try:
            uploaded.seek(0)
            raw_df = pd.read_csv(uploaded, encoding="latin-1", low_memory=False)
        except Exception as e:
            st.error(f"❌ No se pudo leer el archivo: {e}")
            st.stop()

    st.success(f"✅ Archivo cargado: **{uploaded.name}** — {len(raw_df)} filas, {raw_df.shape[1]} columnas")

    # ── VALIDACIÓN DE ESTRUCTURA ──────────────────────────────────────────────
    st.subheader("🔍 Validación de estructura")

    cols_present  = [c for c in REQUIRED_COLS if c in raw_df.columns]
    cols_missing  = [c for c in REQUIRED_COLS if c not in raw_df.columns]
    cols_optional = [c for c in OPTIONAL_COLS if c in raw_df.columns]

    v1, v2, v3 = st.columns(3)
    with v1:
        st.metric("Columnas obligatorias encontradas",
                  f"{len(cols_present)}/{len(REQUIRED_COLS)}",
                  delta=None if cols_missing else "✓ Completo")
    with v2:
        st.metric("Columnas opcionales presentes", len(cols_optional))
    with v3:
        st.metric("Filas a procesar", len(raw_df))

    if cols_missing:
        st.error(f"❌ Faltan columnas obligatorias: `{'`, `'.join(cols_missing)}`")
        st.markdown(
            "El sistema puede continuar con scoring parcial usando solo las columnas disponibles, "
            "pero la precisión será menor."
        )
        if not st.checkbox("Continuar de todas formas con scoring parcial"):
            st.stop()
    else:
        st.success("✅ Estructura válida — todas las columnas obligatorias presentes")

    # Validaciones de datos
    issues = []
    if "monto_reclamado" in raw_df.columns and (pd.to_numeric(raw_df["monto_reclamado"], errors="coerce") < 0).any():
        issues.append("⚠️ `monto_reclamado` tiene valores negativos")
    if "dias_desde_inicio_poliza" in raw_df.columns and (pd.to_numeric(raw_df["dias_desde_inicio_poliza"], errors="coerce") < 0).any():
        issues.append("⚠️ `dias_desde_inicio_poliza` tiene valores negativos")
    if raw_df.get("id_siniestro", pd.Series(dtype=str)).duplicated().any():
        issues.append("⚠️ Existen `id_siniestro` duplicados en el archivo")
    nulls_pct = raw_df[cols_present].isnull().mean().mean() * 100
    if nulls_pct > 20:
        issues.append(f"⚠️ Alta proporción de nulos en columnas clave ({nulls_pct:.1f}%)")

    if issues:
        for iss in issues:
            st.warning(iss)
    else:
        st.success("✅ Datos válidos — sin anomalías estructurales detectadas")

    # ── PREVIEW ───────────────────────────────────────────────────────────────
    with st.expander("👁️ Vista previa de los datos cargados"):
        st.dataframe(raw_df.head(10), use_container_width=True)
        st.caption(f"Mostrando 10 de {len(raw_df)} filas")

    # ── SCORING ───────────────────────────────────────────────────────────────
    st.subheader("⚡ Calcular score de riesgo")
    st.markdown(
        "El motor aplica las **24 reglas antifraude** y el **modelo ML** "
        "a cada siniestro del archivo."
    )

    if st.button("🚀 Procesar y puntuar siniestros", type="primary"):
        with st.spinner("Procesando siniestros..."):

            from src.rules.fraud_rules import apply_rules_df
            from src.scoring.risk_score import compute_scores

            work_df = raw_df.copy()

            # Derivar ratio_monto_suma si no existe
            if "ratio_monto_suma" not in work_df.columns:
                if "monto_reclamado" in work_df.columns and "monto_estimado" in work_df.columns:
                    denom = pd.to_numeric(work_df["monto_estimado"], errors="coerce").replace(0, np.nan)
                    work_df["ratio_monto_suma"] = (
                        pd.to_numeric(work_df["monto_reclamado"], errors="coerce") / denom
                    ).clip(0, 5)

            # Derivar alertas de borde si no existen
            if "alerta_borde_inicio" not in work_df.columns and "dias_desde_inicio_poliza" in work_df.columns:
                d = pd.to_numeric(work_df["dias_desde_inicio_poliza"], errors="coerce").fillna(999)
                work_df["alerta_borde_inicio"] = d <= 30
            if "alerta_borde_fin" not in work_df.columns and "dias_hasta_fin_poliza" in work_df.columns:
                d = pd.to_numeric(work_df["dias_hasta_fin_poliza"], errors="coerce").fillna(999)
                work_df["alerta_borde_fin"] = d <= 30
            if "reporte_tardio" not in work_df.columns and "dias_ocurrencia_reporte" in work_df.columns:
                d = pd.to_numeric(work_df["dias_ocurrencia_reporte"], errors="coerce").fillna(0)
                work_df["reporte_tardio"] = d > 7

            # Aplicar scoring completo
            try:
                scored_new = compute_scores(work_df)
            except Exception as e:
                st.error(f"Error en scoring: {e}")
                st.stop()

            # Aplicar modelo ML si está disponible
            arts = _load_artifacts_cached()
            if arts.available:
                from src.models.predict_model import predict_scores
                scored_new = predict_scores(scored_new, arts)

        # ── Resultados ────────────────────────────────────────────────────────
        st.success(f"✅ Procesados {len(scored_new)} siniestros")

        # KPIs
        nivel_counts = scored_new["nivel_riesgo"].value_counts() if "nivel_riesgo" in scored_new.columns else pd.Series(dtype=int)
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Total", len(scored_new))
        with k2:
            st.metric("🟢 Bajo",  int(nivel_counts.get("BAJO",  0)))
        with k3:
            st.metric("🟡 Medio", int(nivel_counts.get("MEDIO", 0)))
        with k4:
            st.metric("🔴 Alto",  int(nivel_counts.get("ALTO",  0)),
                      delta="⚠️ Requieren revisión" if nivel_counts.get("ALTO", 0) > 0 else None,
                      delta_color="inverse")

        # Tabla de resultados
        display_cols = (
            ["id_siniestro", "nivel_riesgo", "score_riesgo", "score_reglas",
             "recomendacion", "alertas_activas"]
        )
        display_cols = [c for c in display_cols if c in scored_new.columns]
        result_df = scored_new.sort_values("score_riesgo", ascending=False)[display_cols]

        # Colorear por nivel
        def color_nivel(val):
            colors = {"ALTO": "background-color:#fee2e2",
                      "MEDIO": "background-color:#fef9c3",
                      "BAJO": "background-color:#dcfce7"}
            return colors.get(val, "")

        if "nivel_riesgo" in result_df.columns:
            st.dataframe(
                result_df.style.applymap(color_nivel, subset=["nivel_riesgo"]),
                use_container_width=True, height=400,
            )
        else:
            st.dataframe(result_df, use_container_width=True, height=400)

        # Gráfico de distribución
        if "score_riesgo" in scored_new.columns:
            fig_up = px.histogram(
                scored_new, x="score_riesgo",
                color="nivel_riesgo" if "nivel_riesgo" in scored_new.columns else None,
                color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
                nbins=20, title="Distribución de scores — archivo cargado",
                labels={"score_riesgo": "Score de riesgo (0-100)"},
            )
            fig_up.add_vline(x=40, line_dash="dash", line_color="gray", annotation_text="Bajo/Medio")
            fig_up.add_vline(x=75, line_dash="dash", line_color="gray", annotation_text="Medio/Alto")
            fig_up.update_layout(margin=dict(t=40, b=0), height=300)
            st.plotly_chart(fig_up, use_container_width=True)

        # Exportar
        csv_out = scored_new.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Descargar resultados con scores",
            data=csv_out,
            file_name=f"scored_{uploaded.name}",
            mime="text/csv",
        )

        st.caption(
            "⚖️ Los scores son alertas para revisión humana. "
            "No constituyen acusaciones ni rechazan automáticamente ningún siniestro."
        )
