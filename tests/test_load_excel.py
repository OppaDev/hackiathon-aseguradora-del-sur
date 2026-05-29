"""Tests para src/ingestion/load_excel.py"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.ingestion.load_excel import (
    normalize_siniestros,
    normalize_proveedores,
    _to_bool,
    _aggregate_documents,
    _add_derived_features,
    validate_master,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_siniestro(**kwargs) -> pd.DataFrame:
    defaults = {
        "ID Siniestro": "SIN-0001",
        "ID Póliza": "POL-0001",
        "ID Asegurado": "ASE-0001",
        "Ramo": "Vehículos",
        "Placa Vehículo Asegurado": "ABC-1234",
        "Cobertura": "Choque",
        "Fecha Ocurrencia": "2024-01-15",
        "Fecha Reporte": "2024-01-18",
        "Días Ocurr→Reporte": 3,
        "Monto Reclamado ($)": 5000.0,
        "Monto Estimado ($)": 4800.0,
        "Monto Pagado ($)": 4800.0,
        "Estado": "Liquidado",
        "Sucursal": "Quito",
        "ID Proveedor": "PRO-001",
        "Descripción del Evento": "Choque leve en intersección",
        "Docs Completos": "Sí",
        "Prov. Lista Restrictiva": "No",
        "Días desde Inicio Póliza": 120,
        "Días hasta Fin Póliza": 245,
        "N° Reclamos Previos Asegurado": 1,
        "Suma Asegurada ($)": 20000.0,
        "Similitud Narrativa Máx.": 0.10,
        "Número Parte Policial": "PP-00123",
    }
    defaults.update(kwargs)
    return pd.DataFrame([defaults])


# ---------------------------------------------------------------------------
# _to_bool
# ---------------------------------------------------------------------------

def test_to_bool_si_no():
    s = pd.Series(["Sí", "No", "sí", "no", "SI"])
    result = _to_bool(s)
    assert result.tolist() == [True, False, True, False, True]


def test_to_bool_numeric():
    s = pd.Series([1, 0, 1])
    result = _to_bool(s)
    assert result.tolist() == [True, False, True]


def test_to_bool_nulos():
    s = pd.Series([None, np.nan, "Sí"])
    result = _to_bool(s)
    assert result.tolist() == [False, False, True]


# ---------------------------------------------------------------------------
# normalize_siniestros
# ---------------------------------------------------------------------------

def test_normalize_siniestros_columnas():
    df = normalize_siniestros(_make_siniestro())
    assert "id_siniestro" in df.columns
    assert "monto_reclamado" in df.columns
    assert "fecha_ocurrencia" in df.columns
    assert "docs_completos" in df.columns


def test_normalize_siniestros_tipos():
    df = normalize_siniestros(_make_siniestro())
    assert pd.api.types.is_float_dtype(df["monto_reclamado"])
    assert pd.api.types.is_datetime64_any_dtype(df["fecha_ocurrencia"])
    assert df["docs_completos"].dtype == bool


def test_normalize_siniestros_bool_proveedor():
    df = normalize_siniestros(_make_siniestro(**{"Prov. Lista Restrictiva": "Sí"}))
    assert df["proveedor_lista_restrictiva"].iloc[0] == True


# ---------------------------------------------------------------------------
# normalize_proveedores
# ---------------------------------------------------------------------------

def test_normalize_proveedores_sin_unnamed():
    raw = pd.DataFrame([{
        "ID Proveedor": "PRO-001",
        "Nombre Proveedor": "Taller ABC",
        "Tipo": "Taller",
        "Ciudad": "Quito",
        "N° Siniestros Asociados": 5,
        "En Lista Restrictiva": "No",
        "Motivo Restricción": "",
        "Promedio Monto ($)": 3500.0,
        "Unnamed: 8": None,
    }])
    df = normalize_proveedores(raw)
    assert "Unnamed: 8" not in df.columns
    assert "nombre_proveedor" in df.columns


# ---------------------------------------------------------------------------
# _aggregate_documents
# ---------------------------------------------------------------------------

def test_aggregate_documents_conteo():
    doc = pd.DataFrame([
        {"id_documento": "DOC-001", "id_siniestro": "SIN-0001",
         "tipo_documento": "Factura", "nombre_archivo_pdf": "f1.pdf"},
        {"id_documento": "DOC-002", "id_siniestro": "SIN-0001",
         "tipo_documento": "Parte Policial", "nombre_archivo_pdf": "p1.pdf"},
        {"id_documento": "DOC-003", "id_siniestro": "SIN-0002",
         "tipo_documento": "Factura", "nombre_archivo_pdf": "f2.pdf"},
    ])
    agg = _aggregate_documents(doc)
    sin1 = agg[agg["id_siniestro"] == "SIN-0001"].iloc[0]
    assert sin1["cantidad_documentos"] == 2


# ---------------------------------------------------------------------------
# _add_derived_features
# ---------------------------------------------------------------------------

def test_derived_ratio_monto():
    df = pd.DataFrame([{"monto_reclamado": 19000.0, "suma_asegurada": 20000.0}])
    df = _add_derived_features(df)
    assert abs(df["ratio_monto_suma"].iloc[0] - 0.95) < 0.001


def test_derived_narrativa_clonada():
    df = pd.DataFrame([
        {"similitud_narrativa": 0.90},
        {"similitud_narrativa": 0.75},
        {"similitud_narrativa": 0.30},
    ])
    df = _add_derived_features(df)
    assert df["narrativa_clonada"].tolist() == [True, False, False]
    assert df["narrativa_similar"].tolist() == [True, True, False]


def test_derived_reporte_tardio():
    df = pd.DataFrame([
        {"dias_ocurrencia_reporte": 10},
        {"dias_ocurrencia_reporte": 3},
    ])
    df = _add_derived_features(df)
    assert df["reporte_tardio"].tolist() == [True, False]


# ---------------------------------------------------------------------------
# validate_master
# ---------------------------------------------------------------------------

def test_validate_master_ok():
    df = normalize_siniestros(_make_siniestro())
    df = _add_derived_features(df)
    issues = validate_master(df)
    errores = [i for i in issues if i.startswith("CRÍTICO")]
    assert len(errores) == 0


def test_validate_master_sin_id():
    df = pd.DataFrame([{"col": "valor"}])
    issues = validate_master(df)
    assert any("id_siniestro" in i for i in issues)
