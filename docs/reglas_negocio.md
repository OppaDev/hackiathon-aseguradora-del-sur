# Reglas de Negocio Antifraude — FraudIA Claims

## Principio

Las reglas asignan puntos de riesgo (0-100 acumulado). Cada regla genera una explicación textual en español legible para el analista. Ninguna regla acusa fraude: señalan la necesidad de revisión.

## Tabla de reglas

| Código | Regla | Condición | Puntos | Severidad |
|---|---|---|---|---|
| R001 | Reclamo inicio de vigencia (crítico) | ≤ 10 días desde inicio póliza | 8 | CRÍTICO |
| R002 | Reclamo inicio de vigencia (alto) | 11-30 días desde inicio póliza | 4 | ALTO |
| R003 | Reclamo fin de vigencia (crítico) | ≤ 10 días hasta fin póliza | 8 | CRÍTICO |
| R004 | Reclamo fin de vigencia (alto) | 11-30 días hasta fin póliza | 4 | ALTO |
| R004b | Siniestro extremo borde vigencia | < 2 días (< 48 horas) | 10 | CRÍTICO |
| R005 | Reporte tardío | > 7 días entre ocurrencia y reporte | 5 | MEDIO |
| R006 | Demora atípica denuncia robo | > 4 días en caso de robo | 8 | CRÍTICO |
| R007 | Demora moderada denuncia robo | 24-48 horas en caso de robo | 4 | ALTO |
| R008 | Alta frecuencia asegurado | ≥ 3 reclamos previos del asegurado | 8 | ALTO |
| R009 | Alta frecuencia vehículo | ≥ 3 reclamos del mismo vehículo/placa | 6 | ALTO |
| R010 | Alta frecuencia solo RC | > 2 eventos previos solo Responsabilidad Civil | 6 | MEDIO |
| R011 | Proveedor en lista restrictiva | proveedor_lista_restrictiva = True | 10 | CRÍTICO |
| R012 | Factura alterada | Detectada en PDF o hoja documentos | 15 | CRÍTICO |
| R013 | RUC inválido | RUC con formato incorrecto o marcado | 10 | CRÍTICO |
| R014 | Narrativa idéntica (clonada) | similitud_narrativa ≥ 0.85 | 8 | CRÍTICO |
| R015 | Narrativa similar | similitud_narrativa entre 0.70-0.84 | 4 | ALTO |
| R016 | Monto excede suma asegurada | monto_reclamado > 95% de suma_asegurada | 5 | ALTO |
| R017 | Monto atípico vs proveedor | monto_reclamado > promedio_proveedor × 1.5 | 4 | MEDIO |
| R018 | Parte policial tardío | Parte elaborado > 7 días después del hecho | 6 | ALTO |
| R019 | Robo sin denuncia previa | Cobertura robo + sin denuncia registrada | 12 | CRÍTICO |
| R020 | Tercero no identificado | Daño severo + tercero no identificado + sin cámaras | 5 | MEDIO |
| R021 | Pérdida Total por Robo (PTxRB) | Cobertura PTxRB activa | 8 | CRÍTICO |
| R022 | Accidente madrugada sin testigos | Hora entre 00:00-05:00 + sin testigos | 6 | MEDIO |
| R023 | Documentos incompletos | docs_completos = False | 4 | BAJO |
| R024 | Fecha factura previa al siniestro | fecha_factura < fecha_ocurrencia | 10 | CRÍTICO |

## Reglas críticas del reto (RF-0X)

Las siguientes reglas del documento oficial se mapean directamente:

| Código oficial | Equivalente interno | Clasificación |
|---|---|---|
| RF-01 | R021 | Rojo automático |
| RF-02 | R012 + R024 | Rojo automático |
| RF-03 | R011 | Rojo automático |
| RF-04 | Lógica de dinámica imposible | Rojo automático |
| RF-05 | R001 + R003 + R004b | Amarillo forzado mínimo |
| RF-06 | R006 | Amarillo forzado mínimo |
| RF-07 | R014 | Amarillo forzado mínimo |

> Si se activa cualquier regla con clasificación "Rojo automático", el nivel de riesgo es Rojo independientemente del score numérico.

## Ejemplos de explicaciones generadas

**R012 activada:**
> "La factura asociada a este siniestro presenta marcas de posible alteración documental. Se recomienda revisión de la documentación original por el área de auditoría."

**R001 activada:**
> "El siniestro ocurrió 7 días después del inicio de la póliza. Esta temporalidad requiere verificación documental adicional."

**R014 activada:**
> "La descripción del evento presenta una similitud del 91% con el siniestro SIN-0087. Se recomienda comparar ambos relatos."
