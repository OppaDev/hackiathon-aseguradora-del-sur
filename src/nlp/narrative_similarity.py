"""
Fase 7 — NLP: similitud narrativa.

El dataset tiene 33 descripciones únicas compartidas por 500 siniestros
(dato real del dataset sintético del reto). La estrategia NLP se adapta:

1. TF-IDF sobre los 33 textos únicos → matriz de similitud entre plantillas
2. Por cada siniestro: frecuencia de su descripción en el portafolio
3. Señales: descripción muy frecuente (>10 usos) sugiere texto copiado/scripted
4. El campo `similitud_narrativa` del Excel es la fuente autoritativa de similitud;
   este módulo lo valida y agrega señales de frecuencia y clonación.

Columnas generadas (nlp_*):
  - nlp_freq_descripcion:   cuántos otros siniestros tienen el mismo texto exacto
  - nlp_descripcion_rara:   descripción aparece en ≤2 siniestros (no sospechosa)
  - nlp_descripcion_comun:  descripción aparece en ≥10 siniestros (texto scripted)
  - nlp_sim_entre_grupos:   similitud máxima del grupo de descripción con otro grupo
  - nlp_grupo_id:           ID del grupo de descripción (0..32)
  - nlp_cluster_fraude:     grupo al que pertenecen pares de grupos con alta similitud
  - nlp_score:              score NLP 0-100 basado en similitud_narrativa + frecuencia
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# Stop words español básico
STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "con", "una", "su", "para", "es", "al", "lo", "como", "más",
    "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "si", "sobre",
    "cuando", "también", "hasta", "hay", "desde", "te", "me", "sin",
    "entre", "muy", "así", "no", "que", "bien", "tanto", "ni", "era",
    "esto", "durante", "dentro", "hacia", "cada", "donde", "mientras",
}

UMBRAL_CLONADA  = 0.85
UMBRAL_SIMILAR  = 0.70
UMBRAL_FREQ_COMUN = 10    # descripción usada ≥10 veces → texto scripted


# ---------------------------------------------------------------------------
# Preprocesamiento
# ---------------------------------------------------------------------------

def _preprocess(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\sáéíóúüñ]", " ", text)
    tokens = [t for t in text.split() if t not in STOPWORDS_ES and len(t) > 2]
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# TF-IDF sobre grupos únicos de descripción
# ---------------------------------------------------------------------------

def compute_group_similarity(unique_texts: list[str]) -> np.ndarray:
    """
    Calcula la matriz de similitud coseno entre los textos únicos.

    Returns:
        np.ndarray (n_unique × n_unique), diagonal = 0.
    """
    preprocessed = [_preprocess(t) for t in unique_texts]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    try:
        tfidf_matrix = vectorizer.fit_transform(preprocessed)
        sim_matrix = cosine_similarity(tfidf_matrix)
    except ValueError:
        # Si todos los textos quedan vacíos tras preprocesar
        sim_matrix = np.eye(len(unique_texts))
    np.fill_diagonal(sim_matrix, 0.0)
    return sim_matrix


def build_group_pairs(
    unique_texts: list[str],
    sim_matrix: np.ndarray,
    threshold: float = UMBRAL_SIMILAR,
) -> pd.DataFrame:
    """DataFrame de pares de grupos de descripción con similitud >= threshold."""
    n = len(unique_texts)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim_matrix[i, j])
            if s >= threshold:
                pairs.append({
                    "grupo_a":   i,
                    "grupo_b":   j,
                    "texto_a":   unique_texts[i][:60],
                    "texto_b":   unique_texts[j][:60],
                    "similitud": round(s, 4),
                })
    return pd.DataFrame(pairs) if pairs else pd.DataFrame(
        columns=["grupo_a", "grupo_b", "texto_a", "texto_b", "similitud"]
    )


# ---------------------------------------------------------------------------
# Clústeres de narrativas fraudulentas
# ---------------------------------------------------------------------------

def _cluster_groups(n_groups: int, sim_matrix: np.ndarray) -> dict[int, int]:
    """
    Asigna clúster a cada grupo usando componentes conectados (similitud >= umbral).
    Grupos sin conexión → cluster_id = -1.
    """
    try:
        import networkx as nx
        G = nx.Graph()
        G.add_nodes_from(range(n_groups))
        for i in range(n_groups):
            for j in range(i + 1, n_groups):
                if sim_matrix[i, j] >= UMBRAL_SIMILAR:
                    G.add_edge(i, j)
        idx_to_cluster = {}
        cluster_id = 0
        for comp in nx.connected_components(G):
            if len(comp) > 1:
                for node in comp:
                    idx_to_cluster[node] = cluster_id
                cluster_id += 1
        return idx_to_cluster
    except ImportError:
        return {}


# ---------------------------------------------------------------------------
# Enriquecimiento del DataFrame
# ---------------------------------------------------------------------------

def enrich_with_nlp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade columnas nlp_* al DataFrame a partir de `descripcion`
    y del campo `similitud_narrativa` del Excel.
    """
    df = df.copy()

    # Frecuencia de cada descripción
    freq_map = df["descripcion"].value_counts().to_dict()
    df["nlp_freq_descripcion"] = df["descripcion"].map(freq_map).fillna(0).astype(int)

    # Señales de frecuencia
    df["nlp_descripcion_rara"]  = df["nlp_freq_descripcion"] <= 2
    df["nlp_descripcion_comun"] = df["nlp_freq_descripcion"] >= UMBRAL_FREQ_COMUN

    # Grupos de descripción
    unique_texts = df["descripcion"].unique().tolist()
    text_to_group = {t: i for i, t in enumerate(unique_texts)}
    df["nlp_grupo_id"] = df["descripcion"].map(text_to_group)

    # Similitud entre grupos
    sim_matrix = compute_group_similarity(unique_texts)
    group_max_sim = {i: float(sim_matrix[i].max()) for i in range(len(unique_texts))}
    df["nlp_sim_entre_grupos"] = df["nlp_grupo_id"].map(group_max_sim).round(4)

    # Clústeres de grupos similares
    cluster_map = _cluster_groups(len(unique_texts), sim_matrix)
    df["nlp_cluster_fraude"] = df["nlp_grupo_id"].map(
        lambda g: cluster_map.get(g, -1)
    )

    # Score NLP (0-100):
    # 70% viene de similitud_narrativa del Excel (campo ya validado en el portafolio)
    # 30% viene de la frecuencia de la descripción normalizada
    sim_excel = pd.to_numeric(df.get("similitud_narrativa", 0), errors="coerce").fillna(0)
    freq_norm = (df["nlp_freq_descripcion"] / df["nlp_freq_descripcion"].max()).clip(0, 1)
    df["nlp_score"] = (sim_excel * 70 + freq_norm * 30).clip(0, 100).round(1)

    # Comparación con Excel
    df["nlp_valida_excel"] = (
        (sim_excel >= UMBRAL_CLONADA) == df["nlp_descripcion_comun"]
    )

    log.info(
        f"NLP enriquecido: {df['nlp_descripcion_rara'].sum()} raras | "
        f"{df['nlp_descripcion_comun'].sum()} comunes | "
        f"{(df['nlp_cluster_fraude'] >= 0).sum()} en clústeres"
    )
    return df


