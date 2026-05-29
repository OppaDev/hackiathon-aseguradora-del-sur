"""
Fase 1 — Carga y limpieza del Excel
Lee las 5 hojas del dataset, normaliza columnas y genera claims_master.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeo de columnas originales → nombres normalizados
# ---------------------------------------------------------------------------

COLS_SINIESTROS = {
    "ID Siniestro": "id_siniestro",
    "ID Póliza": "id_poliza",
    "ID Asegurado": "id_asegurado",
    "Ramo": "ramo",
    "Placa Vehículo Asegurado": "placa",
    "Cobertura": "cobertura",
    "Fecha Ocurrencia": "fecha_ocurrencia",
    "Fecha Reporte": "fecha_reporte",
    "Días Ocurr→Reporte": "dias_ocurrencia_reporte",
    "Monto Reclamado ($)": "monto_reclamado",
    "Monto Estimado ($)": "monto_estimado",
    "Monto Pagado ($)": "monto_pagado",
    "Estado": "estado",
    "Sucursal": "sucursal",
    "ID Proveedor": "id_proveedor",
    "Descripción del Evento": "descripcion",
    "Docs Completos": "docs_completos",
    "Prov. Lista Restrictiva": "proveedor_lista_restrictiva",
    "Días desde Inicio Póliza": "dias_desde_inicio_poliza",
    "Días hasta Fin Póliza": "dias_hasta_fin_poliza",
    "N° Reclamos Previos Asegurado": "historial_siniestros_asegurado",
    "Suma Asegurada ($)": "suma_asegurada",
    "Similitud Narrativa Máx.": "similitud_narrativa",
    "Número Parte Policial": "numero_parte_policial",
}

COLS_POLIZAS = {
    "ID Póliza": "id_poliza",
    "ID Asegurado": "id_asegurado",
    "Ramo": "ramo_poliza",
    "Fecha Inicio": "fecha_inicio_poliza",
    "Fecha Fin": "fecha_fin_poliza",
    "Suma Asegurada ($)": "suma_asegurada_poliza",
    "Prima Anual ($)": "prima_anual",
    "Canal Venta": "canal_venta",
    "Estado Póliza": "estado_poliza",
}

COLS_ASEGURADOS = {
    "ID Asegurado": "id_asegurado",
    "Nombres Asegurado": "nombres_asegurado",
    "Segmento": "segmento",
    "Ciudad": "ciudad",
    "Antigüedad (años)": "antiguedad_anios",
    "N° Pólizas Activas": "n_polizas_activas",
    "N° Reclamos Últimos 12 Meses": "n_reclamos_12_meses",
    "N° Reclamos Histórico Total": "n_reclamos_historico",
    "Reclamos RC sin Tercero": "reclamos_rc_sin_tercero",
    "Perfil Riesgo Histórico": "perfil_riesgo_historico",
}

COLS_PROVEEDORES = {
    "ID Proveedor": "id_proveedor",
    "Nombre Proveedor": "nombre_proveedor",
    "Tipo": "tipo_proveedor",
    "Ciudad": "ciudad_proveedor",
    "N° Siniestros Asociados": "n_siniestros_proveedor",
    "En Lista Restrictiva": "proveedor_en_lista_restrictiva",
    "Motivo Restricción": "motivo_restriccion",
    "Promedio Monto ($)": "promedio_monto_proveedor",
}

COLS_DOCUMENTOS = {
    "ID Documento": "id_documento",
    "ID Siniestro": "id_siniestro",
    "Tipo Documento": "tipo_documento",
    "Nombre Archivo PDF": "nombre_archivo_pdf",
}


# ---------------------------------------------------------------------------
# Funciones de carga
# ---------------------------------------------------------------------------

def load_excel(path: str) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel y devuelve un dict {nombre_hoja: DataFrame}."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    log.info(f"Leyendo Excel: {path.name}")
    xl = pd.ExcelFile(path)

    hojas_requeridas = {"1_Siniestros", "2_Polizas", "3_Asegurados", "4_Proveedores", "5_Documentos"}
    hojas_disponibles = set(xl.sheet_names)
    faltantes = hojas_requeridas - hojas_disponibles
    if faltantes:
        raise ValueError(f"Faltan hojas en el Excel: {faltantes}")

    sheets = {}
    for hoja in hojas_requeridas:
        sheets[hoja] = xl.parse(hoja)
        log.info(f"  {hoja}: {len(sheets[hoja])} filas, {len(sheets[hoja].columns)} columnas")

    return sheets


def _rename(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Renombra columnas según el mapa, ignorando las que no existan."""
    existing = {k: v for k, v in col_map.items() if k in df.columns}
    missing = set(col_map.keys()) - set(df.columns)
    if missing:
        log.warning(f"  Columnas no encontradas (se omiten): {missing}")
    return df.rename(columns=existing)


