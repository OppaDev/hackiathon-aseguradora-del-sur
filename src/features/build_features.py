"""
Fase 3 — Feature Engineering y cruce documental.

Combina claims_master.csv + documents_extracted.csv en claims_with_documents.csv.
Por cada siniestro agrega las señales documentales de los PDFs y calcula
un sub-score documental crudo (0-100) para uso posterior en el scoring final.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agregación de señales documentales por siniestro
# ---------------------------------------------------------------------------

def _agg_docs(docs: pd.DataFrame) -> pd.DataFrame:
    """
    Recibe documents_extracted (26 filas, una por PDF).
    Devuelve un DataFrame con una fila por id_siniestro y columnas doc_*.
    """

    def _any_true(series: pd.Series) -> bool:
        # Convert via map to avoid FutureWarning from fillna on object dtype
        return bool(series.map(lambda x: bool(x) if x is not None and x == x else False).any())

    def _max_num(series: pd.Series):
        s = pd.to_numeric(series, errors="coerce")
        return s.max() if s.notna().any() else None

    agg_rows = []
    for sin_id, grp in docs.groupby("id_siniestro"):
        row = {"id_siniestro": sin_id}

        # Señales de facturas
        row["doc_factura_alterada"]      = _any_true(grp["factura_alterada"])
        row["doc_ruc_invalido"]          = _any_true(grp["ruc_invalido"])
        row["doc_caso_fraude"]           = (grp["caso_marcado"] == "Fraude").any()
        row["doc_caso_inconsistente"]    = (grp["caso_marcado"] == "Inconsistente").any()

        # Señales de partes policiales
        row["doc_parte_tardio_dias"]     = _max_num(grp.get("parte_tardio_dias", pd.Series(dtype=float)))
        row["doc_sin_denuncia_previa"]   = _any_true(grp.get("sin_denuncia_previa", pd.Series(dtype=bool)))
        row["doc_robo"]                  = _any_true(grp.get("robo", pd.Series(dtype=bool)))
        row["doc_perdida_total"]         = _any_true(grp.get("perdida_total", pd.Series(dtype=bool)))
        row["doc_flagrancia"]            = _any_true(grp.get("flagrancia", pd.Series(dtype=bool)))
        row["doc_lesionados"]            = _any_true(grp.get("lesionados", pd.Series(dtype=bool)))
        row["doc_detenidos"]             = _any_true(grp.get("detenidos", pd.Series(dtype=bool)))

        # Señales de declaraciones
        row["doc_tercero_identificado"]  = _any_true(grp.get("tercero_identificado", pd.Series(dtype=bool)))
        row["doc_sin_testigos"]          = _any_true(grp.get("sin_testigos", pd.Series(dtype=bool)))
        row["doc_sin_intervencion"]      = _any_true(grp.get("sin_intervencion_policial", pd.Series(dtype=bool)))

        # Hora del accidente (para regla R022: madrugada sin testigos)
        horas = grp["hora_accidente"].dropna() if "hora_accidente" in grp.columns else pd.Series(dtype=str)
        row["doc_hora_accidente"]        = horas.iloc[0] if len(horas) > 0 else None

        # Fecha de factura más temprana (para regla R024: factura previa al siniestro)
        fechas_fac = grp["fecha_factura"].dropna() if "fecha_factura" in grp.columns else pd.Series(dtype=str)
        row["doc_fecha_factura_min"]     = fechas_fac.min() if len(fechas_fac) > 0 else None

        # Metadata documental
        row["n_pdfs_extraidos"]          = len(grp)
        row["tipos_pdf"]                 = "|".join(grp["tipo_documento"].dropna().unique())

        agg_rows.append(row)

    return pd.DataFrame(agg_rows)


# ---------------------------------------------------------------------------
# Features derivadas combinadas (Excel + PDF)
# ---------------------------------------------------------------------------

def _add_combined_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas derivadas que cruzan datos del Excel con señales PDF."""

    df = df.copy()

    # Inconsistencia monto vs factura
    # Si hay factura y el total facturado difiere >20% del monto_reclamado
    # (aquí no tenemos el total de factura por siniestro en el master, pero sí
    # el ratio de montos ya calculado en Phase 1 — mantenemos la columna)

    # Parte tardío: señal binaria clara para el score
    df["doc_parte_tardio"] = (
        pd.to_numeric(df.get("doc_parte_tardio_dias", 0), errors="coerce").fillna(0) > 7
    )

    # Alta similitud narrativa + sin testigos → doble alerta
    sim = pd.to_numeric(df.get("similitud_narrativa", 0), errors="coerce").fillna(0)
    sin_testigos = df.get("doc_sin_testigos", False).fillna(False).astype(bool)
    df["alerta_similitud_sin_testigos"] = (sim > 0.7) & sin_testigos

    # Robo declarado sin denuncia policial previa
    robo = df.get("doc_robo", False).fillna(False).astype(bool)
    sin_denuncia = df.get("doc_sin_denuncia_previa", False).fillna(False).astype(bool)
    df["alerta_robo_sin_denuncia"] = robo & sin_denuncia

    # Proveedor en lista restrictiva con facturas fraudulentas
    prov_lista = df.get("proveedor_lista_restrictiva", False).fillna(False).astype(bool)
    factura_alterada = df.get("doc_factura_alterada", False).fillna(False).astype(bool)
    df["alerta_proveedor_fraude_documental"] = prov_lista & factura_alterada

    # Score documental crudo (0-100): suma ponderada de señales PDF
    # Pesos calibrados para el reto — se normalizarán en Phase 5
    score_doc = pd.Series(0.0, index=df.index)
    score_doc += df.get("doc_factura_alterada", False).fillna(False).astype(float) * 25
    score_doc += df.get("doc_ruc_invalido", False).fillna(False).astype(float) * 20
    score_doc += df.get("doc_caso_fraude", False).fillna(False).astype(float) * 30
    score_doc += df.get("doc_caso_inconsistente", False).fillna(False).astype(float) * 15
    score_doc += df.get("doc_sin_denuncia_previa", False).fillna(False).astype(float) * 15
    score_doc += df.get("doc_parte_tardio", False).fillna(False).astype(float) * 10
    score_doc += df.get("doc_sin_testigos", False).fillna(False).astype(float) * 8
    score_doc += df.get("doc_sin_intervencion", False).fillna(False).astype(float) * 5
    score_doc += df.get("doc_perdida_total", False).fillna(False).astype(float) * 5
    df["score_documental_raw"] = score_doc.clip(0, 100)

    return df


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def build_features(
    claims_path: str,
    docs_path: str,
    output_path: str,
) -> pd.DataFrame:
    """
    Cruza claims_master con documents_extracted, genera features combinadas
    y guarda claims_with_documents.csv.
    """
    claims = pd.read_csv(claims_path)
    docs   = pd.read_csv(docs_path)

    log.info(f"claims_master: {claims.shape}")
    log.info(f"documents_extracted: {docs.shape}")

    # Siniestros que tienen PDFs extraídos
    siniestros_con_pdf = docs["id_siniestro"].nunique()
    log.info(f"Siniestros con PDFs: {siniestros_con_pdf}")

    # Agregar señales documentales por siniestro
    doc_agg = _agg_docs(docs)
    log.info(f"doc_agg: {doc_agg.shape}")

    # Left join — siniestros sin PDF tendrán NaN en columnas doc_*
    merged = claims.merge(doc_agg, on="id_siniestro", how="left")

    # Rellenar booleanos doc_* con False para siniestros sin PDF
    bool_doc_cols = [c for c in merged.columns if c.startswith("doc_") and c != "doc_parte_tardio_dias"]
    for col in bool_doc_cols:
        if merged[col].dtype == object or merged[col].isna().any():
            try:
                merged[col] = merged[col].map(lambda x: bool(x) if pd.notna(x) else False)
            except Exception:
                pass

    merged["n_pdfs_extraidos"] = merged["n_pdfs_extraidos"].fillna(0).astype(int)
    merged["tipos_pdf"]        = merged["tipos_pdf"].fillna("")

    # Features combinadas
    merged = _add_combined_features(merged)

    log.info(f"claims_with_documents: {merged.shape}")

    # Guardar
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info(f"Guardado: {output_path}")

    return merged


