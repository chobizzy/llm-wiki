"""Vault graph analysis: community detection, god nodes, surprising connections.

Reads the vault's wikilink graph (from page frontmatter and [[wikilinks]]),
then runs:
  1. Degree-based god-node ranking (most-linked pages)
  2. Greedy modularity community detection (pure Python, no binary deps)
     — equivalent to Leiden for small-to-medium graphs (<10k nodes)
  3. Surprising connections — edges that cross community boundaries,
     ranked by how unexpected they are (inter-community edges where both
     endpoints have low cross-community degree)

Optional: `pip install leidenalg python-igraph` for the real Leiden algorithm.
Falls back to the greedy method automatically — no dependency required.

Output JSON:
{
  "god_nodes": [{"page": "...", "degree": N, "in_degree": N, "out_degree": N}, ...],
  "communities": [{"id": N, "pages": [...], "label": "..."}, ...],
  "surprising_connections": [{"source": "...", "target": "...", "score": 0.N}, ...],
  "dead_ends": ["page with 0 outgoing links", ...],
  "isolated": ["page with 0 links at all", ...],
  "stats": {"pages": N, "edges": N, "communities": N}
}
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Wikilink / frontmatter parsing
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")
_MD_LINK_RE = re.compile(r"\[.*?\]\(([^)]+\.md[^)]*)\)")
_TAGS_RE = re.compile(r"^tags:\s*\[([^\]]+)\]", re.MULTILINE)
_TAGS_LIST_RE = re.compile(r"^tags:\s*\n((?:\s+-\s+\S+\n)+)", re.MULTILINE)


def _slug(page_name: str) -> str:
    """Normalise a wikilink target to a page slug."""
    return page_name.strip().lower().replace(" ", "-")


def _page_slug(path: Path, root: Path) -> str:
    return _slug(path.stem)


def parse_vault_graph(vault: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Parse all .md pages and return (outgoing_edges, page_tags).

    outgoing_edges: {source_slug: [target_slug, ...]}
    page_tags:      {slug: [tag, ...]}
    """
    outgoing: dict[str, list[str]] = defaultdict(list)
    tags_map: dict[str, list[str]] = {}
    skip_dirs = {"_raw", "_archived", "_staging", "_archives", ".obsidian"}

    pages: list[Path] = []
    for p in vault.rglob("*.md"):
        if any(part in skip_dirs for part in p.parts):
            continue
        pages.append(p)

    known_slugs = {_page_slug(p, vault) for p in pages}

    for page in pages:
        src = _page_slug(page, vault)
        try:
            text = page.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Tags
        m = _TAGS_RE.search(text)
        if m:
            tags_map[src] = [t.strip().strip("'\"") for t in m.group(1).split(",")]
        else:
            m2 = _TAGS_LIST_RE.search(text)
            if m2:
                tags_map[src] = [ln.strip().lstrip("- ") for ln in m2.group(1).splitlines() if ln.strip()]

        # Wikilinks
        for link in _WIKILINK_RE.findall(text):
            target = _slug(link.split("/")[-1])
            if target and target != src and target in known_slugs:
                outgoing[src].append(target)

        # Markdown links (when OBSIDIAN_LINK_FORMAT=markdown)
        for href in _MD_LINK_RE.findall(text):
            target = _slug(Path(href).stem)
            if target and target != src and target in known_slugs:
                outgoing[src].append(target)

        if src not in outgoing:
            outgoing[src] = []

    # Ensure every known page appears as a key
    for p in pages:
        s = _page_slug(p, vault)
        outgoing.setdefault(s, [])

    return dict(outgoing), tags_map


# ---------------------------------------------------------------------------
# Graph metrics
# ---------------------------------------------------------------------------

