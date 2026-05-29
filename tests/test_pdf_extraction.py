"""
Tests para src/pdf_extraction/ — usan los PDFs reales del dataset.
"""

import pytest
from pathlib import Path
import fitz

from src.pdf_extraction.extract_facturas import extract_factura
from src.pdf_extraction.extract_partes_policiales import extract_parte_policial, _dias_entre
from src.pdf_extraction.extract_declaraciones import extract_declaracion
from src.pdf_extraction.extract_pdfs import read_pdf_text, extract_all_pdfs

ROOT = Path(__file__).resolve().parents[1]
PDFS = ROOT / "data" / "raw" / "pdfs"

FACTURA_SIN0001  = PDFS / "facturas" / "Muestras_Facturas_Siniestros- SIN-0001.pdf"
FACTURA_SIN0005  = PDFS / "facturas" / "Muestras_Facturas_Siniestros-SIN-0005.pdf"
FACTURA_SIN0022  = PDFS / "facturas" / "Muestras_Facturas_Siniestros-SIN-0022.pdf"
PARTE_SIN0005    = PDFS / "partes_policiales" / "PP_SIN-0005_DOC-0012.pdf"
PARTE_SIN0040    = PDFS / "partes_policiales" / "PP_SIN-0040_DOC-0097.pdf"
PARTE_SIN0344    = PDFS / "partes_policiales" / "PP_SIN-0344_DOC-0862.pdf"
DECL_SIN0378     = PDFS / "declaraciones_accidente" / "DA_SIN-0378_DOC-0952.pdf"
DECL_SIN0448     = PDFS / "declaraciones_accidente" / "DA_SIN-0448_DOC-1123.pdf"


def _text(path: Path) -> str:
    return read_pdf_text(path)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def test_dias_entre_positivo():
    assert _dias_entre("2026-03-22", "2026-03-17") == 5

def test_dias_entre_nulo():
    assert _dias_entre(None, "2026-03-17") is None

def test_dias_entre_mismo_dia():
    assert _dias_entre("2026-03-17", "2026-03-17") == 0


# ---------------------------------------------------------------------------
# Facturas — SIN-0001 (legítimo, sin alertas)
# ---------------------------------------------------------------------------

