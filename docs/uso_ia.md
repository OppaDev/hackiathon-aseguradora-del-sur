# Uso de Inteligencia Artificial — FraudIA Claims

## Descripción general

FraudIA Claims utiliza inteligencia artificial en cuatro niveles complementarios para detectar posibles señales de riesgo en siniestros de seguros.

## Componentes de IA

### 1. Motor de reglas (Fase 4)
24 reglas antifraude (R001–R024) basadas en conocimiento de dominio del sector asegurador ecuatoriano. Cada regla evalúa un patrón específico y asigna un puntaje de riesgo.

### 2. Modelos ML supervisado y no supervisado (Fase 8–9)
- **RandomForestClassifier**: modelo supervisado entrenado con 28 features sobre 400 siniestros. Métricas: F1=1.0, AUC-ROC=1.0, CV F1 mean=0.951.
- **IsolationForest**: modelo no supervisado para detección de anomalías (contamination=0.15). No requiere etiquetas.
- Entrenamiento en Google Colab; artefactos exportados como `.pkl`.

### 3. Análisis NLP (Fase 7)
TF-IDF sobre narrativas de siniestros para detectar:
- Descripciones idénticas o muy similares entre distintos siniestros.
- Narrativas de alta frecuencia que sugieren patrones repetitivos.

### 4. Agente conversacional con Claude API (Fase 10)
Integración con `claude-haiku-4-5-20251001` para:
- Análisis narrativo en lenguaje natural de siniestros específicos.
- Respuesta a preguntas del analista sobre el portafolio.
- Resumen ejecutivo automático.

**Modo fallback**: si `ANTHROPIC_API_KEY` no está disponible, el agente genera análisis determinísticos basados en plantillas y las reglas disparadas. El sistema opera completamente sin API key.

## Score de riesgo final

```
score_riesgo = 40% × score_reglas
             + 25% × score_documental
             + 20% × score_modelo_ml
             + 15% × score_nlp
```

| Nivel | Rango | Acción |
|-------|-------|--------|
| BAJO  | 0–30  | Flujo normal de liquidación |
| MEDIO | 31–65 | Escalar a Unidad Antifraude |
| ALTO  | 66–100 | Revisión especializada de campo |

## Configuración del agente IA

### Desarrollo local
```bash
cp .env.example .env
# Editar .env con: ANTHROPIC_API_KEY=sk-ant-...
```

### Streamlit Community Cloud
En el panel del proyecto: **Settings → Secrets**:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```
