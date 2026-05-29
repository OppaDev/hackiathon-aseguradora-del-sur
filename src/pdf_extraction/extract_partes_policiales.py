"""
Extractor de Partes Policiales PDF.

Estructura observada en los PDFs reales:
  - Encabezado: Parte No: PTACP...  Doc ID Sistema: DOC-XXXX (SIN: SIN-XXXX)
  - Fecha de Elaboracion: YYYY-MM-DD  Hora: HH:MM:SS
  - Fecha del Hecho: YYYY-MM-DD
  - Hora Aproximada: HH:MM:SS
  - Calle 1 / Calle 2
  - Tipo de accidente: [X] en la opción correspondiente
  - Consecuencias: texto
  - Flagrancia: SI/NO
  - Circunstancias del Hecho: texto libre
  - Participantes con Placa, Estado (LESIONADO/ILESO), Detenido
  - OBSERVACION: texto adicional
"""

import re
from datetime import datetime
from typing import Optional
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patrones regex
# ---------------------------------------------------------------------------

RE_SIN            = re.compile(r"Siniestro[:\s]+([A-Z0-9\-]+)", re.IGNORECASE)
RE_DOC_ID         = re.compile(r"Doc ID(?:\s*Sistema)?[:\s]+([A-Z0-9\-]+)", re.IGNORECASE)
RE_PARTE_NO       = re.compile(r"Parte No[:\s]+([A-Z0-9]+)", re.IGNORECASE)
RE_FECHA_ELAB     = re.compile(r"Fecha de Elaboracion[:\s]+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
RE_FECHA_HECHO    = re.compile(r"Fecha del Hecho[:\s]+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
RE_HORA_HECHO     = re.compile(r"Hora Aproximada[:\s]+(\d{2}:\d{2}:\d{2})", re.IGNORECASE)
RE_CALLE1         = re.compile(r"Calle 1[:\s]+(.+?)(?:\nCalle 2|\n)", re.IGNORECASE)
RE_CONSECUENCIAS  = re.compile(r"Consecuencias[:\s]+(.+?)(?:\nClima|$)", re.IGNORECASE | re.DOTALL)
RE_FLAGRANCIA     = re.compile(r"Flagrancia[:\s]+(SI|NO)", re.IGNORECASE)
RE_TIPO_ACC       = re.compile(r"\[X\]\s*([^\n\[]+)", re.IGNORECASE)
RE_CIRCUNSTANCIAS = re.compile(
    r"Circunstancias del Hecho[:\s]*\n(.+?)(?:\nParte Elevado|$)", re.IGNORECASE | re.DOTALL
)
RE_OBSERVACION    = re.compile(r"OBSERVACION[:\s]+(.+?)(?:\nParte Elevado|$)", re.IGNORECASE | re.DOTALL)
RE_PLACA_VEH      = re.compile(r"Vehiculo Placa ([A-Z]{2,3}-\d{3,4})", re.IGNORECASE)
RE_DETENIDO       = re.compile(r"Detenido[:\s]+(SI|NO)", re.IGNORECASE)


def _dias_entre(fecha1_str: Optional[str], fecha2_str: Optional[str]) -> Optional[int]:
    """Calcula días entre dos fechas ISO (fecha1 - fecha2)."""
    if not fecha1_str or not fecha2_str:
        return None
    try:
        d1 = datetime.strptime(fecha1_str, "%Y-%m-%d")
        d2 = datetime.strptime(fecha2_str, "%Y-%m-%d")
        return (d1 - d2).days
    except ValueError:
        return None


def extract_parte_policial(text: str, archivo: str) -> dict:
    """
    Extrae campos de un parte policial PDF.
    """
    result = {
        "tipo_documento":         "Parte Policial",
        "archivo_pdf":            archivo,
        "id_siniestro":           None,
        "id_documento":           None,
        "numero_parte":           None,
        "fecha_elaboracion":      None,
        "fecha_hecho":            None,
        "hora_hecho":             None,
        "lugar":                  None,
        "tipo_accidente":         None,
        "consecuencias":          None,
        "flagrancia":             False,
        "robo":                   False,
        "perdida_total":          False,
        "lesionados":             False,
        "detenidos":              False,
        "sin_denuncia_previa":    False,
        "sin_testigos":           False,
        "parte_tardio_dias":      None,
        "placa_asegurado":        None,
        "observaciones":          None,
        "texto_extraido":         text[:500],
    }

    # IDs
    if m := RE_SIN.search(text):
        result["id_siniestro"] = m.group(1).strip()

    if m := RE_DOC_ID.search(text):
        result["id_documento"] = m.group(1).strip()

    if m := RE_PARTE_NO.search(text):
        result["numero_parte"] = m.group(1).strip()

    # Fechas
    if m := RE_FECHA_ELAB.search(text):
        result["fecha_elaboracion"] = m.group(1)

    if m := RE_FECHA_HECHO.search(text):
        result["fecha_hecho"] = m.group(1)

    if m := RE_HORA_HECHO.search(text):
        result["hora_hecho"] = m.group(1)

    # Días de retraso del parte
    result["parte_tardio_dias"] = _dias_entre(
        result["fecha_elaboracion"], result["fecha_hecho"]
    )

    # Lugar
    if m := RE_CALLE1.search(text):
        result["lugar"] = m.group(1).strip()

    # Tipo de accidente (checkbox [X])
    tipos = RE_TIPO_ACC.findall(text)
    if tipos:
        result["tipo_accidente"] = ", ".join(t.strip() for t in tipos)

    # Consecuencias
    if m := RE_CONSECUENCIAS.search(text):
        consecuencias = " ".join(m.group(1).strip().split())
        result["consecuencias"] = consecuencias
        result["perdida_total"] = any(
            kw in consecuencias.upper()
            for kw in ["PERDIDA TOTAL", "PÉRDIDA TOTAL", "PERDIDA DEL VEHICULO"]
        )
        result["lesionados"] = "LESIONADO" in consecuencias.upper()

    # Flagrancia
    if m := RE_FLAGRANCIA.search(text):
        result["flagrancia"] = m.group(1).upper() == "SI"

    # Robo (detectado en tipo de accidente O en consecuencias)
    result["robo"] = (
        "ROBO" in (result["tipo_accidente"] or "").upper()
        or "ROBO" in (result["consecuencias"] or "").upper()
    )

    # Circunstancias del hecho
    if m := RE_CIRCUNSTANCIAS.search(text):
        circunstancias = " ".join(m.group(1).strip().split())
        text_upper = circunstancias.upper()
        result["sin_denuncia_previa"] = any(
            kw in text_upper for kw in [
                "SIN DENUNCIA POLICIAL PREVIA",
                "NO PRESENTO DENUNCIA",
                "SIN DENUNCIA PREVIA",
            ]
        )
        result["sin_testigos"] = any(
            kw in text_upper for kw in [
                "NO EXISTEN TESTIGOS",
                "SIN TESTIGOS",
                "NO HAY TESTIGOS",
            ]
        )

    # Observaciones
    if m := RE_OBSERVACION.search(text):
        result["observaciones"] = " ".join(m.group(1).strip().split())

    # Placa del primer vehículo participante
    placas = RE_PLACA_VEH.findall(text)
    if placas:
        result["placa_asegurado"] = placas[0]

    # Detenidos
    detenidos = RE_DETENIDO.findall(text)
    result["detenidos"] = any(d.upper() == "SI" for d in detenidos)

    return result
