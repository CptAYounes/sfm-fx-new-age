from __future__ import annotations

import json
from pathlib import Path

from .contracts.registry import load_routes, load_subtabs
from .core.dag import scanner_graph
from .core.runtime import ApplicationRuntime


def run_checks() -> dict[str, object]:
    definitions = load_subtabs()
    routes = load_routes()
    runtime = ApplicationRuntime()
    try:
        active_root = Path(__file__).resolve().parent
        forbidden = 'FI' + 'RE'
        legacy_matches = [str(path.relative_to(active_root)) for path in active_root.rglob('*')
            if path.suffix in {'.py', '.csv'} and '__pycache__' not in path.parts
            and forbidden in path.read_text(encoding='utf-8')]
        owners = {item.backend_owner for item in definitions}
        components = {state.component_id for state in runtime.components.states()}
        unknown_owners = sorted(owners - components)
        route_components = {route.source for route in routes} | {route.destination for route in routes}
        unknown_route_components = sorted(route_components - components)
        snapshots = [runtime.api(d.main_tab).snapshot(d.subtab_id) for d in definitions]
        graph = scanner_graph()
        split = runtime.architecture_summary()['subtabs_by_tab']
        return {
            'main_tabs': len(runtime.tabs), 'subtabs': len(definitions), 'subtabs_by_tab': split,
            'routes': len(routes), 'route_scope': 'DECLARED_HOST_CONTRACTS_NOT_FULL_DOMAIN_IMPLEMENTATION',
            'components': len(components), 'snapshot_contracts': len(snapshots),
            'scanner_declared_nodes': len(graph), 'scanner_declared_edges': sum(map(len, graph.values())),
            'unknown_owners': unknown_owners, 'unknown_route_components': unknown_route_components,
            'legacy_execution_term_matches': legacy_matches,
            'ok': len(runtime.tabs) == 4 and len(definitions) == 42
                and split == {'1': 10, '2': 10, '3': 13, '4': 9}
                and len(snapshots) == 42 and not unknown_owners and not unknown_route_components
                and not legacy_matches and not runtime.router.errors,
        }
    finally:
        runtime.close()


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['ok'] else 1
