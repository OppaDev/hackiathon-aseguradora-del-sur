# Arquitectura del Sistema — FraudIA Claims

## Arquitectura MVP

```
Excel (5 hojas)  +  26 PDFs
        |                |
   [Ingesta]      [Extracción PDF]
        |                |
  claims_master   documents_extracted
        \               /
         [Feature Engineering]
               |
    claims_with_documents
               |
    ┌──────────┼──────────┬──────────┐
[Reglas]  [Modelo IA]  [NLP]   [Redes]
    └──────────┼──────────┴──────────┘
               |
         Score 0-100
               |
     Verde / Amarillo / Rojo
               |
    ┌──────────┼──────────┐
[Dashboard] [Agente IA] [Reportes]
               |
        Streamlit Cloud
```

## Componentes

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Ingesta | `src/ingestion/load_excel.py` | Leer las 5 hojas del Excel, normalizar columnas, cruzar tablas |
| Extracción PDF | `src/pdf_extraction/` | Extraer campos de 26 PDFs con PyMuPDF y regex |
| Feature Engineering | `src/features/build_features.py` | Cruzar Excel + PDFs, generar variables derivadas |
| Motor de Reglas | `src/rules/fraud_rules.py` | 24 reglas antifraude con puntuación y explicación |
| Score | `src/scoring/risk_score.py` | Combinar reglas + documental + modelo + NLP en score 0-100 |
| Modelo IA | `src/models/predict_model.py` | Cargar Isolation Forest / Random Forest entrenado en Colab |
| NLP | `src/nlp/narrative_similarity.py` | TF-IDF + cosine similarity entre narrativas |
| Redes | `src/network/relationship_graph.py` | NetworkX: grafo asegurado–proveedor–siniestro |
| Explicabilidad | `src/explainability/explain_score.py` | Generar justificación textual del score |
| Agente IA | `src/ai_agent/claims_agent.py` | Claude API con RAG sobre datos procesados |
| Dashboard | `src/app/app.py` | Streamlit: 8 páginas interactivas |
| Carga CSV | `src/app/app.py` (página 8) | CU01: validación, scoring en tiempo real y chat IA sobre CSV subido |

## Arquitectura futura escalable

```
Sistemas Core de Siniestros
        |
    [ETL / Airflow]
        |
Oracle / PostgreSQL
        |
┌───────┼───────┐
[Reglas] [ML API] [NLP/RAG]
└───────┼───────┘
        |
   [FastAPI REST]
        |
┌───────┼──────────┐
[Dashboard] [Alertas RT] [Integración]
```

### Tecnologías en arquitectura futura
- **Base de datos:** Oracle / PostgreSQL
- **ETL:** Apache Airflow o AWS Glue
- **Serving del modelo:** FastAPI + Docker
- **Orquestación:** Kubernetes
- **Monitoreo:** Grafana + Prometheus
- **MLOps:** MLflow para versionado de modelos
