"""Readiness replay of one genuinely new connector-owned acquisition.

No fixture creation, source-clock changes, source-scope changes, or networking.
A closed capture and this recorded-cutoff replay do not prove a continuous feed.
"""
from pathlib import Path
from collections import Counter
import hashlib, json, os, sqlite3, sys
from typing import Any, cast

PACKAGE=Path(os.environ['SFM_CURRENT_PACKAGE_ROOT']).resolve(strict=True)
sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import AccountContext,PAIRS,FRAMES,instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest

CAPTURE=Path(os.environ['SFM_CURRENT_CAPTURE']).resolve(strict=True)
OUT=Path(os.environ['SFM_CURRENT_OUT']).resolve()
OUT.mkdir(parents=True,exist_ok=False,mode=0o700)
receipt=json.loads((CAPTURE/'capture-receipt.json').read_bytes())
assert receipt['result']=='ORIGINAL_ACQUISITION_COMPLETE_NOT_ALL_STRATEGIES_COMPLETE',receipt['result']
assert receipt['synthetic_observations']==0 and receipt['source_database_modified'] is False
assert receipt['sdk_processes_stopped'] and receipt['auth_thread_stopped'] and receipt['runtime_closed']
assert receipt['denied_broker_mutations']==0 and receipt['background_jobs_left']==0
source=sqlite3.connect((CAPTURE/'state.sqlite3').as_uri()+'?mode=ro',uri=True)
try:
    source.execute('PRAGMA query_only=ON');source.execute('BEGIN')
    scope=json.loads(source.execute("SELECT body FROM records WHERE kind='setting' AND id='connector_remember'").fetchone()[0])['scope_id']
    selected=[];observed=[]
    for kind,identity,raw in source.execute("SELECT kind,id,body FROM records WHERE kind IN ('account_metadata','authority','spec','quote','bar','bar_revision','calendar','native_quote_history_received','native_quote_history_page','native_quote_history_job') ORDER BY kind,id"):
        body=json.loads(raw)
        if body.get('scope_id')!=scope:continue
        assert body.get('origin') in (None,'LIVE_OBSERVED')
        observed.extend(body[k] for k in ('available_at','bid_at','ask_at') if body.get(k))
        selected.append((kind,identity,raw))
finally:source.close()
assert selected and observed
# Source-owned observed clock, never today's clock substituted onto older data.
# Include actually acquired context availability so its admission is not future.
config=json.loads((CAPTURE/'sources.json').read_bytes())
source_files=[]
for provider in config['providers']:
    path=Path(provider['manifest_path']);manifest=json.loads(path.read_bytes())
    for entry in manifest['entries']:
        payload=path.parent/entry['file'];raw=payload.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        body=json.loads(raw);assert body['origin']=='LIVE_OBSERVED'
        assert body['scope_id']==scope and body['kind'] not in {'VENUE_BOOK','TRADED_PRINTS','AGGRESSOR_PRINTS'}
        observed.append(body['available_at']);source_files.append(dict(file=str(payload.relative_to(CAPTURE)),sha256=entry['sha256']))
cutoff=max(observed,key=instant)
r=ApplicationRuntime(clock=lambda:cutoff,supplemental_config=CAPTURE/'sources.json')
proof:dict[str,Any]=dict(result='FAIL',scope='FRESH_ACQUISITION_RECORDED_CUTOFF_REPLAY_NOT_CONTINUOUS_LIVE_QUALIFICATION',
    cutoff=cutoff,capture_receipt_sha256=hashlib.sha256((CAPTURE/'capture-receipt.json').read_bytes()).hexdigest(),
    input_row_sha256=hashlib.sha256(json.dumps(selected,separators=(',',':')).encode()).hexdigest(),
    synthetic_observations=0,full_requested_completion=False,source_files=source_files)
try:
    with r.database.transaction() as connection:connection.executemany('INSERT INTO records VALUES(?,?,?)',selected)
    account=r.database.get('account_metadata',scope);assert account and account['authenticated'] is False
    r.accounts.select(AccountContext(**{key:value for key,value in account.items() if key!='scope_id'}))
    r.supplemental_ingress.poll(force=True)
    for method in METHODS:
        reply=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=method.recipe_id,version=method.version,enabled=True))
        assert reply.status.value=='ACCEPTED'
    r.pump()
    layers=cast(list[dict[str,Any]],[row for pair in PAIRS for frame in FRAMES for row in r.analytics.projections.read(pair,frame)])
    denominator=json.loads((PACKAGE/'sfm_fx_new_age/contracts/data/public_document_requirements.json').read_bytes())
    assert {row['strategy_id'] for row in layers}==set(denominator['expected_catalogue_ids'])
    assert len(layers)==len(METHODS)*len(PAIRS)*len(FRAMES)
    assert all(row['state']!='ERROR' for row in layers)
    blockers={'volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance'}
    assert all(row['state']=='DATA_UNAVAILABLE' and not any(row[key] for key in ('zones','series','markers')) for row in layers if row['strategy_id'] in blockers)
    chart_checks=[]
    for pair in PAIRS:
        for frame in FRAMES:
            chart=thaw(r.api(1).query('1.4',DataRequest('chart',symbol=pair,timeframe=frame,limit=5000)))
            authority=r.market.authority(pair);assert authority is not None
            assert len(chart['strategy_layers'])==len(METHODS)
            assert all((row['symbol'],row['timeframe'],row['scope_id'],row['source_epoch'])==(pair,frame,r.market.scope_id,authority['source_epoch']) for row in chart['strategy_layers'])
            chart_checks.append(dict(symbol=pair,timeframe=frame,layers=len(chart['strategy_layers'])))
    per_profile=[dict(strategy_id=method.key,states=dict(Counter(row['state'] for row in layers if row['strategy_id']==method.key)),
        positive_geometry_rows=sum(row['state']=='READY' for row in layers if row['strategy_id']==method.key)) for method in METHODS]
    matrix={':'.join(row[key] for key in ('strategy_id','symbol','timeframe')):{key:row[key] for key in ('state','reason','zones','series','markers','metrics','available_at','fingerprint')} for row in layers}
    with (OUT/'matrix.json').open('x') as stream:json.dump(matrix,stream,sort_keys=True);stream.write('\n')
    assert r.accounts.current is not None
    proof.update(result='PASS_FRESH_ORIGINAL_REPLAY_NOT_ALL_STRATEGIES_READY',matrix_rows=len(layers),states=dict(Counter(row['state'] for row in layers)),
        per_profile=per_profile,chart_checks=chart_checks,matrix_sha256=hashlib.sha256((OUT/'matrix.json').read_bytes()).hexdigest(),
        supplemental_status=r.supplemental_ingress.status(),fixture_imports=[key for key in sys.modules if key.startswith('sfm_fx_new_age.testing')],
        sdk_workers_started=bool(r.connector.workers),input_blockers=sorted(blockers),account_authenticated=r.accounts.current.authenticated)
    assert not proof['fixture_imports'] and not proof['sdk_workers_started'] and not proof['account_authenticated']
finally:
    r.close();proof['runtime_closed']=r.closed
    with (OUT/'current-replay-receipt.json').open('x') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
print(json.dumps({key:value for key,value in proof.items() if key not in {'per_profile','source_files','chart_checks','supplemental_status'}},indent=2))
