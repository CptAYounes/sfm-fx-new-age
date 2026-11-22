"""Seal the qualified six-pair public-venue scope; never claim full completion."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,xml.etree.ElementTree as ET,zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/public-fiat-access-v1'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    assert not (OUT/'final-evidence.json').exists()
    OUT.chmod(0o700)
    build=json.loads((OUT/'build-receipt.json').read_bytes());wheel=Path(build['wheel'])
    assert digest(wheel)==build['wheel_sha256']
    source=OUT/'source-snapshot';source.mkdir()
    with zipfile.ZipFile(wheel) as z:
        names=[n for n in z.namelist() if n.startswith('sfm_fx_new_age/') and not n.endswith('/')]
        assert len(names)==build['matched_package_files']==139
        for name in names:
            original=ROOT/'src'/name
            assert original.name!='AGENTS.md' and original.read_bytes()==z.read(name)==(Path(build['installed_package_root'])/name).read_bytes()
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
    shutil.copy2(ROOT/'README.md',OUT/'README.snapshot.txt')
    shutil.copy2(ROOT/'PROGRESS.md',OUT/'PROGRESS.snapshot.md')
    shutil.copy2(ROOT/'pyproject.toml',source/'pyproject.toml')
    (source/'scripts').mkdir();shutil.copy2(ROOT/'scripts/launch.sh',source/'scripts/launch.sh')
    verification=OUT/'verification-snapshot';verification.mkdir()
    for name in ('kraken_public_desktop.py','kraken_public_original_checks.py','run_kraken_desktop.py','finalize_public_fiat.py'):
        shutil.copy2(ROOT/'verification'/name,verification/name)
    shutil.copy2(ROOT/'.runtime/feed-bootstrap-isolation-v5/executed-inputs/checks/engineering.py',verification/'engineering.py')
    accepted={}
    for label in ('source-native-final','installed-native-final'):
        path=OUT/label/'acceptance.json';proof=json.loads(path.read_bytes())
        assert proof['result']=='PASS_PUBLIC_VENUE_NATIVE_STARTUP_RECURRING_RECONNECT'
        assert proof['observed_genuine_lanes']==108 and proof['print_based_pair_frame_method_lanes']==72 and proof['quantity_positive_lanes']==36
        assert proof['broker_mutations']==proof['denied_broker_writes']==0 and not proof['fixture_imports']
        assert proof['runtime_closed'] and proof['sdk_processes_stopped'] and proof['public_worker_joined']
        assert proof['library_captured_after_actual_refresh'] and proof['actual_native_chart_layers']==5
        assert proof['reconnect_rebound'] and proof['first_epoch']!=proof['second_epoch']
        accepted[label]=dict(acceptance_sha256=digest(path),genuine_lanes=108,zero_broker_writes=True,joined=True)
    suites={}
    for label in ('source','installed'):
        for suffix,expected in (('regression',1141),('original',62)):
            path=OUT/(('final-'+label+'-regression-junit.xml') if suffix=='regression' else (label+'-complete-original-junit.xml'))
            suite=next(ET.parse(path).getroot().iter('testsuite'))
            assert int(suite.get('tests'))==expected and all(suite.get(k)=='0' for k in ('errors','failures','skipped'))
            suites[label+'-'+suffix]=dict(tests=expected,failures=0,errors=0,skipped=0,receipt_sha256=digest(path))
    with zipfile.ZipFile(OUT/'prior-provider-research-exact.zip') as z:
        for line in z.read('MANIFEST.sha256').decode().splitlines():
            sha,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==sha
    entries={}
    for path in sorted(OUT.rglob('*')):
        if not path.is_file():continue
        assert not path.is_symlink() and path.name!='AGENTS.md'
        path.chmod(0o444)
        entries[str(path.relative_to(OUT))]=dict(sha256=digest(path),bytes=path.stat().st_size)
    manifest=dict(schema_version=1,sealed_at=datetime.now(timezone.utc).isoformat(),
        verdict='QUALIFIED_SIX_PAIR_KRAKEN_VENUE_CONTEXT_NOT_FULL_REQUESTED_COMPLETION',
        full_requested_completion=False,
        verified_pairs=['EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD'],
        executed_quantity_frames=['H1','H4','D1'],print_based_projection_frames=['W1','D1','H4','H1'],
        native=accepted,engineering_and_original_checks=suites,build=build,
        unchanged_architecture=dict(workspaces=4,backend_views=42,method_profiles=83),
        open_scope=[
            'NZDUSD original venue executions and documented aggressors: absent from this production venue list',
            'W1 displacement/effort original 14/20-week executed-quantity lookbacks: not supplied by initial hourly history',
            'Strict native sequenced full-book/FIX qualification and separate broker FIX Price configuration: not recovered'],
        restrictions=dict(venue='KRAKEN_SPOT_FIAT',cTrader_fills=False,consolidated_FX=False,profitable_or_trade_ready=False,
                          book_sequence_claim=False,normal_operator_database_written=False,orders_written=False,
                          pinned_research_chart_not_live_quote_overlay=True),
        publication_policy=dict(maximum_live_snapshots_per_pair_kind=16,normalized_native_observations_deduplicated=True,
                                historical_re_evaluation_beyond_rolling_publications_not_promised=True),
        failures_preserved=['source-native-v1','source-native-v2','source-regression-junit.xml may be absent because the interrupted 270s run never finalized it; source-first-failure-junit.xml and logs remain',
                            'initial focused-junit.xml missing test path, no tests run; corrected focused-v2-junit.xml retained'],
        entries=entries)
    target=OUT/'final-evidence.json'
    with target.open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    target.chmod(0o444)
    print(json.dumps(dict(manifest=str(target),sha256=digest(target),entries=len(entries),full_requested_completion=False),indent=2))


if __name__=='__main__':main()
