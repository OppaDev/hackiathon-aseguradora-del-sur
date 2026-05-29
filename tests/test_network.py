"""
Tests para src/network/relationship_graph.py — usan datos reales.
"""

import pytest
import pandas as pd
import networkx as nx
from pathlib import Path

from src.network.relationship_graph import (
    build_relationship_graph,
    detect_network_anomalies,
    export_edges,
    get_node_neighbors,
    run,
)

ROOT        = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "data" / "processed" / "claims_with_documents.csv"
SCORED_PATH = ROOT / "data" / "processed" / "claims_scored.csv"
EDGES_PATH  = ROOT / "data" / "processed" / "network_edges.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df_merged() -> pd.DataFrame:
    df_full   = pd.read_csv(CLAIMS_PATH)
    df_scored = pd.read_csv(SCORED_PATH)
    score_cols = [c for c in ["id_siniestro", "score_riesgo", "nivel_riesgo",
                               "rule_alerts", "rule_severity_max"] if c in df_scored.columns]
    return df_full.merge(df_scored[score_cols], on="id_siniestro", how="left")


@pytest.fixture(scope="module")
def G(df_merged) -> nx.Graph:
    return build_relationship_graph(df_merged)


@pytest.fixture(scope="module")
def df_with_net(df_merged, G) -> pd.DataFrame:
    return detect_network_anomalies(G, df_merged)


# ---------------------------------------------------------------------------
# Estructura del grafo
# ---------------------------------------------------------------------------

class TestGrafoConstruccion:
    def test_nodos_siniestros(self, G):
        siniestros = [n for n, d in G.nodes(data=True) if d.get("tipo") == "siniestro"]
        assert len(siniestros) == 500

    def test_nodos_asegurados(self, G):
        asegurados = [n for n, d in G.nodes(data=True) if d.get("tipo") == "asegurado"]
        assert len(asegurados) == 174

    def test_nodos_proveedores(self, G):
        proveedores = [n for n, d in G.nodes(data=True) if d.get("tipo") == "proveedor"]
        assert len(proveedores) == 33

    def test_total_aristas(self, G):
        # 500 aristas asegurado→siniestro + 500 aristas siniestro→proveedor
        assert G.number_of_edges() == 1000

    def test_grafo_conectado(self, G):
        assert nx.is_connected(G)

    def test_siniestro_tiene_atributos(self, G):
        data = G.nodes["SIN-0005"]
        assert "tipo" in data
        assert data["tipo"] == "siniestro"

    def test_siniestro_conectado_a_asegurado(self, G):
        vecinos = list(G.neighbors("SIN-0005"))
        tipos = [G.nodes[n].get("tipo") for n in vecinos]
        assert "asegurado" in tipos

    def test_siniestro_conectado_a_proveedor(self, G):
        vecinos = list(G.neighbors("SIN-0005"))
        tipos = [G.nodes[n].get("tipo") for n in vecinos]
        assert "proveedor" in tipos


# ---------------------------------------------------------------------------
# Detección de anomalías
# ---------------------------------------------------------------------------

class TestDeteccionAnomalias:
    def test_columnas_net_presentes(self, df_with_net):
        for col in ["net_proveedor_alto_riesgo", "net_asegurado_recurrente",
                    "net_par_concentrado", "net_score", "net_componente_id"]:
            assert col in df_with_net.columns, f"Falta: {col}"

    def test_hay_proveedores_alto_riesgo(self, df_with_net):
        n = df_with_net["net_proveedor_alto_riesgo"].sum()
        assert n > 0

    def test_hay_asegurados_recurrentes(self, df_with_net):
        n = df_with_net["net_asegurado_recurrente"].sum()
        assert n > 0

    def test_hay_pares_concentrados(self, df_with_net):
        n = df_with_net["net_par_concentrado"].sum()
        assert n > 0

    def test_net_score_en_rango(self, df_with_net):
        assert (df_with_net["net_score"] >= 0).all()
        assert (df_with_net["net_score"] <= 100).all()

    def test_pares_tienen_score_alto(self, df_with_net):
        pares = df_with_net[df_with_net["net_par_concentrado"]]
        assert pares["net_score"].min() >= 30  # par concentrado = ≥35 puntos de red


# ---------------------------------------------------------------------------
# Exportación de aristas
# ---------------------------------------------------------------------------

class TestExportAristas:
    def test_csv_exportado(self, G):
        df_edges = export_edges(G, str(EDGES_PATH))
        assert EDGES_PATH.exists()
        assert len(df_edges) == 1000

    def test_columnas_aristas(self):
        df_edges = pd.read_csv(EDGES_PATH)
        for col in ["origen", "destino", "tipo_relacion", "peso",
                    "tipo_origen", "tipo_destino"]:
            assert col in df_edges.columns

    def test_tipos_relacion(self):
        df_edges = pd.read_csv(EDGES_PATH)
        tipos = set(df_edges["tipo_relacion"].unique())
        assert "participa_en" in tipos
        assert "atendido_por" in tipos


# ---------------------------------------------------------------------------
# Pipeline run
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_run_devuelve_grafo_y_df(self):
        G, df = run(str(CLAIMS_PATH), str(SCORED_PATH), str(EDGES_PATH))
        assert isinstance(G, nx.Graph)
        assert len(df) == 500

    def test_run_df_tiene_columnas_net(self):
        _, df = run(str(CLAIMS_PATH), str(SCORED_PATH), str(EDGES_PATH))
        assert "net_score" in df.columns


# ---------------------------------------------------------------------------
# get_node_neighbors
# ---------------------------------------------------------------------------

class TestGetNodeNeighbors:
    def test_vecinos_de_siniestro(self, G):
        vecinos = get_node_neighbors(G, "SIN-0005")
        assert len(vecinos) == 2  # 1 asegurado + 1 proveedor

    def test_nodo_inexistente(self, G):
        vecinos = get_node_neighbors(G, "SIN-9999")
        assert vecinos == {}