def get_similar_claims(
    id_siniestro: str,
    df: pd.DataFrame,
    top_n: int = 5,
) -> list[dict]:
    """
    Devuelve siniestros con la misma descripción o descripción similar.
    Útil para el panel de detalle en el dashboard.
    """
    if id_siniestro not in df["id_siniestro"].values:
        return []

    row = df[df["id_siniestro"] == id_siniestro].iloc[0]
    desc    = row["descripcion"]
    grupo   = row["nlp_grupo_id"]
    cluster = row["nlp_cluster_fraude"]

    # 1. Misma descripción exacta (excluyendo el propio)
    mismos = df[
        (df["descripcion"] == desc) & (df["id_siniestro"] != id_siniestro)
    ]["id_siniestro"].tolist()[:top_n]

    # 2. Si hay cluster, incluir otros del mismo cluster
    if cluster >= 0 and len(mismos) < top_n:
        otros_cluster = df[
            (df["nlp_cluster_fraude"] == cluster) &
            (df["descripcion"] != desc) &
            (df["id_siniestro"] != id_siniestro)
        ]["id_siniestro"].tolist()[: top_n - len(mismos)]
        mismos.extend(otros_cluster)

    return [
        {"id_siniestro": sid, "tipo": "misma_descripcion" if i < len(
            df[(df["descripcion"] == desc) & (df["id_siniestro"] != id_siniestro)]
        ) else "descripcion_similar"}
        for i, sid in enumerate(mismos[:top_n])
    ]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(
    claims_path: str,
    output_enriched: Optional[str] = None,
    output_pairs: Optional[str] = None,
) -> pd.DataFrame:
    """Carga, enriquece y guarda el DataFrame con señales NLP."""
    df = pd.read_csv(claims_path)
    df = enrich_with_nlp(df)

    if output_enriched:
        Path(output_enriched).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_enriched, index=False, encoding="utf-8-sig")
        log.info(f"Guardado: {output_enriched}")

    if output_pairs:
        unique_texts = df["descripcion"].unique().tolist()
        sim_matrix   = compute_group_similarity(unique_texts)
        df_pairs     = build_group_pairs(unique_texts, sim_matrix)
        Path(output_pairs).parent.mkdir(parents=True, exist_ok=True)
        df_pairs.to_csv(output_pairs, index=False, encoding="utf-8-sig")
        log.info(f"Pares de grupos similares: {output_pairs} ({len(df_pairs)} filas)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(__file__).resolve().parents[2]
    claims_path   = root / "data" / "processed" / "claims_with_documents.csv"
    output_enrich = root / "data" / "processed" / "claims_nlp.csv"
    output_pairs  = root / "data" / "processed" / "similarity_pairs.csv"

    df = run(str(claims_path), str(output_enrich), str(output_pairs))

    print(f"\n{'='*60}")
    print(f"  Siniestros: {len(df)} | Descripciones únicas: {df['descripcion'].nunique()}")
    print(f"\n  Señales NLP:")
    print(f"    Raras (≤2 usos):    {df['nlp_descripcion_rara'].sum()}")
    print(f"    Comunes (≥10 usos): {df['nlp_descripcion_comun'].sum()}")
    print(f"    En clústeres sim.:  {(df['nlp_cluster_fraude'] >= 0).sum()}")

    print(f"\n  Top 5 grupos por frecuencia:")
    top_grupos = (
        df.groupby("descripcion")["id_siniestro"]
        .count()
        .nlargest(5)
        .reset_index()
    )
    top_grupos.columns = ["descripcion", "frecuencia"]
    for _, r in top_grupos.iterrows():
        print(f"    [{r['frecuencia']:3d}x] {r['descripcion'][:55]}")

    print(f"\n  Score NLP (media):  {df['nlp_score'].mean():.1f}")
    print(f"  Score NLP (máx):    {df['nlp_score'].max():.1f}")
    print(f"\n  Top 5 por nlp_score:")
    for _, r in df.nlargest(5, "nlp_score")[["id_siniestro", "nlp_score", "nlp_freq_descripcion"]].iterrows():
        print(f"    {r['id_siniestro']}: {r['nlp_score']:.1f} (freq={r['nlp_freq_descripcion']})")
