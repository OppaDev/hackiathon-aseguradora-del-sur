# Limitaciones del sistema — FraudIA Claims

## Limitaciones técnicas

### Dataset sintético
El sistema fue entrenado y validado sobre un dataset sintético de 500 siniestros generado para el hackathon. Las métricas de modelo (F1=1.0, AUC-ROC=1.0) reflejan la naturaleza sintética de los datos y **no deben interpretarse como rendimiento real en producción**.

Para despliegue productivo se requiere:
- Reentrenamiento con siniestros históricos reales etiquetados por expertos.
- Validación cruzada con datos de múltiples períodos.
- Ajuste de umbrales de riesgo según el apetito de riesgo de la aseguradora.

### NLP sobre datos sintéticos
El dataset tiene solo 33 descripciones únicas para 500 siniestros. El análisis de similitud opera a nivel de grupos, no de similitud individual entre siniestros distintos. En datos reales, la variabilidad narrativa será mayor.

### Modelo no supervisado
IsolationForest asume que ~15% de los siniestros son anómalos (`contamination=0.15`). Este parámetro debe calibrarse con datos reales y estimaciones del equipo antifraude.

## Limitaciones éticas y legales

### El sistema NO puede:
- **Tomar decisiones de pago o rechazo** de siniestros.
- **Acusar a ninguna persona** de cometer fraude.
- **Constituir prueba legal** de ningún tipo.
- **Reemplazar el criterio** del equipo humano especializado.

### El sistema SOLO puede:
- Identificar posibles señales de riesgo para revisión humana.
- Priorizar casos que podrían merecer atención adicional.
- Generar hipótesis de análisis que deben ser verificadas.

### Riesgo de sesgo
Las reglas y el modelo pueden generar falsos positivos que afecten desproporcionadamente a ciertos perfiles de asegurados o proveedores. Se recomienda:
- Monitoreo periódico de la tasa de falsos positivos por segmento.
- Revisión humana obligatoria antes de cualquier acción sobre un siniestro.
- Auditoría regular de los patrones de activación de reglas.

## Limitaciones operativas

- **Sin tiempo real**: el sistema procesa lotes de siniestros; no está diseñado para scoring en tiempo real de siniestros individuales al momento del reporte.
- **Sin integración a core**: requiere exportación manual de datos del sistema core de la aseguradora.
- **Modelos estáticos**: los modelos no se actualizan automáticamente; requieren reentrenamiento periódico.
