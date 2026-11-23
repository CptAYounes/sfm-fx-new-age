#!/usr/bin/env python3
"""Verify the portable public source/documentation package without broker access."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
IGNORED = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'build', 'dist'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def members(base: Path) -> list[Path]:
    import os
    found = []
    for folder, directories, filenames in os.walk(base, followlinks=False):
        directories[:] = [x for x in directories if x not in IGNORED and not x.endswith('.egg-info')]
        for name in filenames:
            path = Path(folder) / name
            if path.suffix not in {'.pyc', '.pyo'}:
                found.append(path)
    return sorted(found)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.refs = []
        self.chapters = 0
        self.remote_resources = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if 'id' in attributes:
            self.ids.append(attributes['id'])
        for key in ['href', 'src']:
            if key in attributes:
                self.refs.append(attributes[key])
        if tag == 'section' and 'chapter' in attributes.get('class', '').split():
            self.chapters += 1
        if tag in {'script', 'link', 'img'}:
            for key in ['src', 'href']:
                if urlsplit(attributes.get(key, '')).scheme in {'http', 'https'}:
                    self.remote_resources.append(attributes[key])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-doc-manifest', action='store_true', help='Explicitly rebind intentionally updated documentation')
    parser.add_argument('--refresh-source-manifest', action='store_true', help='Explicitly rebind intentionally updated packaged source')
    args = parser.parse_args()
    provenance_path = DOCS / 'publication.json'
    provenance = json.loads(provenance_path.read_text())
    if args.refresh_source_manifest:
        for row in provenance['product_files']:
            row['sha256'] = digest(ROOT / row['path'])
            row['unchanged'] = row['sha256'] == row['original_sha256']
        provenance_path.write_text(json.dumps(provenance, indent=2) + '\n')
    manifest_path = DOCS / 'MANIFEST.sha256'
    if args.refresh_doc_manifest or args.refresh_source_manifest:
        manifest_path.write_text(''.join(f'{digest(p)}  {p.relative_to(DOCS).as_posix()}\n' for p in members(DOCS) if p != manifest_path))

    failures = []
    checks = {}

    def check(name, passed, detail=None):
        checks[name] = {'pass': bool(passed), 'detail': detail}
        if not passed:
            failures.append(name)

    files = members(ROOT)
    if (ROOT / '.git').exists():
        result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT, check=True, capture_output=True)
        candidates = sorted({ROOT / p for p in result.stdout.decode().split('\0') if p})
    else:
        candidates = files
    private = [str(p.relative_to(ROOT)) for p in candidates if any(x in {'.runtime', '.venv', 'private'} for x in p.relative_to(ROOT).parts) or p.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx'} or p.name == '.env']
    check('no_private_payloads', not private, private)
    links = [str(p.relative_to(ROOT)) for p in candidates if p.is_symlink()]
    check('no_symlink_payloads', not links, links)
    oversized = [str(p.relative_to(ROOT)) for p in candidates if p.is_file() and p.stat().st_size > 10_000_000]
    check('no_oversized_payloads', not oversized, oversized)
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    check('license_and_version', metadata['project']['license'] == 'MIT' and metadata['project']['version'] == provenance['version'] and 'Copyright (c) 2026 Anthony Younes' in (ROOT / 'LICENSE').read_text())

    meta = json.loads((DOCS / 'package.json').read_text())
    check('60_main_documents', [d['id'] for d in meta['documents']] == [f'NA-D{i:02d}' for i in range(1, 61)] and {str(p.relative_to(DOCS)) for p in (DOCS / 'documents').glob('*.md')} == {d['path'] for d in meta['documents']})
    check('12_architecture_decisions', len(meta['decisions']) == 12 and {str(p.relative_to(DOCS)) for p in (DOCS / 'decisions').glob('*.md')} == {d['path'] for d in meta['decisions']})
    check('14_reference_chapters', len(meta['references']) == 14 and {str(p.relative_to(DOCS)) for p in (DOCS / 'references').glob('*.md')} == set(meta['references']))
    source_rows = provenance['product_files']
    current = {str(p.relative_to(ROOT)) for p in members(ROOT / 'src/sfm_fx_new_age')}
    check('158_product_files_exact_membership', len(source_rows) == len(current) == 158 and current == {r['path'] for r in source_rows})
    drift = [r['path'] for r in source_rows if not (ROOT / r['path']).is_file() or digest(ROOT / r['path']) != r['sha256']]
    check('source_snapshot_integrity', not drift, drift)
    check('152_python_product_modules', len(list((ROOT / 'src/sfm_fx_new_age').rglob('*.py'))) == 152)
    expected = {}
    for line in manifest_path.read_text().splitlines():
        sha, name = line.split('  ', 1)
        if name in expected or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe or duplicate documentation manifest entry')
        expected[name] = sha
    actual = {str(p.relative_to(DOCS)) for p in members(DOCS) if p != manifest_path}
    bad = [name for name, sha in expected.items() if not (DOCS / name).is_file() or digest(DOCS / name) != sha]
    check('documentation_manifest_membership', actual == set(expected), {'members': len(expected), 'missing': sorted(set(expected) - actual), 'extra': sorted(actual - set(expected))})
    check('documentation_manifest_hashes', not bad, bad)
    for path in members(DOCS):
        if path.suffix == '.json':
            json.loads(path.read_text())
    check('all_documentation_json_parses', True)

    from markdown_it import MarkdownIt
    markdown = MarkdownIt('commonmark', {'html': True}).enable('table')
    broken = []
    bad_anchors = []
    local_count = 0
    anchor_count = 0
    for path in files:
        if path.suffix != '.md':
            continue
        page = Page()
        page.feed(markdown.render(path.read_text()))
        for ref in page.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or not url.path:
                continue
            # Root-relative GitHub website URLs are not checkout paths.
            if url.path.startswith('/'):
                continue
            local_count += 1
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                broken.append({'file': str(path.relative_to(ROOT)), 'ref': ref})
                continue
            if re.fullmatch(r'L\d+(?:-L\d+)?', url.fragment):
                anchor_count += 1
                requested = [int(x) for x in re.findall(r'\d+', url.fragment)]
                if not target.is_file() or max(requested) > len(target.read_text().splitlines()) or min(requested) < 1:
                    bad_anchors.append({'file': str(path.relative_to(ROOT)), 'ref': ref})
    check('relative_markdown_links', not broken, {'checked': local_count, 'broken': broken})
    check('source_line_anchors', not bad_anchors, {'checked': anchor_count, 'bad': bad_anchors})
    handbook = Page()
    handbook.feed((DOCS / 'SFM_FX_New_Age_Engineering_Handbook.html').read_text())
    check('html_chapters_and_ids', handbook.chapters == 88 and len(handbook.ids) == len(set(handbook.ids)), {'chapters': handbook.chapters})
    check('html_offline_resources', not handbook.remote_resources, handbook.remote_resources)
    html_bad = []
    for ref in handbook.refs:
        url = urlsplit(ref)
        if url.scheme or url.netloc:
            continue
        if not url.path and url.fragment and url.fragment not in handbook.ids:
            html_bad.append(ref)
        if url.path and not (DOCS / unquote(url.path)).resolve().is_file():
            html_bad.append(ref)
    check('html_local_links_and_anchors', not html_bad, html_bad)
    diagram_bad = []
    for row in meta['diagrams']:
        for suffix in ['dot', 'svg', 'png']:
            path = DOCS / 'diagrams' / f"{row['id']}.{suffix}"
            if not path.is_file() or path.stat().st_size < 100:
                diagram_bad.append(str(path.relative_to(DOCS)))
        if not ET.parse(DOCS / row['path']).getroot().tag.endswith('svg'):
            diagram_bad.append(row['path'])
    check('eight_editable_rendered_diagrams', len(meta['diagrams']) == 8 and not diagram_bad, diagram_bad)

    def rows(path):
        with (DOCS / path).open(newline='') as handle:
            return list(csv.DictReader(handle))

    views = rows('references/views.csv')
    check('42_view_identities', len(views) == len({r['subtab_id'] for r in views}) == 42 and Counter(r['main_tab'] for r in views) == {'1': 10, '2': 10, '3': 13, '4': 9})
    methods = rows('references/strategies.csv')
    keys = {r['strategy_id'] for r in methods}
    check('83_method_policy_identities', len(keys) == len(methods) == len({r['policy_id'] for r in methods}) == 83)
    lanes = rows('references/active-analytical-identities.csv')
    identities = {(r['strategy_id'], r['symbol'], r['timeframe']) for r in lanes}
    expected_lanes = {(m, s, t) for m in keys for s in {'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD'} for t in {'W1', 'D1', 'H4', 'H1'}}
    check('1992_exact_analytical_identities', len(lanes) == len(identities) == 1992 and identities == expected_lanes)
    source_symbols = {}
    missing_symbols = []
    for row in rows('references/requirements-traceability.csv'):
        for field, name in [('source', 'symbol'), ('test_module', 'test_function')]:
            rel = row[field]
            if rel not in source_symbols:
                tree = ast.parse((ROOT / rel).read_text())
                found = set()
                def walk(nodes, prefix=''):
                    for node in nodes:
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                            found.add(prefix + node.name)
                            if isinstance(node, ast.ClassDef):
                                walk(node.body, prefix + node.name + '.')
                walk(tree.body)
                source_symbols[rel] = found
            if row[name] not in source_symbols[rel]:
                missing_symbols.append((rel, row[name]))
    check('traceability_matches_actual_ast', not missing_symbols, missing_symbols)
    sbom = json.loads((DOCS / 'references/sbom.cdx.json').read_text())
    check('historical_sbom_structural_inventory', sbom['bomFormat'] == 'CycloneDX' and len(sbom['components']) == meta['counts']['installed_python_distributions'])
    result = subprocess.run(['pdftotext', '-layout', str(DOCS / 'SFM_FX_New_Age_Engineering_Handbook.pdf'), '-'], capture_output=True, text=True, check=True)
    text = result.stdout
    check('pdf_all_document_and_adr_ids', all(row['id'] in text for row in meta['documents'] + meta['decisions']) and '\ufffd' not in text)
    info = subprocess.check_output(['pdfinfo', str(DOCS / 'SFM_FX_New_Age_Engineering_Handbook.pdf')], text=True)
    pages = int(re.search(r'^Pages:\s+(\d+)', info, re.M).group(1))
    render = json.loads((DOCS / 'verification/reader-render.json').read_text())
    check('pdf_page_count', pages == render['pdf_pages'] and pages > 60, pages)
    print(json.dumps({'result': 'PASS_PUBLICATION' if not failures else 'FAIL_PUBLICATION', 'checks': checks, 'failed_checks': failures, 'scope': 'Portable source/docs/offline integrity; no broker access or profitability certification'}, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
