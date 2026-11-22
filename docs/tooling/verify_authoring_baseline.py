"""Read-only companion validation; never launches the application or contacts a provider.

Use application venv Python. --write-report is a publication step before sealing.
After sealing, omit it: the checksum manifest protects the existing report too.
"""
from pathlib import Path
import argparse,ast,collections,csv,datetime,hashlib,html,json,re,subprocess,sys,unicodedata,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from markdown_it import MarkdownIt

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)
    def text(self):return ' '.join(self.parts)

class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.refs=[];self.sections=0;self.remote=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        for k in ['href','src']:
            if k in a:self.refs.append(a[k])
        if tag=='section' and 'chapter' in a.get('class','').split():self.sections+=1
        if tag in {'script','link','img'} and any(urlsplit(a.get(k,'')).scheme in {'http','https'} for k in ['src','href']):self.remote.append(a)

def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).replace('\u200b','').replace('\ufeff','')).strip()
def htext(s):p=Plain();p.feed(s);return p.text()
def rows(root,path):
    with (root/path).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('package',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--source-root',type=Path);ap.add_argument('--write-report',action='store_true');args=ap.parse_args()
    root=args.package.resolve();meta=json.loads((root/'package.json').read_text());source=(args.source_root or Path(meta['source_root'])).resolve();errors=[];checks={}
    def check(name,value,detail=None):
        checks[name]=dict(pass_=bool(value),detail=detail)
        if not value:errors.append(name)
    mainpaths=[d['path'] for d in meta['documents']];adrpaths=[d['path'] for d in meta['decisions']];refs=meta['references']
    check('exact_main_document_ids',[d['id'] for d in meta['documents']]==[f'NA-D{i:02d}' for i in range(1,61)])
    check('exact_main_directory_membership',{str(x.relative_to(root)) for x in (root/'documents').glob('*.md')}==set(mainpaths))
    check('exact_adr_membership',{str(x.relative_to(root)) for x in (root/'decisions').glob('*.md')}==set(adrpaths) and len(adrpaths)==12)
    check('exact_reference_membership',{str(x.relative_to(root)) for x in (root/'references').glob('*.md')}==set(refs) and len(refs)==14)
    check('nonempty_substantive_documents',all(len(re.findall(r'\b\w+\b',(root/p).read_text()))>=250 and (root/p).read_text().count('\n## ')>=3 for p in mainpaths))
    check('no_unfilled_stubs',not any(re.search(r'\b(?:TBD|TODO|Lorem ipsum)\b',(root/p).read_text()) for p in mainpaths+adrpaths))
    md=MarkdownIt('commonmark',{'html':True}).enable('table');link_count=0;source_anchors=0;badlinks=[];badlines=[]
    for p in root.rglob('*.md'):
        page=Page();page.feed(md.render(p.read_text()))
        for ref in page.refs:
            u=urlsplit(ref)
            if u.scheme or u.netloc or not u.path:continue
            link_count+=1;target=(p.parent/unquote(u.path)).resolve()
            if not target.is_file():badlinks.append(dict(file=str(p.relative_to(root)),ref=ref));continue
            if u.fragment.startswith('L') and u.fragment[1:].isdigit():
                line=int(u.fragment[1:]);source_anchors+=1
                try:count=len(target.read_text().splitlines())
                except (UnicodeError,OSError):count=0
                if not 1<=line<=count:badlines.append(dict(file=str(p.relative_to(root)),ref=ref,line_count=count))
    check('relative_markdown_links_exist',not badlinks,dict(links=link_count,failures=badlinks))
    check('source_line_anchors_exist',not badlines,dict(anchors=source_anchors,failures=badlines))
    page=Page();page.feed((root/'SFM_FX_New_Age_Engineering_Handbook.html').read_text())
    check('html_exact_chapters',page.sections==88,page.sections)
    check('html_unique_ids',len(page.ids)==len(set(page.ids)))
    check('html_internal_targets',all(ref[1:] in page.ids for ref in page.refs if ref.startswith('#')))
    check('html_no_remote_runtime_resources',not page.remote)
    localbad=[]
    for ref in page.refs:
        u=urlsplit(ref)
        if not u.scheme and not u.netloc and u.path and not (root/unquote(u.path)).is_file():localbad.append(ref)
    check('html_local_files_exist',not localbad,localbad)
    check('json_files_parse',all(json.loads(p.read_text()) is not None for p in root.rglob('*.json')))
    browser=json.loads((root/'verification/browser-reader-check.json').read_text())
    check('browser_reader_positive_search_and_navigation',browser['result']=='PASS_OFFLINE_READER_BROWSER' and browser['base']['all_images_loaded'] and browser['base']['all_internal_anchors_resolve'] and not browser['base']['horizontal_overflow'] and 0<browser['search']['visible_chapters']<88 and browser['restored_chapters']==88 and browser['navigation']['target_title'].startswith('NA-D24'))
    check('typed_contract_fields_count',len(rows(root,'references/contract-fields.csv'))==meta['counts']['typed_contract_fields'])
    source_rows=rows(root,'references/source-files.csv')
    check('current_product_module_count',sum(x['path'].startswith('src/sfm_fx_new_age/') and x['path'].endswith('.py') for x in source_rows)==meta['counts']['current_product_python_modules'])
    check('installed_distribution_inventory_count',len(rows(root,'references/installed-python-distributions.csv'))==meta['counts']['installed_python_distributions'])
    syntax=[]
    for p in (root/'tooling').glob('*.py'):
        try:compile(p.read_text(),str(p),'exec')
        except SyntaxError as exc:syntax.append(str(exc))
    check('tooling_no_pyc_compile',not syntax,syntax)
    views=rows(root,'references/views.csv');routes=rows(root,'references/routes.csv');commands=rows(root,'references/commands.csv');strategies=rows(root,'references/strategies.csv');lanes=rows(root,'references/active-analytical-identities.csv');req=rows(root,'references/requirements-traceability.csv');corpus=rows(root,'references/original-corpus-requirements.csv');tests=rows(root,'references/retained-v23-test-cases.csv')
    check('view_identity_set',len(views)==42 and len({x['subtab_id'] for x in views})==42 and collections.Counter(x['main_tab'] for x in views)=={'1':10,'2':10,'3':13,'4':9})
    check('host_routes_count',len(routes)==41)
    check('command_registry_count',len(commands)==40 and len({x['command'] for x in commands})==40)
    keys={x['strategy_id'] for x in strategies};pairs={'EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD'};frames={'W1','D1','H4','H1'}
    check('exact_83_unique_method_policy_set',len(strategies)==len(keys)==83 and len({x['policy_id'] for x in strategies})==83)
    actual={(x['strategy_id'],x['symbol'],x['timeframe']) for x in lanes};expected={(m,p,f) for m in keys for p in pairs for f in frames}
    check('exact_1992_analytical_identities',len(lanes)==len(actual)==1992 and actual==expected)
    check('original_corpus_91_unique_requirements',len(corpus)==len({x['requirement_id'] for x in corpus})==91)
    check('requirements_44_unique_source_test_links',len(req)==len({x['requirement_id'] for x in req})==44)
    check('retained_test_1541_outcomes',len(tests)==1541 and all(x.get('outcome')=='passed' for x in tests) and len({(x['classname'],x['name']) for x in tests})==1541)
    symbols=rows(root,'references/source-symbols.csv');symset={(x['path'],x['name']) for x in symbols}
    check('all_crosswalk_symbols_exist',all((x['source'],x['symbol']) in symset and (x['test_module'],x['test_function']) in symset and (root/x['document']).is_file() for x in req))
    astcache={};symbol_drift=[]
    for x in req:
        for rel,name in [(x['source'],x['symbol']),(x['test_module'],x['test_function'])]:
            if rel not in astcache:
                tree=ast.parse((source/rel).read_text());found=set()
                def visit(nodes,parent=''):
                    for node in nodes:
                        if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                            found.add(parent+node.name)
                            if isinstance(node,ast.ClassDef):visit(node.body,parent+node.name+'.')
                visit(tree.body);astcache[rel]=found
            if name not in astcache[rel]:symbol_drift.append((rel,name))
    check('crosswalk_symbols_match_current_ast',not symbol_drift,symbol_drift)
    baseline=json.loads((root/'verification/source-baseline.json').read_text());drift=[]
    for x in baseline['files']:
        p=source/x['path']
        if not p.is_file() or sha(p)!=x['sha256'] or p.stat().st_mtime_ns!=x['mtime_ns']:drift.append(x['path'])
    check('all_original_hashes_and_mtimes_preserved',not drift,dict(input_files=len(baseline['files']),drift=drift))
    original_source=source/'.runtime/strategy-signals-v23/candidate-04.json';candidate=json.loads(original_source.read_text())
    drift=[p for p,s in candidate['source'].items() if not (source/p).is_file() or sha(source/p)!=s]
    check('sealed_v23_candidate_source_members_match',not drift,dict(members=len(candidate['source']),drift=drift))
    rs=json.loads((root/'references/retained-release-summary.json').read_text());rd=[]
    for name,x in rs['source_receipts'].items():
        if not (source/x['path']).is_file() or sha(source/x['path'])!=x['sha256']:rd.append(name)
    check('selected_original_release_receipts_unchanged',not rd,rd)
    junit=ET.parse(root/'verification/documentation-smoke.xml').getroot();cases=junit.findall('.//testcase')
    counts=dict(total=len(cases),failures=sum(x.find('failure') is not None for x in cases),errors=sum(x.find('error') is not None for x in cases),skipped=sum(x.find('skipped') is not None for x in cases))
    check('fresh_171_offline_test_outcomes',counts==dict(total=171,failures=0,errors=0,skipped=0),counts)
    smoke=json.loads((root/'verification/smoke-test.json').read_text());check('fresh_smoke_exit_and_ten_modules',smoke['returncode']==0 and len(smoke['modules'])==10)
    fresh=json.loads((root/'verification/fresh_checks.json').read_text());check('fresh_three_headless_commands',len(fresh)==3 and all(x['returncode']==0 and json.loads(x['stdout']).get('ok',True) for x in fresh))
    diagrams=meta['diagrams'];svgfail=[]
    for x in diagrams:
        for suffix in ['dot','svg','png']:
            p=root/('diagrams/'+x['id']+'.'+suffix)
            if not p.is_file() or p.stat().st_size<100:svgfail.append(str(p))
        svg=ET.parse(root/x['path']).getroot()
        if not svg.tag.endswith('svg'):svgfail.append(x['id'])
    check('eight_editable_and_rendered_diagrams',len(diagrams)==8 and not svgfail,svgfail)
    dl=json.loads((root/'verification/pdf-diagram-layout.json').read_text());check('pdf_diagrams_inside_page',len(dl)==8 and all(x['fully_inside_content'] and x['left']>=0 and x['top']+x['height']<x['page_height']-40 for x in dl))
    render=json.loads((root/'verification/reader-render.json').read_text())
    pdf=root/'SFM_FX_New_Age_Engineering_Handbook.pdf'
    proc=subprocess.run(['pdftotext','-layout',str(pdf),'-'],capture_output=True,text=True,check=True);pdftext=norm(proc.stdout)
    info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout;pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    check('pdf_page_count_matches_renderer',pages==render['pdf_pages'] and pages>60,dict(pages=pages))
    check('pdf_all_main_and_adr_ids',all(d['id'] in pdftext for d in meta['documents']+meta['decisions']))
    fragments=[];all_fragments=[];missing=[];all_missing=[];compact_pdf=re.sub(r'\s+','',pdftext)
    for d in meta['documents']:
        body=(root/d['path']).read_text().split('## Source and authority anchors')[0]
        body=body[body.find('\n## ')+1:]
        tokens=md.parse(body);paragraphs=[]
        for n,t in enumerate(tokens):
            if t.type=='inline' and n and tokens[n-1].type=='paragraph_open':
                plain=norm(htext(md.render(t.content)))
                if len(plain)>=100:paragraphs.append(plain)
        for frag in paragraphs:
            # Ignore only whitespace introduced by PDF line wrapping or HTML
            # inline-node boundaries; retain exact ordered non-whitespace text.
            found=re.sub(r'\s+','',frag) in compact_pdf
            all_fragments.append(dict(document=d['id'],excerpt=frag[:100],present=found))
            if not found:all_missing.append(dict(document=d['id'],excerpt=frag))
        for frag in ([paragraphs[0],paragraphs[-1]] if paragraphs else []):
            found=re.sub(r'\s+','',frag) in compact_pdf
            fragments.append(dict(document=d['id'],excerpt=frag[:100],present=found))
            if not found:missing.append(dict(document=d['id'],excerpt=frag))
    check('pdf_first_and_last_substantive_paragraphs',len(fragments)==120 and not missing,dict(excerpts=len(fragments),missing=missing))
    check('pdf_all_substantive_paragraphs',len(all_fragments)>=120 and not all_missing,dict(excerpts=len(all_fragments),missing=all_missing))
    check('pdf_no_missing_glyph_replacement','\ufffd' not in proc.stdout)
    # This is a content/integrity check, not legal license/official schema validation.
    sbom=json.loads((root/'references/sbom.cdx.json').read_text());check('sbom_structural_inventory',sbom['bomFormat']=='CycloneDX' and sbom['specVersion']=='1.5' and len(sbom['components'])==meta['counts']['installed_python_distributions'] and all(x.get('name') and x.get('version') and x.get('purl') for x in sbom['components']))
    check('no_operational_or_private_binary_exports',not any(p.suffix in {'.sqlite3','.db','.pem','.key','.whl'} or p.name=='.env' for p in root.rglob('*') if p.is_file()))
    manifest=root/'MANIFEST.sha256';manifest_result='NOT_YET_SEALED'
    if manifest.exists():
        expected_files={};bad=[]
        for line in manifest.read_text().splitlines():
            digest,name=line.split('  ',1);expected_files[name]=digest
            p=root/name
            if not p.is_file() or sha(p)!=digest:bad.append(name)
        actual_files={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p!=manifest}
        check('sealed_manifest_exact_membership',actual_files==set(expected_files),dict(missing=sorted(set(expected_files)-actual_files),extra=sorted(actual_files-set(expected_files))))
        check('sealed_manifest_all_hashes',not bad,dict(members=len(expected_files),mismatches=bad))
        manifest_result='VERIFIED' if not bad and actual_files==set(expected_files) else 'FAILED'
    result=dict(result='PASS_DOCUMENTATION_PACKAGE' if not errors else 'FAIL_DOCUMENTATION_PACKAGE',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),package=str(root),source=str(source),checks=checks,failed_checks=errors,main_documents=60,adrs=12,reference_chapters=14,diagrams=8,markdown_files=len(list(root.rglob('*.md'))),markdown_words=sum(len(re.findall(r'\b\w+\b',p.read_text())) for p in root.rglob('*.md')),pdf_pages=pages,relative_links_checked=link_count,source_anchors_checked=source_anchors,manifest=manifest_result,scope_limit='Documentation/source-preservation/fresh offline checks only; no new native or broker qualification')
    if args.write_report:
        if manifest.exists():raise SystemExit('Refusing to change a sealed validation report; publish a new edition or explicitly unseal first')
        (root/'verification/validation-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if not errors else 1

if __name__=='__main__':raise SystemExit(main())
