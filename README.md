# FraudIA Claims — Detector de Posibles Fraudes en Siniestros

Prototipo funcional de Inteligencia Artificial para apoyar la detección de posibles patrones de fraude en siniestros de seguros.

> **Principio clave:** Esta herramienta genera alertas de revisión. No acusa fraude, no rechaza siniestros automáticamente y no sustituye al analista humano.

---

## Problema que resuelve

Los analistas de siniestros revisan cientos de casos manualmente, sin una herramienta que cruce automáticamente variables de pólizas, asegurados, proveedores, documentos y narrativas. Este sistema prioriza los casos que más requieren revisión especializada.

## Solución

Una **bandeja inteligente de priorización antifraude** que:

- Cruza datos estructurados del Excel con información extraída de PDFs
- Aplica 24 reglas de negocio antifraude con puntuación ponderada
- Usa Isolation Forest y Random Forest para detectar anomalías
- Analiza similitud textual entre narrativas de reclamos (TF-IDF)
- Construye una red de relaciones entre asegurados, proveedores y siniestros (NetworkX)
- Genera un score de riesgo 0-100 con semáforo verde/amarillo/rojo
- Permite consultas en lenguaje natural mediante Claude API (Anthropic)
- Produce justificaciones narrativas automáticas explicables para el analista

---

## Instalación local

### Opción A — Anaconda (recomendada)

```bash
conda env create -f environment.yml
conda activate fraudia
```

### Opción B — pip

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env y agregar tu ANTHROPIC_API_KEY
```

---

## Ejecución

```bash
streamlit run src/app/app.py
```

La aplicación estará disponible en `http://localhost:8501`

> Si no se configura `ANTHROPIC_API_KEY`, el agente IA opera en modo fallback programático sin interrupciones.

---

## Despliegue en Streamlit Cloud

1. Hacer fork/push del repositorio a GitHub
2. Ir a [share.streamlit.io](https://share.streamlit.io) → New app
3. Seleccionar repo y configurar `Main file path`: `src/app/app.py`
4. En **Advanced settings > Secrets**, agregar:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Deploy — URL pública lista en ~3 minutos

## Despliegue con Docker

```bash
docker build -t fraudia-claims .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... fraudia-claims
```

---

## Estructura del repositorio

```
fraudia-claims/
├── data/
│   ├── raw/              ← Excel y PDFs originales
│   ├── processed/        ← CSVs generados por la app
│   └── outputs/          ← Reportes exportados
├── models/               ← Artefactos del modelo entrenado en Colab
├── notebooks/            ← Notebook de entrenamiento (Google Colab)
├── src/
│   ├── ingestion/        ← Carga y limpieza del Excel
│   ├── pdf_extraction/   ← Extracción de texto de PDFs
│   ├── features/         ← Feature engineering y cruce de datos
│   ├── rules/            ← Motor de 24 reglas antifraude
│   ├── scoring/          ← Cálculo del score 0-100
│   ├── models/           ← Integración del modelo entrenado
│   ├── nlp/              ← Similitud narrativa (TF-IDF)
│   ├── network/          ← Red de relaciones (NetworkX)
│   ├── explainability/   ← Justificaciones del score
│   ├── ai_agent/         ← Agente Claude API + fallback
│   └── app/              ← Dashboard Streamlit
├── docs/                 ← Documentación técnica completa
└── tests/                ← Pruebas unitarias
```

---

## Flujo de datos

```
Excel (5 hojas / 500 siniestros)
    + 26 PDFs (facturas, partes policiales, declaraciones)
         ↓
    Ingesta y limpieza
         ↓
    Feature engineering + cruce documental
         ↓
    Motor de reglas (24 reglas) + Modelo IA + NLP + Red de relaciones
         ↓
    Score de riesgo 0-100
         ↓
    Semáforo Verde / Amarillo / Rojo
         ↓
    Dashboard + Agente IA (Claude) + Reporte exportable
```

---

## Score de riesgo

| Rango | Nivel | Acción sugerida |
|---|---|---|
| 0 - 40 | 🟢 Verde | Continuar flujo normal |
| 41 - 75 | 🟡 Amarillo | Escalar a Unidad Antifraude — revisión documental |
| 76 - 100 | 🔴 Rojo | Revisión especializada de campo |

**Composición del score:**
- 40% reglas de negocio
- 25% análisis documental
- 20% modelo IA
- 15% NLP (similitud narrativa)

---

## Dataset utilizado

Datos sintéticos generados para el hackIAthon 2026 — Reto Aseguradora del Sur.

- **500 siniestros** con 24 variables por caso
- **174 asegurados** anonimizados
- **33 proveedores** (talleres, clínicas, peritos)
- **1263 documentos** registrados
- **26 PDFs** de muestra: facturas, partes policiales y declaraciones de accidente

No contiene información personal real ni datos confidenciales de la aseguradora.

---

## Consideraciones éticas

- El sistema **no acusa fraude**. Genera señales de posible riesgo.
- El sistema **no rechaza siniestros** automáticamente.
- Toda decisión requiere revisión de un analista humano especializado.
- El lenguaje del sistema usa frases como: *"posible señal de riesgo"*, *"requiere revisión documental"*, *"caso priorizado para revisión humana"*.
- Ver [docs/sesgo_y_etica.md](docs/sesgo_y_etica.md) para análisis completo de limitaciones y riesgos.

---

## Documentación técnica

- [Arquitectura del sistema](docs/arquitectura.md)
- [Modelo de datos](docs/modelo_datos.md)
- [Reglas de negocio](docs/reglas_negocio.md)
- [Uso de IA](docs/uso_ia.md)
- [Limitaciones](docs/limitaciones.md)
- [Sesgo y ética](docs/sesgo_y_etica.md)
- [Guía de demo](docs/guia_demo.md)
