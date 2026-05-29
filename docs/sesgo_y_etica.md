# Sesgo, Ética y Limitaciones — FraudIA Claims

## Declaración de propósito

FraudIA Claims es una herramienta de **apoyo a la decisión humana**. No toma decisiones autónomas, no acusa fraude y no rechaza siniestros. Su único propósito es priorizar casos para revisión por analistas especializados.

---

## Análisis de posibles sesgos

### Sesgo geográfico
Las reglas y el modelo se entrenaron con datos sintéticos que pueden sobre-representar ciertas ciudades o sucursales. Un proveedor en una región con menor historial podría recibir alertas injustificadas por menor densidad de datos comparativos.

**Mitigación:** Las reglas usan umbrales absolutos (días, montos, frecuencias), no comparaciones relativas por región.

### Sesgo por frecuencia histórica
El historial de reclamos del asegurado puede penalizar a clientes legítimos con múltiples siniestros reales (ej. accidentes reales en zonas de alta siniestralidad).

**Mitigación:** R008 y R009 son señales, no determinantes. El score ponderado necesita acumulación de múltiples alertas para llegar a nivel rojo.

### Sesgo por tipo de cobertura
Coberturas de alto valor (PTxRB, pérdida total) generan alertas automáticas por diseño del reto. Esto puede sesgar hacia ciertos tipos de clientes (vehículos de mayor valor).

**Mitigación:** La regla R021 tiene peso moderado (8 pts) y sola no alcanza nivel rojo.

### Sesgo del modelo de anomalías
Isolation Forest puede marcar como anómalos casos que simplemente son poco frecuentes en el dataset de entrenamiento, sin ser fraudulentos.

**Mitigación:** El modelo IA representa solo el 20% del score final. Las reglas explicables representan el 40%.

---

## Tasa de falsos positivos esperada

Con el score actual y umbrales definidos, se estima:
- **Nivel rojo:** ~5-10% de los casos analizados. De estos, se estima que una fracción significativa son falsos positivos que el analista descartará en revisión.
- **Nivel amarillo:** ~20-30% de los casos. Mayor tolerancia a falsos positivos por ser revisión documental menos costosa.

**Recomendación operativa:** Implementar un mecanismo de retroalimentación donde el analista registre el resultado de la revisión para recalibrar los umbrales del modelo con el tiempo.

---

## Limitaciones explícitas del sistema

1. **Datos sintéticos:** El sistema fue desarrollado y evaluado con datos sintéticos generados para el hackathon. El rendimiento en datos reales puede diferir significativamente.

2. **26 PDFs de muestra:** Solo ~5% de los siniestros tienen PDFs disponibles para análisis documental profundo. El resto se evalúa únicamente con variables del Excel.

3. **No cubre fraude organizado avanzado:** El sistema detecta patrones individuales conocidos. Esquemas de fraude coordinado entre múltiples actores pueden requerir técnicas de análisis de grafos más avanzadas.

4. **NLP en español limitado:** El análisis de similitud textual usa TF-IDF sobre textos en español. No captura semántica profunda (paráfrasis, sinónimos creativos).

5. **Modelo no validado en producción:** Los modelos Isolation Forest y Random Forest fueron entrenados con etiquetas simuladas, no con fraudes confirmados reales.

6. **Sin actualización en tiempo real:** El sistema procesa datos en batch. No detecta fraude mientras el siniestro está siendo reportado.

---

## Principios éticos aplicados

- **Transparencia:** Cada alerta incluye la regla específica que la generó.
- **Explicabilidad:** El score tiene desglose por componente (reglas, documental, modelo, NLP).
- **Proporcionalidad:** El lenguaje usa "posible señal de riesgo", no "fraude confirmado".
- **Supervisión humana:** El sistema no toma decisiones de pago o rechazo.
- **Derecho de revisión:** El analista puede ver exactamente qué datos generaron cada alerta.
- **No discriminación:** Las reglas usan variables de comportamiento del siniestro, no atributos demográficos del asegurado.

---

## Recomendaciones para implementación real

1. Validar el modelo con al menos 6 meses de casos con etiquetas de fraude confirmado antes de producción.
2. Establecer un comité de revisión para casos en nivel rojo antes de cualquier acción.
3. Documentar y auditar todas las decisiones tomadas a partir de las alertas del sistema.
4. Revisar umbrales semestralmente según tasas de falsos positivos observadas.
5. No usar el score como único criterio en ningún proceso formal de rechazo de siniestro.
