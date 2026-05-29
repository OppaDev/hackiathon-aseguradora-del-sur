"""
Extractor de facturas PDF.

Estructura observada en los PDFs reales:
  - Proveedor en la primera línea de texto
  - RUC: XXXXXXXXX (puede incluir "- INVÁLIDO")
  - Fecha: YYYY-MM-DD
  - Nº: 001-002-XXXXXXXXX
  - Siniestro Ref: SIN-XXXX
  - Cliente: nombre (puede saltar línea)
  - Placa: XXX-XXXX
  - Subtotal / IVA / TOTAL A PAGAR con valores en línea siguiente
  - Caso: Legítimo / Fraude / Inconsistente
  - "DOCUMENTO ALTERADO" si está adulterado
"""

import re
from pathlib import Path
from typing import Optional
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patrones regex
# ---------------------------------------------------------------------------

RE_SIN           = re.compile(r"Siniestro\s*Ref[:\s]+([A-Z0-9\-]+)", re.IGNORECASE)
RE_DOC_ALTERADO  = re.compile(r"DOCUMENTO\s+ALTERADO", re.IGNORECASE)
RE_RUC       = re.compile(r"RUC[:\s]+([\d]+(?:\s*-\s*INV[ÁA]LIDO)?)", re.IGNORECASE)
RE_FECHA     = re.compile(r"Fecha[:\s]+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
RE_NUMERO    = re.compile(r"N[°º][:\s]+([\d\-]+)", re.IGNORECASE)
RE_PLACA     = re.compile(r"Placa[:\s]*\n([A-Z]{2,3}-\d{3,4})", re.IGNORECASE)
RE_TOTAL     = re.compile(r"TOTAL A PAGAR\s*\n\s*\$([\d,\.]+)")
RE_SUBTOTAL  = re.compile(r"Subtotal\s+\d+%\s*\n\s*\$([\d,\.]+)")
RE_IVA       = re.compile(r"IVA\s+\d+%\s*\n\s*\$([\d,\.]+)")
RE_CLIENTE   = re.compile(r"Cliente[:\s]*\n(.+?)(?:\nPlaca|\nC\.I)", re.DOTALL)
RE_CASO      = re.compile(r"Caso[:\s]+(Leg[íi]timo|Fraude|Inconsistente)", re.IGNORECASE)


def _parse_monto(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    return float(raw.replace(",", "").replace(" ", ""))


def extract_factura(text: str, archivo: str) -> dict:
    """
    Extrae campos de una factura PDF a partir del texto plano.
    Devuelve un dict con los campos estructurados.
    """
    result = {
        "tipo_documento":    "Factura",
        "archivo_pdf":       archivo,
        "id_siniestro":      None,
        "proveedor":         None,
        "ruc":               None,
        "ruc_invalido":      False,
        "fecha_factura":     None,
        "numero_factura":    None,
        "cliente":           None,
        "placa":             None,
        "subtotal":          None,
        "iva":               None,
        "total":             None,
        "factura_alterada":  False,
        "caso_marcado":      None,
        "texto_extraido":    text[:500],  # primeros 500 chars para auditoría
    }

    # ID siniestro
    m = RE_SIN.search(text)
    if m:
        result["id_siniestro"] = m.group(1).strip()

    # Proveedor: línea anterior a "Servicios Automotrices Integrales" (subtítulo fijo)
    # Si el nombre ocupa dos líneas (ej. "TALLER NO REGISTRADO —\nA RED DE FRAUDE"),
    # se concatenan las dos líneas previas al subtítulo.
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    SUBTITULO = "Servicios Automotrices Integrales".upper()
    for i, line in enumerate(lines):
        if line.upper() == SUBTITULO and i >= 1:
            linea_1 = lines[i - 1]
            # Concatenar con la línea anterior si la inmediata no parece un
            # nombre completo de taller: comienza con preposición, es corta,
            # o la línea anterior no contiene "$" ni es numérica.
            if i >= 2:
                linea_0 = lines[i - 2]
                es_continuacion = (
                    linea_1[:2].upper() in ("A ", "DE", "Y ", "EL", "LA", "LO")
                    or len(linea_1) < 8
                    or linea_1.endswith("—")
                )
                es_precio = "$" in linea_0 or linea_0.replace(".", "").isdigit()
                if es_continuacion and not es_precio:
                    linea_1 = linea_0 + " " + linea_1
            result["proveedor"] = linea_1
            break
    # Fallback: línea antes de RUC si no se encontró subtítulo
    if not result["proveedor"]:
        for i, line in enumerate(lines):
            if line.upper().startswith("RUC") and i > 0:
                result["proveedor"] = lines[i - 1]
                break

    # RUC e indicador de inválido
    m = RE_RUC.search(text)
    if m:
        ruc_raw = m.group(1).strip()
        result["ruc"] = ruc_raw
        result["ruc_invalido"] = "INVÁLIDO" in ruc_raw.upper() or "INVALIDO" in ruc_raw.upper()

    # Fecha de factura
    m = RE_FECHA.search(text)
    if m:
        result["fecha_factura"] = m.group(1)

    # Número de factura
    m = RE_NUMERO.search(text)
    if m:
        result["numero_factura"] = m.group(1).strip()

    # Cliente
    m = RE_CLIENTE.search(text)
    if m:
        cliente = m.group(1).strip().replace("\n", " ")
        result["cliente"] = " ".join(cliente.split())

    # Placa
    m = RE_PLACA.search(text)
    if m:
        result["placa"] = m.group(1).strip()

    # Montos
    result["subtotal"] = _parse_monto(RE_SUBTOTAL.search(text) and RE_SUBTOTAL.search(text).group(1))
    result["iva"]      = _parse_monto(RE_IVA.search(text)      and RE_IVA.search(text).group(1))
    result["total"]    = _parse_monto(RE_TOTAL.search(text)    and RE_TOTAL.search(text).group(1))

    # Alertas documentales — el PDF tiene "DOCUMENTO\nALTERADO" con salto de línea
    result["factura_alterada"] = bool(RE_DOC_ALTERADO.search(text))
    result["caso_marcado"]     = (RE_CASO.search(text) or type("", (), {"group": lambda s, x: None})()).group(1)

    if m := RE_CASO.search(text):
        result["caso_marcado"] = m.group(1).strip().capitalize()

    return result
