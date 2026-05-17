"""
transformer.py — claude-mem → graphify

Lit les observations de claude-mem.db et les injecte comme noeuds
dans graph.json, sans doublons, tous projets confondus.

Usage :
  python transformer.py           # dry-run (affiche ce qui serait ajouté)
  python transformer.py --write   # écrit dans graph.json
"""

import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

DB_PATH    = Path(r"C:\Users\bensa\.claude-mem\claude-mem.db")
GRAPH_PATH = Path(r"G:\Mon Drive\10 - Claude\vault\2 - CONCEPTS\graphify-out\graph.json")


def make_id(title: str) -> str:
    """Empreinte unique d'un titre — même titre = même id = pas de doublon."""
    return "mem-" + hashlib.md5(title.strip().lower().encode()).hexdigest()[:12]


def obs_to_node(obs: dict) -> dict:
    """Convertit une observation claude-mem en noeud graphify."""
    title   = obs.get("title", "").strip()
    project = obs.get("project") or "unknown"
    return {
        "id":              make_id(title),
        "label":           title,
        "source_file":     obs.get("source_file") or f"claude-mem/{project}",
        "source_url":      None,
        "file_type":       "memory",
        "captured_at":     datetime.utcnow().isoformat(),
        "author":          "claude-mem",
        "contributor":     None,
        "rationale":       f"Observation capturee automatiquement depuis le projet '{project}'",
        "community":       None,
        "norm_label":      title.lower().strip(),
    }


def merge_into_graph(graph: dict, observations: list[dict]) -> dict:
    """
    Ajoute les observations dans le graphe sans doublons.
    Un noeud existant (meme id) est ignore silencieusement.
    """
    existing_ids = {n["id"] for n in graph.get("nodes", [])}
    added = 0
    for obs in observations:
        title = (obs.get("title") or "").strip()
        if not title:
            continue
        node = obs_to_node(obs)
        if node["id"] not in existing_ids:
            graph["nodes"].append(node)
            existing_ids.add(node["id"])
            added += 1
    if added:
        print(f"  + {added} nouveaux noeuds ajoutes")
    else:
        print("  Aucun nouveau noeud (tout est deja dans le graphe)")
    return graph


def slug_to_label(slug: str) -> str:
    """'algebre-coran-epistemologie' → 'Algebre Coran Epistemologie'"""
    return " ".join(word.capitalize() for word in slug.replace("-", " ").replace("_", " ").split())


def load_vault_conversations(vault_path) -> list[dict]:
    """Lit les .md de 1 - CONVERSATIONS et les convertit en observations."""
    vault_path = Path(vault_path)
    result = []
    for md in vault_path.rglob("*.md"):
        slug  = md.stem.replace("-raw", "")
        title = slug_to_label(slug)
        result.append({
            "title":        title,
            "project":      "vault/conversations",
            "content_hash": None,
            "source_file":  f"vault/conversations/{md.name}",
        })
    return result


def load_observations() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT title, project, content_hash FROM observations "
        "WHERE title IS NOT NULL AND title != ''"
    ).fetchall()
    conn.close()
    return [{"title": r[0], "project": r[1], "content_hash": r[2]} for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Ecrire dans graph.json")
    args = parser.parse_args()

    print(f"\nSource  : {DB_PATH}")
    print(f"Cible   : {GRAPH_PATH}")

    observations = load_observations()
    print(f"\n{len(observations)} observations lues depuis claude-mem")

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    before = len(graph["nodes"])
    print(f"{before} noeuds existants dans graph.json")

    graph = merge_into_graph(graph, observations)
    after = len(graph["nodes"])

    print(f"\nResultat : {before} -> {after} noeuds (+{after - before})")

    if args.write:
        GRAPH_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"graph.json mis a jour.")
    else:
        print("Dry-run — rien n'a ete ecrit. Lance avec --write pour appliquer.")


if __name__ == "__main__":
    main()
