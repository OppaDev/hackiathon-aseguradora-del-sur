"""
Fase 6 — Análisis de redes de relaciones (NetworkX).

Construye un grafo asegurado–proveedor–siniestro para detectar
patrones no evidentes: redes de fraude coordinado, proveedores
con clústeres sospechosos, asegurados conectados entre sí.

Nodos:
  - asegurado:  id_asegurado
  - proveedor:  id_proveedor
  - siniestro:  id_siniestro

Aristas:
  - asegurado → siniestro   (participa_en)
  - siniestro → proveedor   (atendido_por)

Anomalías detectadas:
  - Proveedor con >3 siniestros de alto riesgo
  - Asegurado con ≥3 siniestros en el grafo
  - Pares (asegurado, proveedor) con múltiples siniestros compartidos
  - Componentes conectados con mayoría de alertas CRÍTICO
"""

import networkx as nx
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Construcción del grafo
# ---------------------------------------------------------------------------

def build_relationship_graph(df: pd.DataFrame) -> nx.Graph:
    """
    Construye el grafo de relaciones a partir de claims_with_documents
    (o claims_scored si ya tiene score_riesgo).

    Nodos:
        Tipo 'asegurado', 'proveedor', 'siniestro' con atributos relevantes.
    Aristas:
        asegurado — siniestro — proveedor.
    """
    G = nx.Graph()

    for _, row in df.iterrows():
        sin_id  = row["id_siniestro"]
        ase_id  = row.get("id_asegurado", None)
        prov_id = row.get("id_proveedor", None)

        score   = float(row["score_riesgo"]) if "score_riesgo" in row and pd.notna(row["score_riesgo"]) else 0.0
        nivel   = str(row["nivel_riesgo"]) if "nivel_riesgo" in row else "BAJO"
        alerts  = str(row.get("rule_alerts", "") or "")

        # Nodo siniestro
        G.add_node(sin_id, tipo="siniestro", score=score, nivel=nivel,
                   ramo=str(row.get("ramo", "")),
                   cobertura=str(row.get("cobertura", "")),
                   monto=float(row.get("monto_reclamado", 0) or 0),
                   alerts=alerts)

        # Nodo asegurado
        if ase_id and pd.notna(ase_id):
            if ase_id not in G:
                G.add_node(ase_id, tipo="asegurado",
                           segmento=str(row.get("segmento", "")),
                           perfil=str(row.get("perfil_riesgo_historico", "")),
                           n_historico=int(row.get("n_reclamos_historico", 0) or 0))
            G.add_edge(ase_id, sin_id, tipo="participa_en", peso=1.0)

        # Nodo proveedor
        if prov_id and pd.notna(prov_id):
            if prov_id not in G:
                G.add_node(prov_id, tipo="proveedor",
                           nombre=str(row.get("nombre_proveedor", prov_id)),
                           en_lista=bool(row.get("proveedor_lista_restrictiva", False)),
                           tipo_prov=str(row.get("tipo_proveedor", "")))
            peso_arista = 2.0 if bool(row.get("proveedor_lista_restrictiva", False)) else 1.0
            G.add_edge(sin_id, prov_id, tipo="atendido_por", peso=peso_arista)

    log.info(f"Grafo construido: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    return G


# ---------------------------------------------------------------------------
# Detección de anomalías de red
# ---------------------------------------------------------------------------

def detect_network_anomalies(G: nx.Graph, df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta patrones sospechosos en el grafo y añade columnas de red al df.

    Columnas añadidas:
      - net_proveedor_alto_riesgo: el proveedor tiene ≥3 siniestros ALTO/MEDIO
      - net_asegurado_recurrente:  el asegurado tiene ≥3 siniestros en la red
      - net_par_concentrado:       mismo par (asegurado, proveedor) en ≥2 siniestros
      - net_score:                 score de riesgo de red (0-100)
      - net_componente_id:         ID del componente conectado
    """
    df = df.copy()

    # Centralidad de intermediación para siniestros (cuántos caminos pasan por ellos)
    try:
        betweenness = nx.betweenness_centrality(G, weight="peso")
    except Exception:
        betweenness = {n: 0.0 for n in G.nodes()}

    # Mapas de conteo por proveedor y por asegurado
    prov_siniestros: dict[str, list] = {}
    ase_siniestros:  dict[str, list] = {}

    for node, data in G.nodes(data=True):
        if data.get("tipo") == "siniestro":
            sin_id  = node
            nivel   = data.get("nivel", "BAJO")

            # Vecinos asegurado y proveedor
            for nb in G.neighbors(sin_id):
                nb_data = G.nodes[nb]
                if nb_data.get("tipo") == "proveedor":
                    prov_siniestros.setdefault(nb, []).append((sin_id, nivel))
                elif nb_data.get("tipo") == "asegurado":
                    ase_siniestros.setdefault(nb, []).append(sin_id)

    # Proveedores con muchos siniestros de riesgo
    prov_alto = {
        pv for pv, sins in prov_siniestros.items()
        if sum(1 for _, niv in sins if niv in ("ALTO", "MEDIO")) >= 3
    }

    # Asegurados recurrentes en la red
    ase_recurrente = {ase for ase, sins in ase_siniestros.items() if len(sins) >= 3}

    # Pares (asegurado, proveedor) concentrados — >1 siniestro compartido
    par_counts: dict[tuple, int] = {}
    for sin_id in G.nodes():
        if G.nodes[sin_id].get("tipo") != "siniestro":
            continue
        vecinos = list(G.neighbors(sin_id))
        ases  = [n for n in vecinos if G.nodes[n].get("tipo") == "asegurado"]
        provs = [n for n in vecinos if G.nodes[n].get("tipo") == "proveedor"]
        for a in ases:
            for p in provs:
                par_counts[(a, p)] = par_counts.get((a, p), 0) + 1

    pares_concentrados = {(a, p) for (a, p), cnt in par_counts.items() if cnt >= 2}

    # Componentes conectados
    componentes = {node: idx for idx, comp in enumerate(nx.connected_components(G))
                   for node in comp}

    # Añadir columnas al DataFrame
    net_prov_alto    = []
    net_ase_recur    = []
    net_par_conc     = []
    net_score        = []
    net_comp         = []

    for _, row in df.iterrows():
        sin_id  = row["id_siniestro"]
        ase_id  = row.get("id_asegurado", "")
        prov_id = row.get("id_proveedor", "")

        es_prov_alto  = prov_id in prov_alto
        es_ase_recur  = ase_id in ase_recurrente
        es_par_conc   = (ase_id, prov_id) in pares_concentrados

        # Score de red: suma ponderada de señales
        s_net = 0.0
        if es_prov_alto:  s_net += 30
        if es_ase_recur:  s_net += 25
        if es_par_conc:   s_net += 35
        # Centralidad normalizada (0-10 pts)
        btw = betweenness.get(sin_id, 0.0)
        s_net += min(btw * 1000, 10)

        net_prov_alto.append(es_prov_alto)
        net_ase_recur.append(es_ase_recur)
        net_par_conc.append(es_par_conc)
        net_score.append(min(s_net, 100))
        net_comp.append(componentes.get(sin_id, -1))

    df["net_proveedor_alto_riesgo"] = net_prov_alto
    df["net_asegurado_recurrente"]  = net_ase_recur
    df["net_par_concentrado"]       = net_par_conc
    df["net_score"]                 = net_score
    df["net_componente_id"]         = net_comp

    log.info(
        f"Red: {sum(net_prov_alto)} prov-alto | "
        f"{sum(net_ase_recur)} ase-recurrente | "
        f"{sum(net_par_conc)} pares-concentrados"
    )
    return df


# ---------------------------------------------------------------------------
# Exportación de aristas para visualización
# ---------------------------------------------------------------------------

def export_edges(G: nx.Graph, output_path: str) -> pd.DataFrame:
    """Exporta aristas del grafo a CSV para el dashboard."""
    rows = []
    for u, v, data in G.edges(data=True):
        rows.append({
            "origen":        u,
            "destino":       v,
            "tipo_relacion": data.get("tipo", ""),
            "peso":          data.get("peso", 1.0),
            "tipo_origen":   G.nodes[u].get("tipo", ""),
            "tipo_destino":  G.nodes[v].get("tipo", ""),
        })
    df_edges = pd.DataFrame(rows)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_edges.to_csv(output_path, index=False, encoding="utf-8-sig")
    log.info(f"Aristas exportadas: {output_path} ({len(df_edges)} filas)")
    return df_edges


def get_node_neighbors(G: nx.Graph, node_id: str) -> dict:
    """Devuelve vecinos directos de un nodo para el panel de detalle."""
    if node_id not in G:
        return {}
    neighbors = {}
    for nb in G.neighbors(node_id):
        nb_data = G.nodes[nb]
        neighbors[nb] = {
            "tipo": nb_data.get("tipo", ""),
            "score": nb_data.get("score", 0),
            "nivel": nb_data.get("nivel", ""),
        }
    return neighbors


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(
    claims_with_docs_path: str,
    scored_path: str,
    edges_output: str,
) -> tuple[nx.Graph, pd.DataFrame]:
    """
    Carga claims_with_documents (datos completos) y claims_scored (scores),
    construye el grafo, detecta anomalías y exporta aristas.
    """
    df_full   = pd.read_csv(claims_with_docs_path)
    df_scored = pd.read_csv(scored_path)

    # Unir scores al dataset completo
    score_cols = ["id_siniestro", "score_riesgo", "nivel_riesgo",
                  "recomendacion", "rule_alerts", "rule_critical_flags",
                  "rule_severity_max", "rule_n_critical"]
    score_cols = [c for c in score_cols if c in df_scored.columns]
    df = df_full.merge(df_scored[score_cols], on="id_siniestro", how="left")

    G  = build_relationship_graph(df)
    df = detect_network_anomalies(G, df)
    export_edges(G, edges_output)
    return G, df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    claims_path  = root / "data" / "processed" / "claims_with_documents.csv"
    scored_path  = root / "data" / "processed" / "claims_scored.csv"
    edges_output = root / "data" / "processed" / "network_edges.csv"

    G, df = run(str(claims_path), str(scored_path), str(edges_output))

    print(f"\n{'='*60}")
    print(f"  Nodos: {G.number_of_nodes()}")
    print(f"  Aristas: {G.number_of_edges()}")
    print(f"  Componentes conectados: {nx.number_connected_components(G)}")

    tipos = {}
    for _, d in G.nodes(data=True):
        t = d.get("tipo", "?")
        tipos[t] = tipos.get(t, 0) + 1
    for t, cnt in sorted(tipos.items()):
        print(f"    {t}: {cnt}")

    print(f"\n  Señales de red detectadas:")
    for col in ["net_proveedor_alto_riesgo", "net_asegurado_recurrente", "net_par_concentrado"]:
        if col in df.columns:
            n = df[col].sum()
            print(f"    {col}: {int(n)}")

    top_net = df.nlargest(5, "net_score")[["id_siniestro", "net_score", "net_par_concentrado"]]
    print(f"\n  Top 5 por score de red:")
    for _, r in top_net.iterrows():
        print(f"    {r['id_siniestro']}: net_score={r['net_score']:.0f}")
