# Guía de Demo — FraudIA Claims

## Inicio rápido

### Opción A: Ejecución local

```bash
# 1. Clonar e instalar
git clone <repo>
cd hackiathon-aseguradora-del-sur
pip install -r requirements.txt

# 2. Configurar API key (opcional)
cp .env.example .env
# Editar .env con ANTHROPIC_API_KEY

# 3. Lanzar dashboard
streamlit run src/app/app.py
# → http://localhost:8501
```

### Opción B: Docker

```bash
docker build -t fraudia-claims .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... fraudia-claims
# → http://localhost:8501
```

## Flujo recomendado para la demo

### 1. Resumen ejecutivo (2 min)
- Mostrar KPIs: 5 ALTO / 92 MEDIO / 403 BAJO.
- Hacer clic en **"Generar resumen ejecutivo con IA"**.
- Mostrar pie chart y distribución de scores.

### 2. Siniestro de alto riesgo (3 min)
- Ir a **Detalle de siniestro**.
- Seleccionar **SIN-0005** (score 91.6/100).
- Mostrar tab **Scores**: desglose de 4 componentes.
- Mostrar tab **Alertas**: 7 reglas disparadas (R002, R006, R012, R013, R019, R021, R023).
- Hacer clic en **Análisis IA** → análisis narrativo completo.

### 3. Explorador (2 min)
- Ir a **Explorador de siniestros**.
- Filtrar por nivel ALTO.
- Mostrar los 5 siniestros críticos.

### 4. Agente IA conversacional (3 min)
- Ir a **Agente IA → Chat libre**.
- Preguntar: *"¿Cuáles son los siniestros que más requieren atención?"*
- Preguntar: *"¿Qué patrones de riesgo son más comunes en este portafolio?"*

### 5. Modelo ML (1 min)
- Ir a **Modelo ML**.
- Mostrar métricas y SHAP importance.
- Destacar: `proveedor_lista_restrictiva` es el feature más importante.

### 6. Red de relaciones (1 min)
- Ir a **Red de relaciones**.
- Mostrar 707 nodos, 1000 conexiones.

## Casos de demo destacados

| Siniestro | Score | Por qué es interesante |
|-----------|-------|------------------------|
| SIN-0005  | 91.6  | Máximo score; proveedor restrictivo + narrativa clonada |
| SIN-0022  | 74.9  | Documentación incompleta + historial |
| SIN-0004  | 72.9  | RUC inválido + múltiples alertas |
| SIN-0009  | 71.9  | Siniestro en inicio de póliza |
| SIN-0006  | 70.1  | Reporte tardío + señales documentales |

## Mensaje clave para jueces

> FraudIA Claims **no reemplaza al analista** — lo empodera. El sistema identifica las 5-10 señales de riesgo que más merecen atención humana dentro de 500 siniestros, reduciendo el tiempo de revisión manual en horas. Toda decisión final es humana.