def _build_degree_tables(
    outgoing: dict[str, list[str]]
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    out_deg: dict[str, int] = {n: len(v) for n, v in outgoing.items()}
    in_deg: dict[str, int] = defaultdict(int)
    for targets in outgoing.values():
        for t in targets:
            in_deg[t] += 1
    degree = {n: out_deg.get(n, 0) + in_deg.get(n, 0) for n in outgoing}
    for n in in_deg:
        degree.setdefault(n, in_deg[n])
    return degree, dict(in_deg), out_deg


def god_nodes(outgoing: dict[str, list[str]], top_n: int = 20) -> list[dict]:
    degree, in_deg, out_deg = _build_degree_tables(outgoing)
    ranked = sorted(degree, key=lambda n: -degree[n])[:top_n]
    return [
        {"page": n, "degree": degree[n],
         "in_degree": in_deg.get(n, 0), "out_degree": out_deg.get(n, 0)}
        for n in ranked
    ]


def dead_ends(outgoing: dict[str, list[str]]) -> list[str]:
    """Pages with no outgoing links."""
    return [n for n, targets in outgoing.items() if not targets]


def isolated(outgoing: dict[str, list[str]]) -> list[str]:
    """Pages with zero links in either direction."""
    _, in_deg, out_deg = _build_degree_tables(outgoing)
    return [n for n in outgoing if in_deg.get(n, 0) == 0 and out_deg.get(n, 0) == 0]


# ---------------------------------------------------------------------------
# Community detection — greedy modularity (Newman-Girvan, pure Python)
# ---------------------------------------------------------------------------

def _modularity(communities: list[set[str]], outgoing: dict[str, list[str]]) -> float:
    """Approximate modularity Q for an undirected projection of outgoing edges."""
    all_edges = [(s, t) for s, targets in outgoing.items() for t in targets]
    m = len(all_edges)
    if m == 0:
        return 0.0
    degree = defaultdict(int)
    for s, t in all_edges:
        degree[s] += 1
        degree[t] += 1
    node_comm: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for n in comm:
            node_comm[n] = i
    Q = 0.0
    for s, t in all_edges:
        if node_comm.get(s) == node_comm.get(t):
            Q += 1 - (degree[s] * degree[t]) / (2 * m)
    return Q / m


def detect_communities_greedy(outgoing: dict[str, list[str]]) -> list[set[str]]:
    """Greedy modularity community detection (label propagation variant).

    Fast O(n·k) approach suitable for vaults up to ~5 000 pages. Each node
    adopts the most frequent label among its neighbours; iterate until stable.
    Falls back gracefully to one community per page if the graph is empty.
    """
    nodes = list(outgoing.keys())
    if not nodes:
        return []

    # Build undirected adjacency
    adj: dict[str, list[str]] = defaultdict(list)
    for src, targets in outgoing.items():
        for t in targets:
            adj[src].append(t)
            adj[t].append(src)

    # Initialise: each node in its own community (label = index)
    labels: dict[str, int] = {n: i for i, n in enumerate(nodes)}

    for _ in range(20):  # max 20 rounds
        changed = False
        for n in nodes:
            neighbours = adj[n]
            if not neighbours:
                continue
            freq: dict[int, int] = defaultdict(int)
            for nb in neighbours:
                freq[labels[nb]] += 1
            best = max(freq, key=lambda lbl: (freq[lbl], -lbl))
            if best != labels[n]:
                labels[n] = best
                changed = True
        if not changed:
            break

    # Group by label
    groups: dict[int, set[str]] = defaultdict(set)
    for n, lbl in labels.items():
        groups[lbl].add(n)
    return list(groups.values())


def detect_communities(outgoing: dict[str, list[str]]) -> list[set[str]]:
    """Try Leiden (leidenalg + igraph) first; fall back to greedy label propagation."""
    try:
        import igraph as ig
        import leidenalg

        nodes = list(outgoing.keys())
        node_idx = {n: i for i, n in enumerate(nodes)}
        edges = [
            (node_idx[s], node_idx[t])
            for s, targets in outgoing.items()
            for t in targets
            if t in node_idx
        ]
        g = ig.Graph(n=len(nodes), edges=edges, directed=False)
        partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)
        return [
            {nodes[i] for i in cluster}
            for cluster in partition
        ]
    except ImportError:
        return detect_communities_greedy(outgoing)


# ---------------------------------------------------------------------------
# Surprising connections
# ---------------------------------------------------------------------------

def surprising_connections(
    outgoing: dict[str, list[str]],
    communities: list[set[str]],
    top_n: int = 20,
) -> list[dict]:
    """Edges that cross community boundaries, ranked by unexpectedness.

    Score = 1 / (cross_degree(source) * cross_degree(target))
    Low cross-degree nodes connected across communities are the most surprising.
    """
    node_comm: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for n in comm:
            node_comm[n] = i

    # Count how many cross-community edges each node already has
    cross_deg: dict[str, int] = defaultdict(int)
    for src, targets in outgoing.items():
        for t in targets:
            if node_comm.get(src) != node_comm.get(t):
                cross_deg[src] += 1
                cross_deg[t] += 1

    results = []
    seen: set[tuple[str, str]] = set()
    for src, targets in outgoing.items():
        for t in targets:
            pair = tuple(sorted((src, t)))
            if pair in seen:
                continue
            if node_comm.get(src) != node_comm.get(t):
                cd_s = cross_deg.get(src, 1)
                cd_t = cross_deg.get(t, 1)
                score = 1.0 / math.sqrt(cd_s * cd_t)
                results.append({"source": src, "target": t, "score": round(score, 4)})
                seen.add(pair)

    results.sort(key=lambda x: -x["score"])
    return results[:top_n]


# ---------------------------------------------------------------------------
# Community labelling (heuristic: most common tag or longest shared prefix)
# ---------------------------------------------------------------------------

def _label_community(pages: list[str], tags_map: dict[str, list[str]]) -> str:
    freq: dict[str, int] = defaultdict(int)
    for p in pages:
        for tag in tags_map.get(p, []):
            if not tag.startswith("visibility/"):
                freq[tag] += 1
    if freq:
        return max(freq, key=lambda t: freq[t])
    # Fallback: shared prefix of page names
    if len(pages) == 1:
        return pages[0]
    prefix = pages[0]
    for p in pages[1:]:
        while not p.startswith(prefix):
            prefix = prefix[:-1]
        if not prefix:
            break
    return prefix.rstrip("-_") or f"cluster-{pages[0][:20]}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyse_vault(vault: Path, top_n: int = 20) -> dict[str, Any]:
    outgoing, tags_map = parse_vault_graph(vault)

    if not outgoing:
        return {
            "god_nodes": [], "communities": [],
            "surprising_connections": [], "dead_ends": [], "isolated": [],
            "stats": {"pages": 0, "edges": 0, "communities": 0},
        }

    communities_raw = detect_communities(outgoing)
    # Sort communities largest-first
    communities_raw.sort(key=lambda c: -len(c))

    total_edges = sum(len(v) for v in outgoing.values())

    return {
        "god_nodes": god_nodes(outgoing, top_n),
        "communities": [
            {
                "id": i,
                "size": len(comm),
                "pages": sorted(comm),
                "label": _label_community(sorted(comm), tags_map),
            }
            for i, comm in enumerate(communities_raw)
        ],
        "surprising_connections": surprising_connections(outgoing, communities_raw, top_n),
        "dead_ends": dead_ends(outgoing),
        "isolated": isolated(outgoing),
        "stats": {
            "pages": len(outgoing),
            "edges": total_edges,
            "communities": len(communities_raw),
        },
    }