class TestFacturaSin0001:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_factura(_text(FACTURA_SIN0001), FACTURA_SIN0001.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0001"

    def test_proveedor(self):
        assert "MULTISERVICIOS" in self.r["proveedor"]

    def test_ruc_valido(self):
        assert self.r["ruc_invalido"] is False

    def test_total(self):
        assert self.r["total"] == 5528.0

    def test_sin_alerta_alterada(self):
        assert self.r["factura_alterada"] is False

    def test_caso_legitimo(self):
        assert self.r["caso_marcado"] == "Legítimo"


# ---------------------------------------------------------------------------
# Facturas — SIN-0005 (fraude: RUC inválido + documento alterado)
# ---------------------------------------------------------------------------

class TestFacturaSin0005:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_factura(_text(FACTURA_SIN0005), FACTURA_SIN0005.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0005"

    def test_ruc_invalido(self):
        assert self.r["ruc_invalido"] is True

    def test_factura_alterada(self):
        assert self.r["factura_alterada"] is True

    def test_caso_fraude(self):
        assert self.r["caso_marcado"] == "Fraude"

    def test_total_positivo(self):
        assert self.r["total"] > 0


# ---------------------------------------------------------------------------
# Facturas — SIN-0022 (proveedor con nombre en 2 líneas)
# ---------------------------------------------------------------------------

class TestFacturaSin0022:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_factura(_text(FACTURA_SIN0022), FACTURA_SIN0022.name)

    def test_proveedor_completo(self):
        # Nombre ocupa 2 líneas — debe concatenarse
        assert "TALLER NO REGISTRADO" in self.r["proveedor"]

    def test_ruc_invalido(self):
        assert self.r["ruc_invalido"] is True

    def test_factura_alterada(self):
        assert self.r["factura_alterada"] is True


# ---------------------------------------------------------------------------
# Partes Policiales — SIN-0005 (robo, sin denuncia previa, parte en 5 días)
# ---------------------------------------------------------------------------

class TestParteSin0005:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_parte_policial(_text(PARTE_SIN0005), PARTE_SIN0005.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0005"

    def test_id_documento(self):
        assert self.r["id_documento"] == "DOC-0012"

    def test_fechas(self):
        assert self.r["fecha_hecho"] == "2026-03-17"
        assert self.r["fecha_elaboracion"] == "2026-03-22"

    def test_parte_tardio_dias(self):
        assert self.r["parte_tardio_dias"] == 5

    def test_robo(self):
        assert self.r["robo"] is True

    def test_sin_denuncia_previa(self):
        assert self.r["sin_denuncia_previa"] is True

    def test_perdida_total(self):
        assert self.r["perdida_total"] is True

    def test_flagrancia_false(self):
        assert self.r["flagrancia"] is False


# ---------------------------------------------------------------------------
# Partes Policiales — SIN-0040 (choque, flagrancia, lesionados)
# ---------------------------------------------------------------------------

class TestParteSin0040:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_parte_policial(_text(PARTE_SIN0040), PARTE_SIN0040.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0040"

    def test_no_robo(self):
        assert self.r["robo"] is False

    def test_flagrancia_true(self):
        assert self.r["flagrancia"] is True

    def test_lesionados(self):
        assert self.r["lesionados"] is True

    def test_detenidos(self):
        assert self.r["detenidos"] is True

    def test_parte_no_tardio(self):
        assert self.r["parte_tardio_dias"] == 3


# ---------------------------------------------------------------------------
# Partes Policiales — SIN-0344 (parte tardío 11 días)
# ---------------------------------------------------------------------------

class TestParteSin0344:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_parte_policial(_text(PARTE_SIN0344), PARTE_SIN0344.name)

    def test_parte_tardio_11_dias(self):
        assert self.r["parte_tardio_dias"] == 11

    def test_perdida_total(self):
        assert self.r["perdida_total"] is True


# ---------------------------------------------------------------------------
# Declaraciones — SIN-0378 (tercero identificado, legítimo)
# ---------------------------------------------------------------------------

class TestDeclSin0378:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_declaracion(_text(DECL_SIN0378), DECL_SIN0378.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0378"

    def test_id_documento(self):
        assert self.r["id_documento"] == "DOC-0952"

    def test_placa(self):
        assert self.r["placa"] == "PIC-5519"

    def test_fecha(self):
        assert self.r["fecha_accidente"] == "15-01-2025"

    def test_hora(self):
        assert self.r["hora_accidente"] == "07:10"

    def test_tercero_identificado(self):
        assert self.r["tercero_identificado"] is True

    def test_sin_lesionados(self):
        assert self.r["lesionados"] is False


# ---------------------------------------------------------------------------
# Declaraciones — SIN-0448 (madrugada, sin tercero, lesionados)
# ---------------------------------------------------------------------------

class TestDeclSin0448:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.r = extract_declaracion(_text(DECL_SIN0448), DECL_SIN0448.name)

    def test_id_siniestro(self):
        assert self.r["id_siniestro"] == "SIN-0448"

    def test_hora_madrugada(self):
        assert self.r["hora_accidente"] == "02:30"

    def test_tercero_no_identificado(self):
        assert self.r["tercero_identificado"] is False

    def test_sin_testigos(self):
        assert self.r["sin_testigos"] is True

    def test_lesionados(self):
        assert self.r["lesionados"] is True


# ---------------------------------------------------------------------------
# Integración: orquestador con los 26 PDFs reales
# ---------------------------------------------------------------------------

class TestExtractAllPdfs:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = extract_all_pdfs(str(PDFS))

    def test_total_documentos(self):
        assert len(self.df) == 26

    def test_tipos_presentes(self):
        tipos = set(self.df["tipo_documento"].unique())
        assert "Factura" in tipos
        assert "Parte Policial" in tipos
        assert "Declaración Accidente" in tipos

    def test_facturas_count(self):
        assert len(self.df[self.df["tipo_documento"] == "Factura"]) == 15

    def test_partes_count(self):
        assert len(self.df[self.df["tipo_documento"] == "Parte Policial"]) == 6

    def test_declaraciones_count(self):
        assert len(self.df[self.df["tipo_documento"] == "Declaración Accidente"]) == 5

    def test_alertas_factura_alterada(self):
        alteradas = self.df[self.df["factura_alterada"] == True]
        assert len(alteradas) >= 4  # SIN-0004, 0005, 0006, 0009, 0022

    def test_alertas_ruc_invalido(self):
        invalidos = self.df[self.df["ruc_invalido"] == True]
        assert len(invalidos) == 5

    def test_partes_tardios(self):
        tardios = self.df[
            self.df["parte_tardio_dias"].notna() &
            (self.df["parte_tardio_dias"] > 7)
        ]
        assert len(tardios) == 4  # SIN-0022(17), SIN-0120(13), SIN-0217(12), SIN-0344(11)

    def test_todos_tienen_id_siniestro(self):
        assert self.df["id_siniestro"].notna().all()
