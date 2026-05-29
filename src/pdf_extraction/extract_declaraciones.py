"""
Extractor de Declaraciones de Accidente PDF.

Estructura observada en los PDFs reales:
  - Doc ID Sistema: DOC-XXXX  /  Siniestro: SIN-XXXX
  - • Asegurado: nombre
  - • Póliza: VH-XXXX-XXXXXX
  - • Placa: XXX-XXXX
  - • Motor / Chasis
  - • Detalle de daños: texto
  - • Lugar / Fecha / Hora del accidente
  - • Explique detalladamente cómo ocurrió el accidente: relato
  - DATOS SOBRE EL CONTRARIO: placa, propietario (puede ser "No identificado")
  - • Testigos del accidente: texto (puede ser vacío o "No hay testigos")
  - INTERVENCIÓN DE AUTORIDADES
  - • Lugar donde se recibe asistencia médica
"""

import re
from typing import Optional
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patrones regex
# ---------------------------------------------------------------------------

RE_SIN           = re.compile(r"Siniestro[:\s]+([A-Z0-9\-]+)", re.IGNORECASE)
RE_DOC_ID        = re.compile(r"Doc ID(?:\s*Sistema)?[:\s]+([A-Z0-9\-]+)", re.IGNORECASE)
RE_ASEGURADO     = re.compile(r"•\s*Asegurado\s*\n(.+?)(?:\n•|\Z)", re.DOTALL)
RE_POLIZA        = re.compile(r"•\s*P[oó]liza\s*\n(.+?)(?:\n•|\Z)", re.DOTALL)
RE_PLACA         = re.compile(r"•\s*Placa\s*\n([A-Z]{2,3}-\d{3,4})", re.IGNORECASE)
RE_FECHA         = re.compile(r"•\s*Fecha\s+(\d{2}-\d{2}-\d{4})", re.IGNORECASE)
RE_HORA          = re.compile(r"•\s*Hora\s*\n(\d{2}:\d{2})", re.IGNORECASE)
RE_LUGAR         = re.compile(r"•\s*Lugar\s+(.+?)(?:\n•|\n•|\nVELOCIDAD)", re.IGNORECASE)
RE_DANOS         = re.compile(r"•\s*Detalle de da[ñn]os[:\s]*\n(.+?)(?:\n•|\n¿)", re.DOTALL | re.IGNORECASE)
RE_RELATO        = re.compile(
    r"Explique detalladamente.+?accidente[:\s]*\n(.+?)(?:\n•\s*•|\n•\s*A juicio)", re.DOTALL | re.IGNORECASE
)
RE_CONTRARIO_NOM = re.compile(r"Nombre del propietario\s*\n(.+?)(?:\n•|\Z)", re.DOTALL)
RE_CONTRARIO_PLA = re.compile(r"DATOS SOBRE EL CONTRARIO.+?Placa\s*\n([A-Z]{2,3}-\d{3,4})", re.DOTALL | re.IGNORECASE)
RE_TESTIGOS      = re.compile(r"Testigos del accidente\s*\n(.+?)(?:\nINTERVENCIÓN|\nINTERVENCION)", re.DOTALL | re.IGNORECASE)
RE_AUTORIDADES   = re.compile(r"agentes tomaron nota.+?\n(.+?)(?:\n•|\Z)", re.DOTALL | re.IGNORECASE)
RE_LESIONADOS    = re.compile(r"Lugar donde se recibe asistencia m[eé]dica\s*\n(.+?)(?:\nEl que|\Z)", re.DOTALL | re.IGNORECASE)
RE_VELOCIDAD     = re.compile(r"Velocidad\s*\n?(\d+)\s*Km", re.IGNORECASE)


def extract_declaracion(text: str, archivo: str) -> dict:
    """
    Extrae campos de una declaración de accidente PDF.
    """
    result = {
        "tipo_documento":          "Declaración Accidente",
        "archivo_pdf":             archivo,
        "id_siniestro":            None,
        "id_documento":            None,
        "nombre_asegurado":        None,
        "poliza":                  None,
        "placa":                   None,
        "fecha_accidente":         None,
        "hora_accidente":          None,
        "lugar":                   None,
        "danos_declarados":        None,
        "relato":                  None,
        "velocidad_kmh":           None,
        "tercero_identificado":    False,
        "placa_tercero":           None,
        "sin_testigos":            False,
        "sin_intervencion_policial": False,
        "lesionados":              False,
        "texto_extraido":          text[:500],
    }

    # IDs
    if m := RE_SIN.search(text):
        result["id_siniestro"] = m.group(1).strip()

    if m := RE_DOC_ID.search(text):
        result["id_documento"] = m.group(1).strip()

    # Datos del asegurado
    if m := RE_ASEGURADO.search(text):
        result["nombre_asegurado"] = " ".join(m.group(1).strip().split())

    if m := RE_POLIZA.search(text):
        result["poliza"] = m.group(1).strip()

    if m := RE_PLACA.search(text):
        result["placa"] = m.group(1).strip()

    # Datos del accidente
    if m := RE_FECHA.search(text):
        result["fecha_accidente"] = m.group(1).strip()

    if m := RE_HORA.search(text):
        result["hora_accidente"] = m.group(1).strip()

    if m := RE_LUGAR.search(text):
        result["lugar"] = " ".join(m.group(1).strip().split())

    if m := RE_DANOS.search(text):
        result["danos_declarados"] = " ".join(m.group(1).strip().split())

    if m := RE_RELATO.search(text):
        result["relato"] = " ".join(m.group(1).strip().split())

    if m := RE_VELOCIDAD.search(text):
        try:
            result["velocidad_kmh"] = int(m.group(1))
        except ValueError:
            pass

    # Tercero
    if m := RE_CONTRARIO_NOM.search(text):
        nombre_tercero = " ".join(m.group(1).strip().split())
        no_identificado = any(
            kw in nombre_tercero.upper()
            for kw in ["NO IDENTIFICADO", "DESCONOCIDO", "SE DIO A LA FUGA", "FUGA"]
        )
        result["tercero_identificado"] = not no_identificado

    if m := RE_CONTRARIO_PLA.search(text):
        placa_t = m.group(1).strip()
        if placa_t.upper() not in ("NO IDENTIFICADA", "DESCONOCIDO", ""):
            result["placa_tercero"] = placa_t
            result["tercero_identificado"] = True

    # Testigos
    if m := RE_TESTIGOS.search(text):
        testigos_text = " ".join(m.group(1).strip().split()).upper()
        result["sin_testigos"] = any(
            kw in testigos_text
            for kw in ["NO HAY TESTIGOS", "SIN TESTIGOS", "NO SE IDENTIFICAN"]
        )

    # Autoridades
    if m := RE_AUTORIDADES.search(text):
        aut_text = " ".join(m.group(1).strip().split()).upper()
        result["sin_intervencion_policial"] = any(
            kw in aut_text
            for kw in ["SIN INTERVENCIÓN", "SIN INTERVENCION", "POSTERIOR AL HECHO"]
        )

    # Lesionados
    if m := RE_LESIONADOS.search(text):
        les_text = " ".join(m.group(1).strip().split()).upper()
        result["lesionados"] = "NO SE REPORTAN LESIONADOS" not in les_text and bool(les_text)

    return result
