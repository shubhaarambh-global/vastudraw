from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "docs" / "agent-memory" / "knowledge-graph.json"

def load_graph() -> dict[str, Any]:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

def validate(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list):
        return ["nodes must be a list"]
    if not isinstance(edges, list):
        return ["edges must be a list"]

    ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node[{index}] must be an object")
            continue
        for key in ("id", "type", "title", "status", "provenance"):
            if key not in node:
                errors.append(f"node[{index}] missing {key}")
        node_id = node.get("id")
        if isinstance(node_id, str):
            if node_id in ids:
                errors.append(f"duplicate node id: {node_id}")
            ids.add(node_id)
        if not isinstance(node.get("provenance"), list) or not node.get("provenance"):
            errors.append(f"node[{index}] provenance must be a non-empty list")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{index}] must be an object")
            continue
        for key in ("from", "rel", "to"):
            if key not in edge:
                errors.append(f"edge[{index}] missing {key}")
        if edge.get("from") not in ids:
            errors.append(f"edge[{index}] unknown from node: {edge.get('from')}")
        if edge.get("to") not in ids:
            errors.append(f"edge[{index}] unknown to node: {edge.get('to')}")
    return errors

def query(graph: dict[str, Any], term: str) -> list[dict[str, Any]]:
    needle = term.casefold()
    matches = []
    for node in graph.get("nodes", []):
        haystack = json.dumps(node, sort_keys=True).casefold()
        if needle in haystack:
            matches.append(node)
    return matches

def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/query Vastudraw Codex memory graph.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    q = sub.add_parser("query")
    q.add_argument("term")
    sub.add_parser("summary")
    args = parser.parse_args()

    graph = load_graph()
    errors = validate(graph)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    if args.command == "validate":
        print(f"OK: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    elif args.command == "query":
        matches = query(graph, args.term)
        for node in matches:
            print(json.dumps(node, indent=2, sort_keys=True))
        if not matches:
            raise SystemExit(2)
    elif args.command == "summary":
        counts: dict[str, int] = {}
        for node in graph["nodes"]:
            counts[node["type"]] = counts.get(node["type"], 0) + 1
        print(json.dumps(counts, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
