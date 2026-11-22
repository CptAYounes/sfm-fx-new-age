"""One full all-profile replay for paired unprofiled latency measurement."""
import hashlib,json,sys
from typing import Any
from original_source_checks import original_runtime,RUN

proof:dict[str,Any]
r,layers,_,proof=original_runtime()
try:
    assert len(layers)==2324 and not any(v['state']=='ERROR' for v in layers)
    assert not [k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')]
    assert not r.connector.workers and r.accounts.current and not r.accounts.current.authenticated
    raw=(json.dumps(layers,sort_keys=True,separators=(',',':'))+'\n').encode()
    with (RUN/'full-layers.json').open('xb') as stream:stream.write(raw)
    proof['full_layers_sha256']=hashlib.sha256(raw).hexdigest()
    proof['network_started']=False
    proof['fixture_imports']=[]
finally:
    r.close();proof['runtime_closed']=r.closed
    with (RUN/'compute-replay-receipt.json').open('x') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
print(json.dumps({k:proof[k] for k in ('scope','elapsed_seconds','full_layers_sha256','input_row_sha256','runtime_closed')},indent=2))