def _to_bool(series: pd.Series) -> pd.Series:
    """Convierte Sí/No, True/False, 1/0 a bool."""
    mapping = {
        "sí": True, "si": True, "yes": True, "true": True, "1": True, 1: True, True: True,
        "no": False, "false": False, "0": False, 0: False, False: False,
    }
    return series.map(lambda x: mapping.get(str(x).strip().lower(), False) if pd.notna(x) else False)


def normalize_siniestros(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename(df, COLS_SINIESTROS)

    # Fechas
    for col in ["fecha_ocurrencia", "fecha_reporte"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numéricos
    for col in ["monto_reclamado", "monto_estimado", "monto_pagado", "suma_asegurada",
                "dias_ocurrencia_reporte", "dias_desde_inicio_poliza", "dias_hasta_fin_poliza",
                "historial_siniestros_asegurado", "similitud_narrativa"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Booleanos
    for col in ["docs_completos", "proveedor_lista_restrictiva"]:
        if col in df.columns:
            df[col] = _to_bool(df[col])

    # Texto limpio
    for col in ["id_siniestro", "id_poliza", "id_asegurado", "id_proveedor",
                "ramo", "cobertura", "estado", "sucursal", "placa", "descripcion"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Validar ID único
    dupes = df["id_siniestro"].duplicated().sum()
    if dupes > 0:
        log.warning(f"  {dupes} IDs de siniestro duplicados")

    log.info(f"  Siniestros normalizados: {len(df)} filas")
    return df


def normalize_polizas(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename(df, COLS_POLIZAS)

    for col in ["fecha_inicio_poliza", "fecha_fin_poliza"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["suma_asegurada_poliza", "prima_anual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info(f"  Pólizas normalizadas: {len(df)} filas")
    return df


def normalize_asegurados(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename(df, COLS_ASEGURADOS)

    for col in ["antiguedad_anios", "n_polizas_activas", "n_reclamos_12_meses",
                "n_reclamos_historico", "reclamos_rc_sin_tercero"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    log.info(f"  Asegurados normalizados: {len(df)} filas")
    return df


def normalize_proveedores(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename(df, COLS_PROVEEDORES)

    # Eliminar columna extra sin nombre si existe
    df = df[[c for c in df.columns if not c.startswith("Unnamed")]]

    for col in ["n_siniestros_proveedor", "promedio_monto_proveedor"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "proveedor_en_lista_restrictiva" in df.columns:
        df["proveedor_en_lista_restrictiva"] = _to_bool(df["proveedor_en_lista_restrictiva"])

    log.info(f"  Proveedores normalizados: {len(df)} filas")
    return df


def normalize_documentos(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename(df, COLS_DOCUMENTOS)
    for col in ["id_documento", "id_siniestro", "tipo_documento"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    log.info(f"  Documentos normalizados: {len(df)} filas")
    return df


# ---------------------------------------------------------------------------
# Construcción de la tabla maestra
# ---------------------------------------------------------------------------

def build_claims_master(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Cruza las 5 hojas del Excel y devuelve una tabla maestra por siniestro.
    """
    sin = normalize_siniestros(sheets["1_Siniestros"])
    pol = normalize_polizas(sheets["2_Polizas"])
    ase = normalize_asegurados(sheets["3_Asegurados"])
    pro = normalize_proveedores(sheets["4_Proveedores"])
    doc = normalize_documentos(sheets["5_Documentos"])

    log.info("Cruzando tablas...")

    # Cruce con Pólizas (left join — puede haber pólizas sin siniestro en esa hoja)
    pol_cols = ["id_poliza", "fecha_inicio_poliza", "fecha_fin_poliza",
                "prima_anual", "canal_venta", "estado_poliza"]
    pol_cols = [c for c in pol_cols if c in pol.columns]
    master = sin.merge(pol[pol_cols], on="id_poliza", how="left")

    # Cruce con Asegurados
    ase_cols = ["id_asegurado", "nombres_asegurado", "segmento", "ciudad",
                "antiguedad_anios", "n_polizas_activas", "n_reclamos_12_meses",
                "n_reclamos_historico", "reclamos_rc_sin_tercero", "perfil_riesgo_historico"]
    ase_cols = [c for c in ase_cols if c in ase.columns]
    master = master.merge(ase[ase_cols], on="id_asegurado", how="left")

    # Cruce con Proveedores
    pro_cols = ["id_proveedor", "nombre_proveedor", "tipo_proveedor",
                "ciudad_proveedor", "n_siniestros_proveedor",
                "proveedor_en_lista_restrictiva", "motivo_restriccion",
                "promedio_monto_proveedor"]
    pro_cols = [c for c in pro_cols if c in pro.columns]
    master = master.merge(pro[pro_cols], on="id_proveedor", how="left")

    # Cruce con Documentos: conteo y tipos por siniestro
    doc_agg = _aggregate_documents(doc)
    master = master.merge(doc_agg, on="id_siniestro", how="left")

    # Rellenar NaN en columnas de conteo
    conteo_cols = ["cantidad_documentos", "cantidad_facturas",
                   "cantidad_partes_policiales", "cantidad_declaraciones"]
    for col in conteo_cols:
        if col in master.columns:
            master[col] = master[col].fillna(0).astype(int)

    # Variables derivadas
    master = _add_derived_features(master)

    # Eliminar columnas duplicadas que puedan surgir del pivot de documentos
    master = master.loc[:, ~master.columns.duplicated()]

    log.info(f"Claims master generado: {len(master)} filas, {len(master.columns)} columnas")
    return master


def _aggregate_documents(doc: pd.DataFrame) -> pd.DataFrame:
    """Agrega la hoja 5_Documentos por id_siniestro."""
    agg = doc.groupby("id_siniestro").agg(
        cantidad_documentos=("id_documento", "count"),
    ).reset_index()

    # Conteo por tipo de documento
    if "tipo_documento" in doc.columns:
        tipo_pivot = doc.groupby(["id_siniestro", "tipo_documento"]).size().unstack(fill_value=0)
        tipo_pivot.columns = [
            f"cantidad_{c.lower().replace(' ', '_').replace('ó','o').replace('é','e')}"
            for c in tipo_pivot.columns
        ]
        # Garantizar columnas mínimas esperadas
        for col, label in [
            ("cantidad_facturas", "factura"),
            ("cantidad_partes_policiales", "parte_policial"),
            ("cantidad_declaraciones", "declaracion"),
        ]:
            # Buscar la columna que contenga la palabra clave
            match = [c for c in tipo_pivot.columns if label in c.lower()]
            if match:
                tipo_pivot = tipo_pivot.rename(columns={match[0]: col})
            elif col not in tipo_pivot.columns:
                tipo_pivot[col] = 0

        tipo_pivot = tipo_pivot.reset_index()
        agg = agg.merge(tipo_pivot, on="id_siniestro", how="left")

    return agg


def _add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas que se usarán en el motor de reglas."""

    # Ratio monto reclamado / suma asegurada
    if "monto_reclamado" in df.columns and "suma_asegurada" in df.columns:
        df["ratio_monto_suma"] = np.where(
            df["suma_asegurada"] > 0,
            df["monto_reclamado"] / df["suma_asegurada"],
            0
        ).round(4)

    # Delta monto vs promedio del proveedor
    if "monto_reclamado" in df.columns and "promedio_monto_proveedor" in df.columns:
        df["delta_monto_proveedor"] = (
            df["monto_reclamado"] - df["promedio_monto_proveedor"]
        ).round(2)

    # Indicador de reclamo cerca de inicio de vigencia
    if "dias_desde_inicio_poliza" in df.columns:
        df["alerta_borde_inicio"] = df["dias_desde_inicio_poliza"].apply(
            lambda x: True if pd.notna(x) and x <= 30 else False
        )

    # Indicador de reclamo cerca de fin de vigencia
    if "dias_hasta_fin_poliza" in df.columns:
        df["alerta_borde_fin"] = df["dias_hasta_fin_poliza"].apply(
            lambda x: True if pd.notna(x) and x <= 30 else False
        )

    # Indicador de reporte tardío
    if "dias_ocurrencia_reporte" in df.columns:
        df["reporte_tardio"] = df["dias_ocurrencia_reporte"].apply(
            lambda x: True if pd.notna(x) and x > 7 else False
        )

    # Indicador de narrativa similar (ya viene del Excel como float)
    if "similitud_narrativa" in df.columns:
        df["narrativa_similar"] = df["similitud_narrativa"] >= 0.70
        df["narrativa_clonada"] = df["similitud_narrativa"] >= 0.85

    log.info("  Variables derivadas calculadas")
    return df


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------

def validate_master(df: pd.DataFrame) -> list[str]:
    """Devuelve lista de problemas encontrados (vacía = OK)."""
    issues = []

    if "id_siniestro" not in df.columns:
        issues.append("CRÍTICO: falta columna id_siniestro")
        return issues

    null_ids = df["id_siniestro"].isna().sum()
    if null_ids > 0:
        issues.append(f"ADVERTENCIA: {null_ids} siniestros sin ID")

    dupes = df["id_siniestro"].duplicated().sum()
    if dupes > 0:
        issues.append(f"ADVERTENCIA: {dupes} IDs duplicados")

    for col in ["fecha_ocurrencia", "monto_reclamado", "suma_asegurada"]:
        if col in df.columns:
            nulls = df[col].isna().sum()
            if nulls > 0:
                issues.append(f"INFO: {nulls} valores nulos en {col}")

    if "monto_reclamado" in df.columns:
        negativos = (df["monto_reclamado"] < 0).sum()
        if negativos > 0:
            issues.append(f"ADVERTENCIA: {negativos} montos reclamados negativos")

    return issues


# ---------------------------------------------------------------------------
# Guardado
# ---------------------------------------------------------------------------

def save_processed(df: pd.DataFrame, output_path: str) -> None:
    """Guarda el DataFrame como CSV en la ruta indicada."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info(f"Guardado: {output_path} ({len(df)} filas)")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def run(excel_path: str, output_path: str) -> pd.DataFrame:
    """
    Pipeline completo: carga → normaliza → cruza → valida → guarda.
    Devuelve el DataFrame resultante.
    """
    sheets = load_excel(excel_path)
    master = build_claims_master(sheets)

    issues = validate_master(master)
    if issues:
        for issue in issues:
            log.warning(issue)
    else:
        log.info("Validación OK: sin problemas detectados")

    save_processed(master, output_path)
    return master


if __name__ == "__main__":
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    excel = root / "data" / "raw" / "excel" / "Evento Datasets_Sinteticos_Fraude_500_v2.xlsx"
    output = root / "data" / "processed" / "claims_master.csv"

    df = run(str(excel), str(output))
    print(f"\nResumen del claims_master:")
    print(f"  Filas: {len(df)}")
    print(f"  Columnas: {len(df.columns)}")
    print(f"  Columnas: {list(df.columns)}")
    print(f"\n  Niveles de riesgo pre-calculados:")
    if "proveedor_lista_restrictiva" in df.columns:
        print(f"    Prov. lista restrictiva: {df['proveedor_lista_restrictiva'].sum()}")
    if "reporte_tardio" in df.columns:
        print(f"    Reporte tardío (>7d):    {df['reporte_tardio'].sum()}")
    if "narrativa_clonada" in df.columns:
        print(f"    Narrativa clonada:       {df['narrativa_clonada'].sum()}")
    if "alerta_borde_inicio" in df.columns:
        print(f"    Borde inicio póliza:     {df['alerta_borde_inicio'].sum()}")
