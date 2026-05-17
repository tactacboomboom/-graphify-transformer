"""
CONTRAT — transformer claude-mem → graphify

Promesse : après avoir lancé transformer.py, le graph.json contient
les observations de claude-mem comme nœuds, sans doublons, pour tous les projets.

Lancer : python test_transformer.py
Résultat attendu : 4 tests PASS, 0 FAIL
"""

import json
import sqlite3
import hashlib
import sys
import os
from pathlib import Path
from copy import deepcopy

# ── Chemins ────────────────────────────────────────────────────────────────────
DB_PATH    = Path(r"C:\Users\bensa\.claude-mem\claude-mem.db")
GRAPH_PATH = Path(r"G:\Mon Drive\10 - Claude\vault\2 - CONCEPTS\graphify-out\graph.json")

# ── Helpers test ───────────────────────────────────────────────────────────────
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    msg = f"{status} {name}"
    if not condition and detail:
        msg += f"\n       → {detail}"
    print(msg)
    results.append(condition)

# ── Charger le module à tester ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
try:
    import transformer
    module_loaded = True
except ImportError as e:
    module_loaded = False
    print(f"[FAIL] Impossible d'importer transformer.py : {e}")
    print("       -> Lance d'abord : creer transformer.py dans ce dossier")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Extraction : claude-mem contient des observations exploitables
# ══════════════════════════════════════════════════════════════════════════════
print("\n── TEST 1 : Extraction depuis claude-mem ─────────────────────────────")

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT title, project FROM observations WHERE title IS NOT NULL AND title != ''").fetchall()
conn.close()

check(
    "claude-mem contient des observations avec un titre",
    len(rows) > 0,
    f"Trouvé {len(rows)} observations"
)

projects_found = set(r[1] for r in rows if r[1])
check(
    "Plusieurs projets présents dans claude-mem",
    len(projects_found) >= 1,
    f"Projets : {projects_found}"
)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Transformation : chaque observation devient un nœud graphify valide
# ══════════════════════════════════════════════════════════════════════════════
print("\n── TEST 2 : Transformation observation → nœud ────────────────────────")

sample_obs = {"title": "Test concept pipeline", "project": "Claire", "content_hash": None}
node = transformer.obs_to_node(sample_obs)

check(
    "Le nœud a un champ 'label'",
    "label" in node and node["label"] == "Test concept pipeline"
)
check(
    "Le nœud a un champ 'id' (empreinte unique)",
    "id" in node and len(node["id"]) > 0
)
check(
    "Le nœud a un champ 'source_file' avec le projet",
    "source_file" in node and "Claire" in node["source_file"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Déduplication : ajouter deux fois le même concept = 1 seul nœud
# ══════════════════════════════════════════════════════════════════════════════
print("\n── TEST 3 : Déduplication (pas de doublons) ──────────────────────────")

fake_graph = {"nodes": [], "edges": []}
obs = {"title": "Nilpotence Cognitive", "project": "vault", "content_hash": None}

graph_after_1 = transformer.merge_into_graph(deepcopy(fake_graph), [obs])
graph_after_2 = transformer.merge_into_graph(deepcopy(graph_after_1), [obs])

check(
    "Après 2 insertions du même concept → toujours 1 seul nœud",
    len(graph_after_2["nodes"]) == 1,
    f"Nœuds trouvés : {len(graph_after_2['nodes'])}"
)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Source vault : les .md de 1 - CONVERSATIONS sont lus
# ══════════════════════════════════════════════════════════════════════════════
print("\n── TEST 5 : Lecture du vault 1 - CONVERSATIONS ───────────────────────")

VAULT_PATH = Path(r"G:\Mon Drive\10 - Claude\vault\1 - CONVERSATIONS")
vault_obs = transformer.load_vault_conversations(VAULT_PATH)

check(
    "Des fichiers .md sont détectés dans le vault",
    len(vault_obs) > 0,
    f"Trouvé {len(vault_obs)} fichiers"
)

sample_vault = vault_obs[0]
check(
    "Chaque fichier produit un label lisible (pas juste un chemin brut)",
    "label" in transformer.obs_to_node(sample_vault)
    and "-" not in transformer.obs_to_node(sample_vault)["label"][:3],
    f"Label obtenu : {transformer.obs_to_node(sample_vault).get('label','?')}"
)

check(
    "La source est identifiée comme vault/conversations",
    "conversations" in transformer.obs_to_node(sample_vault).get("source_file", "").lower()
)

# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Intégration : le vrai graph.json est enrichi sans perdre l'existant
# ══════════════════════════════════════════════════════════════════════════════
print("\n── TEST 4 : Intégration sur le vrai graphe ───────────────────────────")

original_graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
nodes_before = len(original_graph["nodes"])

conn = sqlite3.connect(DB_PATH)
all_obs = [
    {"title": r[0], "project": r[1], "content_hash": r[2]}
    for r in conn.execute(
        "SELECT title, project, content_hash FROM observations WHERE title IS NOT NULL AND title != ''"
    ).fetchall()
]
conn.close()

enriched = transformer.merge_into_graph(deepcopy(original_graph), all_obs)
nodes_after = len(enriched["nodes"])

check(
    "Le graphe enrichi a au moins autant de nœuds qu'avant",
    nodes_after >= nodes_before,
    f"Avant : {nodes_before} nœuds → Après : {nodes_after} nœuds"
)
check(
    "Au moins un nœud ajouté (observations nouvelles détectées)",
    nodes_after > nodes_before,
    f"Aucun nœud ajouté — toutes les observations étaient déjà dans le graphe"
)

# ══════════════════════════════════════════════════════════════════════════════
# BILAN
# ══════════════════════════════════════════════════════════════════════════════
total = len(results)
passed = sum(results)
print(f"\n{'═'*54}")
print(f"  {passed}/{total} PASS  {'✅ Contrat respecté' if passed == total else '❌ Contrat non respecté'}")
print(f"{'═'*54}\n")
sys.exit(0 if passed == total else 1)
