"""Source-declared dependency graph, not a claim of implemented sensors."""
from __future__ import annotations

from graphlib import TopologicalSorter
from importlib.resources import files
import json


def scanner_graph() -> dict[str, tuple[str, ...]]:
    raw = json.loads(files('sfm_fx_new_age.contracts.data').joinpath('scanner_component_dag_44.json').read_text())
    graph = {row['id']: tuple(row['depends_on']) for row in raw['items']}
    if len(graph) != 44 or sum(map(len, graph.values())) != 130:
        raise ValueError('Scanner graph identity/count mismatch')
    if any(parent not in graph for parents in graph.values() for parent in parents):
        raise ValueError('Unknown scanner dependency')
    tuple(TopologicalSorter(graph).static_order())
    return graph


def dirty_descendants(component_id: str) -> tuple[str, ...]:
    graph = scanner_graph()
    if component_id not in graph:
        raise KeyError(component_id)
    dirty = {component_id}
    order = tuple(TopologicalSorter(graph).static_order())
    for node in order:
        if set(graph[node]) & dirty:
            dirty.add(node)
    return tuple(node for node in order if node in dirty)
