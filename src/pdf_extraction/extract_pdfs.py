"""
Orquestador de extracción de PDFs.

Recorre las 3 carpetas de PDFs, detecta el tipo de documento por su nombre/carpeta,
extrae campos con el módulo correspondiente y genera documents_extracted.csv
"""

import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
import logging

from src.pdf_extraction.extract_facturas import extract_factura
from src.pdf_extraction.extract_partes_policiales import extract_parte_policial
from src.pdf_extraction.extract_declaraciones import extract_declaracion

log = logging.getLogger(__name__)

# Carpeta → función de extracción
EXTRACTORS = {
    "facturas":                extract_factura,
    "partes_policiales":       extract_parte_policial,
    "declaraciones_accidente": extract_declaracion,
}


def read_pdf_text(path: Path) -> str:
    """Extrae todo el texto de un PDF con PyMuPDF."""
    try:
        doc = fitz.open(str(path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        log.error(f"Error leyendo {path.name}: {e}")
        return ""


def extract_all_pdfs(pdfs_root: str) -> pd.DataFrame:
    """
    Recorre las carpetas bajo pdfs_root, extrae campos de cada PDF
    y devuelve un DataFrame con una fila por documento.
    """
    pdfs_root = Path(pdfs_root)
    records = []

    for folder_name, extractor_fn in EXTRACTORS.items():
        folder = pdfs_root / folder_name
        if not folder.exists():
            log.warning(f"Carpeta no encontrada: {folder}")
            continue

        pdfs = sorted(folder.glob("*.pdf"))
        log.info(f"{folder_name}: {len(pdfs)} PDF(s) encontrados")

        for pdf_path in pdfs:
            text = read_pdf_text(pdf_path)
            if not text.strip():
                log.warning(f"  PDF vacío o sin texto: {pdf_path.name}")
                continue

            record = extractor_fn(text, pdf_path.name)
            record["ruta_pdf"] = str(pdf_path)
            records.append(record)
            log.info(f"  ✓ {pdf_path.name} → SIN: {record.get('id_siniestro', '?')}")

    if not records:
        log.warning("No se extrajeron documentos")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    log.info(f"Total documentos extraídos: {len(df)}")
    return df


def save_documents(df: pd.DataFrame, output_path: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info(f"Guardado: {output_path} ({len(df)} filas)")


def run(pdfs_root: str, output_path: str) -> pd.DataFrame:
    """Pipeline completo: recorrer PDFs → extraer → guardar."""
    df = extract_all_pdfs(pdfs_root)
    if not df.empty:
        save_documents(df, output_path)
    return df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    pdfs_root = root / "data" / "raw" / "pdfs"
    output   = root / "data" / "processed" / "documents_extracted.csv"

    df = run(str(pdfs_root), str(output))

    if df.empty:
        print("No se generaron registros.")
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  Documentos extraídos: {len(df)}")
    print(f"  Columnas: {len(df.columns)}")
    print(f"{'='*55}")

    for tipo in df["tipo_documento"].unique():
        sub = df[df["tipo_documento"] == tipo]
        print(f"\n  [{tipo}] — {len(sub)} docs")
        print(f"    Siniestros: {sorted(sub['id_siniestro'].dropna().tolist())}")

    print(f"\n  Alertas detectadas:")
    for col in ["factura_alterada", "ruc_invalido", "sin_denuncia_previa",
                "sin_testigos", "perdida_total", "robo", "flagrancia"]:
        if col in df.columns:
            count = df[col].sum() if df[col].dtype == bool else (df[col] == True).sum()
            if count:
                print(f"    {col}: {int(count)}")

    if "parte_tardio_dias" in df.columns:
        tardios = df[df["parte_tardio_dias"].notna() & (df["parte_tardio_dias"] > 7)]
        print(f"    parte_tardio (>7 días): {len(tardios)}")
        for _, row in tardios.iterrows():
            print(f"      {row['id_siniestro']}: {int(row['parte_tardio_dias'])} días")
