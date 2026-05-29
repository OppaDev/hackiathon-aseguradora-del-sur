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

from src.app.data_loader import load_main_dataframe, load_network_edges, get_data_status
from src.app.components.risk_badge import risk_badge, score_gauge_html, metric_card, agent_mode_pill
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
    st.image("https://img.shields.io/badge/FraudIA-Claims-1e3a5f?style=for-the-badge", use_column_width=True)
    st.markdown("## 🛡️ FraudIA Claims")
    st.markdown("*Sistema de detección de señales de riesgo en siniestros*")
    st.divider()

    PAGES = {
        "📊 Resumen ejecutivo":   "overview",
        "🔍 Explorador de siniestros": "explorer",
        "📋 Detalle de siniestro": "detail",
        "🕸️ Red de relaciones":    "network",
        "🔤 Análisis NLP":         "nlp",
        "🤖 Modelo ML":            "model",
        "💬 Agente IA":            "agent",
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
    agent_mode_pill(status["agent"]["mode"])

# ---------------------------------------------------------------------------
# Carga de datos (cacheada)
# ---------------------------------------------------------------------------

with st.spinner("Cargando datos..."):
    try:
        df = load_main_dataframe()
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

# ── 1. RESUMEN EJECUTIVO ────────────────────────────────────────────────────
if page == "overview":
    st.title("📊 Resumen Ejecutivo")
    st.caption("Vista general del portafolio de siniestros analizados")

    dist = df["nivel_riesgo"].value_counts() if "nivel_riesgo" in df.columns else {}
    alto  = int(dist.get("ALTO",  0))
    medio = int(dist.get("MEDIO", 0))
    bajo  = int(dist.get("BAJO",  0))
    total = len(df)

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Total siniestros", str(total), color="#1e3a5f")
    with c2: metric_card("🔴 ALTO riesgo",   f"{alto} ({alto/total:.1%})", color="#dc2626")
    with c3: metric_card("🟡 MEDIO riesgo",  f"{medio} ({medio/total:.1%})", color="#d97706")
    with c4: metric_card("🟢 BAJO riesgo",   f"{bajo} ({bajo/total:.1%})", color="#16a34a")

    st.divider()

    col_left, col_right = st.columns([1, 1])

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
            fig_hist.add_vline(x=30, line_dash="dash", line_color="#16a34a", annotation_text="BAJO/MEDIO")
            fig_hist.add_vline(x=65, line_dash="dash", line_color="#dc2626", annotation_text="MEDIO/ALTO")
            fig_hist.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()
    st.subheader("Top 10 siniestros por score de riesgo")
    if "score_riesgo" in df.columns:
        top10 = df.nlargest(10, "score_riesgo")[
            ["id_siniestro", "score_riesgo", "nivel_riesgo",
             "tipo_siniestro", "monto_reclamado", "rule_n_rules_fired"]
        ].copy()
        top10["nivel_riesgo_badge"] = top10["nivel_riesgo"].apply(risk_badge)
        top10["score_riesgo"] = top10["score_riesgo"].round(1)
        top10 = top10.rename(columns={
            "id_siniestro": "Siniestro",
            "score_riesgo": "Score",
            "nivel_riesgo": "Nivel",
            "tipo_siniestro": "Tipo",
            "monto_reclamado": "Monto ($)",
            "rule_n_rules_fired": "Reglas",
        })
        st.dataframe(top10[["Siniestro", "Score", "Nivel", "Tipo", "Monto ($)", "Reglas"]],
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💬 Análisis ejecutivo con IA")
    if st.button("Generar resumen ejecutivo con IA", type="primary"):
        with st.spinner("Consultando agente IA..."):
            result = generate_executive_summary(df)
        st.markdown(result["summary"])
        if result["mode"] == "fallback":
            st.caption("⚙️ Análisis generado en modo fallback (sin Claude API)")
        else:
            st.caption("🤖 Análisis generado con Claude API")


# ── 2. EXPLORADOR DE SINIESTROS ─────────────────────────────────────────────
elif page == "explorer":
    st.title("🔍 Explorador de siniestros")
    st.caption("Filtra y ordena el portafolio completo")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        nivel_filter = st.multiselect(
            "Nivel de riesgo",
            ["ALTO", "MEDIO", "BAJO"],
            default=["ALTO", "MEDIO", "BAJO"],
        )
    with col_f2:
        tipos = sorted(df["tipo_siniestro"].dropna().unique().tolist()) if "tipo_siniestro" in df.columns else []
        tipo_filter = st.multiselect("Tipo de siniestro", tipos, default=tipos)
    with col_f3:
        score_range = st.slider("Rango de score", 0, 100, (0, 100))
    with col_f4:
        solo_reglas = st.checkbox("Solo con reglas disparadas", value=False)

    mask = (
        df["nivel_riesgo"].isin(nivel_filter) &
        (df["score_riesgo"] >= score_range[0]) &
        (df["score_riesgo"] <= score_range[1])
    )
    if tipo_filter and "tipo_siniestro" in df.columns:
        mask &= df["tipo_siniestro"].isin(tipo_filter)
    if solo_reglas and "rule_n_rules_fired" in df.columns:
        mask &= df["rule_n_rules_fired"] > 0

    df_filt = df[mask].copy()
    st.caption(f"Mostrando {len(df_filt)} de {len(df)} siniestros")

    display_cols = ["id_siniestro", "score_riesgo", "nivel_riesgo", "tipo_siniestro",
                    "monto_reclamado", "rule_n_rules_fired", "rule_n_critical"]
    display_cols = [c for c in display_cols if c in df_filt.columns]

    df_show = df_filt[display_cols].sort_values("score_riesgo", ascending=False).copy()
    df_show["score_riesgo"] = df_show["score_riesgo"].round(1)

    st.dataframe(
        df_show.rename(columns={
            "id_siniestro": "Siniestro", "score_riesgo": "Score",
            "nivel_riesgo": "Nivel", "tipo_siniestro": "Tipo",
            "monto_reclamado": "Monto ($)", "rule_n_rules_fired": "Reglas",
            "rule_n_critical": "Críticas",
        }),
        use_container_width=True, hide_index=True, height=500,
    )

    if "score_riesgo" in df_filt.columns and len(df_filt) > 0:
        st.subheader("Score por tipo de siniestro")
        fig = px.box(
            df_filt, x="tipo_siniestro", y="score_riesgo",
            color="nivel_riesgo",
            color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
            labels={"score_riesgo": "Score de riesgo", "tipo_siniestro": "Tipo"},
        )
        fig.update_layout(margin=dict(t=20, b=0), height=350)
        st.plotly_chart(fig, use_container_width=True)


# ── 3. DETALLE DE SINIESTRO ──────────────────────────────────────────────────
elif page == "detail":
    st.title("📋 Detalle de siniestro")

    sin_options = df["id_siniestro"].tolist() if "id_siniestro" in df.columns else []
    if "score_riesgo" in df.columns:
        sin_options = df.sort_values("score_riesgo", ascending=False)["id_siniestro"].tolist()

    selected_sin = st.selectbox("Selecciona un siniestro", sin_options)

    if selected_sin:
        row = df[df["id_siniestro"] == selected_sin].iloc[0]
        nivel = row.get("nivel_riesgo", "BAJO")
        score = float(row.get("score_riesgo", 0) or 0)

        col_head, col_badge = st.columns([3, 1])
        with col_head:
            st.subheader(f"Siniestro {selected_sin}")
            st.markdown(f"**Tipo:** {row.get('tipo_siniestro', 'N/D')} | "
                        f"**Asegurado:** {row.get('id_asegurado', 'N/D')} | "
                        f"**Proveedor:** {row.get('id_proveedor', 'N/D')}")
        with col_badge:
            st.markdown(risk_badge(nivel), unsafe_allow_html=True)
            st.markdown(f"**Score: {score:.0f}/100**")

        st.divider()
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Scores", "⚠️ Alertas", "📄 Documentos", "🤖 Análisis IA"])

        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            with c1: metric_card("Score final", f"{score:.0f}", color={"ALTO":"#dc2626","MEDIO":"#d97706","BAJO":"#16a34a"}.get(nivel,"#6b7280"))
            with c2: metric_card("Score reglas",     f"{float(row.get('score_reglas', 0) or 0):.0f}")
            with c3: metric_card("Score documental", f"{float(row.get('score_documental', 0) or 0):.0f}")
            with c4: metric_card("Score ML",         f"{float(row.get('score_modelo', 0) or 0):.0f}")

            st.markdown(score_gauge_html(score, nivel), unsafe_allow_html=True)

            st.markdown("**Recomendación:**")
            st.info(str(row.get("recomendacion", "Sin recomendación disponible") or ""))

            # Sub-scores desglose
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
            fig_bar.update_layout(margin=dict(t=20, b=0), height=280, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            alerts = str(row.get("rule_alerts", "") or "")
            explanations = str(row.get("rule_explanations", "") or "")
            n_fired  = int(row.get("rule_n_rules_fired", 0) or 0)
            n_crit   = int(row.get("rule_n_critical", 0) or 0)

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
            st.markdown("**Datos clave del siniestro:**")
            data_cols = {
                "Monto reclamado": f"${float(row.get('monto_reclamado', 0) or 0):,.2f}",
                "Monto estimado":  f"${float(row.get('monto_estimado', 0) or 0):,.2f}",
                "Días inicio póliza → siniestro": str(row.get("dias_desde_inicio_poliza", "N/D")),
                "Días ocurrencia → reporte":      str(row.get("dias_ocurrencia_reporte", "N/D")),
                "Historial siniestros":            str(row.get("historial_siniestros_asegurado", 0)),
                "Similitud narrativa":             f"{float(row.get('similitud_narrativa', 0) or 0):.1%}",
                "Proveedor en lista restrictiva":  str(bool(row.get("proveedor_lista_restrictiva", False))),
            }
            for k, v in data_cols.items():
                st.markdown(f"- **{k}:** {v}")

        with tab3:
            doc_fields = {
                "doc_factura_alterada":   "Factura con posibles alteraciones",
                "doc_ruc_invalido":       "RUC con posibles inconsistencias",
                "doc_parte_tardio":       "Parte policial tardío",
                "doc_sin_denuncia_previa":"Sin denuncia previa",
                "doc_sin_testigos":       "Sin testigos",
                "doc_robo":               "Tipo: robo",
                "doc_perdida_total":      "Pérdida total declarada",
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
            st.markdown(f"**Cantidad de documentos aportados:** {int(row.get('cantidad_documentos', 0) or 0)}")
            st.markdown(f"**Score documental:** {float(row.get('score_documental', 0) or 0):.0f}/100")

        with tab4:
            arts_status = get_agent_status()
            agent_mode_pill(arts_status["mode"])
            st.caption("*Este análisis es orientativo. Las decisiones finales corresponden al equipo humano.*")

            if st.button("Generar análisis IA", type="primary", key="btn_analyze"):
                with st.spinner("Consultando agente IA..."):
                    from src.models.predict_model import _artifacts, get_shap_explanation
                    shap_exp = get_shap_explanation(selected_sin, df, _artifacts)
                    result   = analyze_claim(selected_sin, df, shap_explanation=shap_exp)
                st.markdown(result["analysis"])
                if result["mode"] == "fallback":
                    st.caption("⚙️ Análisis en modo fallback (sin Claude API)")
                else:
                    st.caption("🤖 Análisis generado con Claude API")


# ── 4. RED DE RELACIONES ─────────────────────────────────────────────────────
elif page == "network":
    st.title("🕸️ Red de relaciones")
    st.caption("Grafo asegurado ↔ siniestro ↔ proveedor")

    edges_df = load_network_edges()

    if edges_df.empty:
        st.warning("Grafo de red no disponible. Ejecuta `python -m src.network.relationship_graph` para generarlo.")
    else:
        col_l, col_r = st.columns([2, 1])

        with col_l:
            # Estadísticas del grafo
            n_siniestros = len(df)
            n_asegurados = df["id_asegurado"].nunique() if "id_asegurado" in df.columns else 0
            n_proveedores = df["id_proveedor"].nunique() if "id_proveedor" in df.columns else 0
            n_edges = len(edges_df)

            m1, m2, m3, m4 = st.columns(4)
            with m1: metric_card("Siniestros", str(n_siniestros))
            with m2: metric_card("Asegurados", str(n_asegurados))
            with m3: metric_card("Proveedores", str(n_proveedores))
            with m4: metric_card("Conexiones", str(n_edges))

        st.subheader("Conexiones por tipo de relación")
        if "tipo_relacion" in edges_df.columns:
            tipo_counts = edges_df["tipo_relacion"].value_counts().reset_index()
            tipo_counts.columns = ["Tipo", "Conexiones"]
            fig = px.bar(tipo_counts, x="Tipo", y="Conexiones",
                         color_discrete_sequence=["#1e3a5f"])
            fig.update_layout(margin=dict(t=20, b=0), height=280)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Distribución de peso de conexiones")
        if "weight" in edges_df.columns:
            fig2 = px.histogram(edges_df, x="weight", nbins=20,
                                color_discrete_sequence=["#1e3a5f"],
                                labels={"weight": "Peso de conexión"})
            fig2.update_layout(margin=dict(t=20, b=0), height=250)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Alertas de red en siniestros")
        net_cols = [c for c in ["net_proveedor_alto_riesgo", "net_asegurado_recurrente",
                                "net_par_concentrado", "net_score"] if c in df.columns]
        if net_cols:
            st.dataframe(
                df[["id_siniestro", "nivel_riesgo"] + net_cols]
                .sort_values("net_score", ascending=False)
                .head(20)
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

    col1, col2, col3 = st.columns(3)
    with col1:
        n_comun = int(df["nlp_descripcion_comun"].sum()) if "nlp_descripcion_comun" in df.columns else 0
        metric_card("Descripciones comunes", str(n_comun), "≥10 ocurrencias", "#d97706")
    with col2:
        n_clon = int(df.get("narrativa_clonada", pd.Series([False]*len(df))).sum())
        metric_card("Narrativas clonadas", str(n_clon), "sim ≥ 0.85", "#dc2626")
    with col3:
        n_grupos = int(df["nlp_grupo_id"].nunique()) if "nlp_grupo_id" in df.columns else 0
        metric_card("Grupos únicos", str(n_grupos), "descripciones distintas")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Score NLP por grupo")
        if "nlp_grupo_id" in df.columns and "nlp_score" in df.columns:
            grupo_stats = (
                df.groupby("nlp_grupo_id")["nlp_score"]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"nlp_grupo_id": "Grupo", "mean": "Score medio", "count": "N"})
                .sort_values("Score medio", ascending=False)
                .head(15)
            )
            fig = px.bar(grupo_stats, x="Grupo", y="Score medio",
                         color="Score medio",
                         color_continuous_scale=["#16a34a", "#d97706", "#dc2626"],
                         text="N",
                         labels={"Score medio": "Score NLP medio"})
            fig.update_coloraxes(showscale=False)
            fig.update_layout(margin=dict(t=20, b=0), height=320)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Frecuencia de descripciones")
        if "nlp_freq_descripcion" in df.columns:
            freq_vals = df["nlp_freq_descripcion"].value_counts().sort_index()
            fig2 = px.bar(
                x=freq_vals.index, y=freq_vals.values,
                labels={"x": "Frecuencia", "y": "Número de siniestros"},
                color_discrete_sequence=["#1e3a5f"],
            )
            fig2.update_layout(margin=dict(t=20, b=0), height=320)
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Siniestros con narrativa más frecuente (posibles señales de copia)")
    if "nlp_freq_descripcion" in df.columns:
        high_freq = df[df["nlp_freq_descripcion"] >= 10].sort_values(
            "nlp_freq_descripcion", ascending=False
        )
        if len(high_freq) > 0:
            show_cols = ["id_siniestro", "nivel_riesgo", "nlp_freq_descripcion",
                         "nlp_score", "similitud_narrativa"]
            show_cols = [c for c in show_cols if c in high_freq.columns]
            st.dataframe(
                high_freq[show_cols].head(20)
                .rename(columns={
                    "id_siniestro": "Siniestro", "nivel_riesgo": "Nivel",
                    "nlp_freq_descripcion": "Freq", "nlp_score": "Score NLP",
                    "similitud_narrativa": "Sim. Excel",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No hay grupos con frecuencia ≥ 10.")


# ── 6. MODELO ML ─────────────────────────────────────────────────────────────
elif page == "model":
    st.title("🤖 Modelo ML — RandomForest + IsolationForest")

    from src.models.predict_model import _artifacts
    info = get_model_info(_artifacts)

    if not info.get("disponible"):
        st.warning(info.get("mensaje", "Modelo no disponible."))
        st.info(f"Instrucciones: `{info.get('instrucciones', 'notebooks/entrenamiento_colab.ipynb')}`")
    else:
        metricas = info.get("metricas", {})

        m1, m2, m3, m4 = st.columns(4)
        with m1: metric_card("F1 Score",    f"{metricas.get('f1', 0):.3f}")
        with m2: metric_card("AUC-ROC",     f"{metricas.get('auc_roc', 0):.3f}")
        with m3: metric_card("Precision",   f"{metricas.get('precision', 0):.3f}")
        with m4: metric_card("CV F1 mean",  f"{metricas.get('cv_f1_mean', 0):.3f}")

        st.caption(f"Entrenado con {metricas.get('n_train', '?')} siniestros | "
                   f"Evaluado en {metricas.get('n_test', '?')} | "
                   f"{info.get('n_features', '?')} features")

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
                fig.update_layout(margin=dict(t=20, b=0, l=0), height=400)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("Score ML vs Score reglas")
            if "score_modelo" in df.columns and "score_reglas" in df.columns:
                fig2 = px.scatter(
                    df, x="score_reglas", y="score_modelo",
                    color="nivel_riesgo",
                    color_discrete_map={"ALTO": "#dc2626", "MEDIO": "#d97706", "BAJO": "#16a34a"},
                    labels={"score_reglas": "Score reglas", "score_modelo": "Score ML"},
                    opacity=0.6,
                    hover_data=["id_siniestro"],
                )
                fig2.update_layout(margin=dict(t=20, b=0), height=380)
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Distribución de scores ML")
        ml_cols = [c for c in ["model_rf_score", "model_isof_score", "score_random_forest",
                               "score_isolation_forest"] if c in df.columns]
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

    agent_status = get_agent_status()
    agent_mode_pill(agent_status["mode"])

    st.markdown(
        "> ⚖️ **Aviso:** Este agente identifica posibles señales de riesgo para revisión humana. "
        "No emite juicios definitivos ni rechaza siniestros automáticamente."
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
                    st.caption("⚙️ Modo fallback — configure ANTHROPIC_API_KEY para respuestas más detalladas")

            st.session_state.chat_history.append(
                {"role": "assistant", "content": result["answer"]}
            )

        if st.button("Limpiar historial"):
            st.session_state.chat_history = []
            st.rerun()

    with tab_individual:
        sin_options = df.sort_values("score_riesgo", ascending=False)["id_siniestro"].tolist() \
                      if "score_riesgo" in df.columns else df["id_siniestro"].tolist()
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
                st.markdown(f"**Score: {result['score_riesgo']:.0f}/100**")

            if result["mode"] == "fallback":
                st.caption("⚙️ Análisis en modo fallback")
            else:
                st.caption("🤖 Análisis con Claude API")

            if shap_exp:
                st.markdown("**Top features (SHAP):**")
                for item in shap_exp[:5]:
                    dire = "⬆️" if item.get("direction") == "aumenta riesgo" else "⬇️"
                    st.markdown(f"- {dire} `{item['feature']}`: {item['shap_value']:+.4f}")
