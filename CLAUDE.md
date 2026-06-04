# FraudIA Claims — Contexto del proyecto

## Descripción
Sistema antifraude de siniestros para la Aseguradora del Sur. Hackathon 2026.
Detecta posibles señales de fraude, asigna score 0-100 y permite consultas en lenguaje natural.

## Estado actual
- **Producción:** Streamlit Community Cloud (deployado, auto-despliega en push a main)
- **Repo:** https://github.com/OppaDev/hackiathon-aseguradora-del-sur
- **Tests:** 258/258 pasando
- **Python:** 3.12 (Anaconda en C:\ProgramData\anaconda3\python.exe)

## Cómo ejecutar localmente
```bash
streamlit run src/app/app.py
# Puerto 8501 por defecto
```

## Score de riesgo — fórmula definitiva
```
score_final = 40% × score_reglas + 25% × score_documental
            + 20% × score_modelo  + 15% × score_nlp
```

| Nivel | Rango  | Acción |
|-------|--------|--------|
| BAJO  | 0–40   | Flujo normal |
| MEDIO | 41–75  | Escalar a Unidad Antifraude |
| ALTO  | 76–100 | Detener pago, revisión de campo |

Estos umbrales están alineados en: `risk_score.py`, `README.md`, `docs/uso_ia.md`, tests.

## Dashboard — 8 páginas
1. Resumen ejecutivo
2. Explorador de siniestros
3. Detalle de siniestro
4. Red de relaciones
5. Análisis NLP
6. Modelo ML
7. Agente IA
8. Cargar Siniestros (CU01)

## Distribución actual del portafolio (500 siniestros)
- ALTO: 1 (0.2%)
- MEDIO: 42 (8.4%)
- BAJO: 457 (91.4%)

## Archivos clave
| Archivo | Descripción |
|---|---|
| `src/app/app.py` | Dashboard Streamlit (8 páginas) |
| `src/scoring/risk_score.py` | Motor de score, _classify() con umbrales 40/75 |
| `src/rules/fraud_rules.py` | 24 reglas antifraude |
| `src/ai_agent/claims_agent.py` | Agente Claude API + fallback determinístico |
| `src/models/predict_model.py` | RF + IsolationForest |
| `data/processed/claims_with_documents.csv` | Dataset principal (500 filas, 89 cols) |
| `data/processed/claims_scored.csv` | Dataset con scores calculados |
| `data/processed/sample_upload_demo.csv` | CSV demo (6 siniestros: 1 ALTO, 3 MEDIO, 2 BAJO) |
| `data/processed/fire_drill_24h.csv` | CSV prueba de fuego: siniestro 1 día tras inicio póliza → 91/100 ALTO |
| `models/fraud_model.pkl` | RandomForest entrenado (Precision 1.000, CV F1 0.951) |

## API key
- Local: `.env` con `ANTHROPIC_API_KEY=sk-ant-...`
- Producción: `st.secrets["ANTHROPIC_API_KEY"]` en Streamlit Cloud
- Modelo: `claude-haiku-4-5-20251001`
- El agente tiene fallback determinístico si no hay API key

## Contexto del agente IA
`_build_portfolio_context()` en `claims_agent.py` genera 9 secciones:
- Top 10 por score, casos ALTO/MEDIO
- Proveedores con alertas (tabla agregada)
- Ciudades con concentración de alertas
- Asegurados frecuentes
- Señales documentales en críticos
- Montos atípicos (ratio >= 90%)
- Casos borde de póliza (<=30 días)
- Patrones repetidos

Para datasets <= 150 filas (CSV subido): incluye todas las filas con detalle completo.

## Inconsistencias ya resueltas
- Umbrales score: corregidos en risk_score.py, tests, docs/uso_ia.md (era 0-30/31-65/66-100)
- Página Modelo ML: usa _load_artifacts_cached() (no el singleton de módulo)
- compute_scores: fix fillna cuando columnas opcionales no existen en CSV subido

## Pendientes para entrega
- [ ] Exportar pitch_fraudia_claims.pptx → pitch.pdf y hacer push
- [ ] Confirmar URL de Streamlit Cloud para incluir en el correo de entrega
- [ ] Enviar correo de entrega con GitHub + URL app + PDF adjunto

## Comandos útiles
```bash
# Tests
python -m pytest tests/ -q

# Solo risk_score
python -m pytest tests/test_risk_score.py -v

# Regenerar scores
python src/scoring/risk_score.py
```