def validate_features(df: pd.DataFrame) -> list[str]:
    """Validaciones básicas del dataset enriquecido."""
    issues = []

    if len(df) != 500:
        issues.append(f"Filas esperadas 500, encontradas {len(df)}")

    required = [
        "id_siniestro", "score_documental_raw",
        "doc_factura_alterada", "doc_ruc_invalido",
        "alerta_robo_sin_denuncia", "alerta_similitud_sin_testigos",
    ]
    for col in required:
        if col not in df.columns:
            issues.append(f"Columna faltante: {col}")

    siniestros_con_pdf = (df["n_pdfs_extraidos"] > 0).sum()
    if siniestros_con_pdf < 20:
        issues.append(f"Pocos siniestros con PDF: {siniestros_con_pdf}")

    return issues


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    claims_path = root / "data" / "processed" / "claims_master.csv"
    docs_path   = root / "data" / "processed" / "documents_extracted.csv"
    output_path = root / "data" / "processed" / "claims_with_documents.csv"

    df = build_features(str(claims_path), str(docs_path), str(output_path))

    issues = validate_features(df)
    if issues:
        print("\nValidación con advertencias:")
        for i in issues:
            print(f"  ⚠ {i}")
    else:
        print("\n✓ Validación OK")

    print(f"\n{'='*55}")
    print(f"  claims_with_documents: {len(df)} filas, {len(df.columns)} columnas")

    # Siniestros con señales documentales
    siniestros_pdf = df[df["n_pdfs_extraidos"] > 0]
    print(f"  Siniestros con PDFs: {len(siniestros_pdf)}")

    for col in ["doc_factura_alterada", "doc_ruc_invalido", "doc_caso_fraude",
                "doc_sin_denuncia_previa", "doc_parte_tardio",
                "alerta_robo_sin_denuncia", "alerta_proveedor_fraude_documental"]:
        if col in df.columns:
            n = df[col].sum() if df[col].dtype != object else (df[col] == True).sum()
            print(f"  {col}: {int(n)}")

    print(f"\n  Score documental (siniestros con PDF):")
    if len(siniestros_pdf) > 0:
        print(f"    media  = {siniestros_pdf['score_documental_raw'].mean():.1f}")
        print(f"    máximo = {siniestros_pdf['score_documental_raw'].max():.1f}")
        top = siniestros_pdf.nlargest(5, "score_documental_raw")[["id_siniestro", "score_documental_raw"]]
        for _, r in top.iterrows():
            print(f"    {r['id_siniestro']}: {r['score_documental_raw']:.0f}")
