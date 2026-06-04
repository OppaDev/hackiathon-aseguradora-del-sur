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

## Flujo recomendado para la demo (10 min)

### 1. Resumen ejecutivo (1.5 min)
- Mostrar KPIs: **1 ALTO / 42 MEDIO / 457 BAJO** (500 siniestros totales).
- Hacer clic en **"Generar resumen ejecutivo con IA"**.
- Mostrar pie chart y distribución de scores con líneas en 40 y 75.

### 2. Siniestro de alto riesgo (2 min)
- Ir a **Detalle de siniestro** → seleccionar **SIN-0005** (score 91.6/100).
- Mostrar tab **Scores**: desglose 4 componentes (reglas 40% + documental 25% + modelo 20% + NLP 15%).
- Mostrar tab **Alertas**: 9 reglas disparadas.
- Hacer clic en **Análisis IA** → Claude genera narrativa explicativa.

### 3. Agente IA — preguntas del jurado (3 min)
- Ir a **Agente IA → Chat libre**.
- Preguntar (pregunta de fuego): *"¿Qué proveedores concentran el 80% de las alertas rojas?"*
- Preguntar: *"¿Qué patrones se repiten en los reclamos sospechosos?"*
- Preguntar: *"Recomienda qué casos debería revisar primero el analista."*

### 4. Prueba de Score — fire drill (2 min)
- Ir a **Cargar Siniestros**.
- Subir `data/processed/fire_drill_24h.csv` (siniestro ocurrido 1 día tras inicio de póliza).
- Pulsar **"Procesar y puntuar"** → Score **91/100 ALTO**, 9 reglas disparadas.
- En el chat inferior: *"¿Por qué este siniestro es de alto riesgo?"* → agente explica cada señal.

### 5. Modelo ML (1 min)
- Ir a **Modelo ML** → mostrar Precision 1.000, CV F1 0.951.
- Destacar SHAP: `proveedor_lista_restrictiva` y `doc_factura_alterada` como features top.

### 6. Red de relaciones (30 seg)
- Ir a **Red de relaciones** → mostrar grafo asegurado–proveedor–siniestro.

## Archivos CSV para la demo

| Archivo | Uso |
|---|---|
| `data/processed/sample_upload_demo.csv` | Demo general: 6 siniestros (1 ALTO, 3 MEDIO, 2 BAJO) |
| `data/processed/fire_drill_24h.csv` | Prueba de fuego: siniestro 24h tras inicio póliza → 91/100 ALTO |

## Casos de demo destacados (histórico)

| Siniestro | Score | Por qué es interesante |
|-----------|-------|------------------------|
| SIN-0005  | 91.6  | Máximo score; proveedor restrictivo + factura alterada + narrativa clonada |
| SIN-0022  | 74.9  | Factura alterada + proveedor lista + score documental alto |
| SIN-0004  | 72.9  | Factura alterada + múltiples alertas documentales |
| SIN-0009  | 71.9  | Borde inicio póliza + monto atípico |
| SIN-0006  | 70.1  | Reporte tardío + señales documentales + proveedor sospechoso |

## Preguntas del jurado — respuestas preparadas

El agente responde correctamente las 12 preguntas del PDF (verificado):
- Top 10 siniestros por riesgo ✅
- Proveedores con más alertas / 80% alertas rojas ✅
- Ramos con más casos sospechosos ✅
- Ciudades con mayor concentración ✅
- Asegurados con mayor frecuencia ✅
- Documentos faltantes en críticos ✅
- Casos con montos atípicos ✅
- Siniestros cerca inicio póliza ✅
- Patrones repetidos ✅
- Resumen ejecutivo casos críticos ✅
- Recomendación de casos a revisar ✅

## Mensaje clave para jueces

> FraudIA Claims **no reemplaza al analista** — lo empodera. El sistema identifica en segundos las señales de riesgo que más merecen atención humana dentro de 500 siniestros. El agente responde preguntas en lenguaje natural sobre el portafolio. Toda decisión final es humana.
