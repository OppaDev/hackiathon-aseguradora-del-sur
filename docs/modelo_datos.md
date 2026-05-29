# Modelo de Datos — FraudIA Claims

## Tablas de entrada (Excel)

### 1_Siniestros (500 registros)
| Campo original | Campo normalizado | Tipo | Descripción |
|---|---|---|---|
| ID Siniestro | id_siniestro | str | Identificador único (SIN-XXXX) |
| ID Póliza | id_poliza | str | Referencia a 2_Polizas |
| ID Asegurado | id_asegurado | str | Referencia a 3_Asegurados |
| Ramo | ramo | str | Vehículos, Salud, Vida, etc. |
| Placa Vehículo Asegurado | placa | str | Placa del vehículo |
| Cobertura | cobertura | str | Choque, Robo, Incendio, etc. |
| Fecha Ocurrencia | fecha_ocurrencia | date | Fecha del evento |
| Fecha Reporte | fecha_reporte | date | Fecha de notificación |
| Días Ocurr→Reporte | dias_ocurrencia_reporte | int | Diferencia en días |
| Monto Reclamado ($) | monto_reclamado | float | Valor solicitado |
| Monto Estimado ($) | monto_estimado | float | Valor estimado por la aseguradora |
| Monto Pagado ($) | monto_pagado | float | Valor pagado (si aplica) |
| Estado | estado | str | Reserva, Pago Total, Negativa, etc. |
| Sucursal | sucursal | str | Sucursal del siniestro |
| ID Proveedor | id_proveedor | str | Referencia a 4_Proveedores |
| Descripción del Evento | descripcion | str | Texto libre del reclamo |
| Docs Completos | docs_completos | bool | Indicador de documentación |
| Prov. Lista Restrictiva | proveedor_lista_restrictiva | bool | Proveedor en lista negra |
| Días desde Inicio Póliza | dias_desde_inicio_poliza | int | Días entre inicio póliza y siniestro |
| Días hasta Fin Póliza | dias_hasta_fin_poliza | int | Días entre siniestro y fin póliza |
| N° Reclamos Previos Asegurado | historial_siniestros_asegurado | int | Historial del asegurado |
| Suma Asegurada ($) | suma_asegurada | float | Cobertura máxima |
| Similitud Narrativa Máx. | similitud_narrativa | float | Similitud máxima con otro reclamo [0-1] |
| Número Parte Policial | numero_parte_policial | str | Referencia al parte policial |

### 2_Polizas (500 registros)
| Campo | Tipo | Descripción |
|---|---|---|
| id_poliza | str | PK |
| id_asegurado | str | FK → 3_Asegurados |
| ramo | str | |
| fecha_inicio | date | Inicio de vigencia |
| fecha_fin | date | Fin de vigencia |
| suma_asegurada | float | |
| prima_anual | float | |
| canal_venta | str | Directo, Agente, Broker |
| estado_poliza | str | Vigente, Vencida, Cancelada |

### 3_Asegurados (174 registros)
| Campo | Tipo | Descripción |
|---|---|---|
| id_asegurado | str | PK |
| nombres_asegurado | str | Anonimizado |
| segmento | str | Natural, Corporativo, etc. |
| ciudad | str | |
| antiguedad_anios | int | Años como cliente |
| n_polizas_activas | int | |
| n_reclamos_12_meses | int | |
| n_reclamos_historico | int | |
| reclamos_rc_sin_tercero | int | Reclamos RC sin tercero identificado |
| perfil_riesgo_historico | str | Bajo / Medio / Alto |

### 4_Proveedores (33 registros)
| Campo | Tipo | Descripción |
|---|---|---|
| id_proveedor | str | PK |
| nombre_proveedor | str | |
| tipo | str | Taller, Clínica, Perito, etc. |
| ciudad | str | |
| n_siniestros_asociados | int | |
| en_lista_restrictiva | bool | |
| motivo_restriccion | str | Razón de la restricción |
| promedio_monto | float | Monto promedio reclamado |

### 5_Documentos (1263 registros)
| Campo | Tipo | Descripción |
|---|---|---|
| id_documento | str | PK |
| id_siniestro | str | FK → 1_Siniestros |
| tipo_documento | str | Factura, Parte Policial, Declaración |
| nombre_archivo_pdf | str | Nombre del PDF (puede no existir físicamente) |

---

## Tablas procesadas (generadas por la app)

### claims_master.csv
Cruce de las 5 hojas del Excel. Una fila por siniestro.

### documents_extracted.csv
Campos extraídos de los 26 PDFs disponibles.
Campos clave: `factura_alterada`, `ruc_invalido`, `parte_tardio_dias`, `tercero_no_identificado`

### claims_with_documents.csv
`claims_master` enriquecido con variables documentales y features derivadas.

### claims_scored.csv
Tabla final con score de riesgo, nivel, alertas y explicación por siniestro.

### network_edges.csv
Aristas del grafo de relaciones: `origen`, `destino`, `tipo_relacion`, `peso`

---

## Relaciones entre tablas

```
1_Siniestros ──(id_poliza)──→ 2_Polizas
1_Siniestros ──(id_asegurado)──→ 3_Asegurados
1_Siniestros ──(id_proveedor)──→ 4_Proveedores
1_Siniestros ←──(id_siniestro)── 5_Documentos
```
