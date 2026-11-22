"""Shared pair-local analytical binding, separate from account authorization."""
from sfm_fx_new_age.contracts.domain import PAIRS


def eligible_lanes(connector):
    r=connector.r;account=r.accounts.current
    states={s:'WAITING_ACCOUNT_AUTHORIZATION' for s in PAIRS}
    if not account or not account.authenticated or account.origin.value!='LIVE_OBSERVED':return {},states
    state=connector.native.get((account.endpoint_class,account.account_id),{})
    intent=connector.feed_intents.get(account.scope_id)
    if not state.get('connected') or not intent or intent.get('epoch')!=state.get('epoch'):return {},states
    eligible={}
    for symbol in PAIRS:
        authority=r.market.authority(symbol);spec=r.market.spec(account.account_id,symbol)
        if not authority or (authority.get('scope_id'),authority.get('source_epoch'),authority.get('origin'))!=(account.scope_id,state.get('epoch'),'LIVE_OBSERVED'):
            resolution=state.get('symbol_resolution',{}).get(symbol)
            states[symbol]=resolution if resolution and resolution not in {'EXACT_NATIVE_NAME','RESOLVED_BY_ASSETS'} else 'WAITING_CURRENT_AUTHORITY'
            continue
        if not spec or spec.scope_id!=account.scope_id or spec.origin.value!='LIVE_OBSERVED' or state.get('symbols',{}).get(spec.broker_symbol_id)!=symbol or spec.broker_symbol_id not in state.get('specs',{}):
            states[symbol]=state.get('symbol_resolution',{}).get(symbol,'WAITING_CURRENT_SPECIFICATION')
            if states[symbol] in {'EXACT_NATIVE_NAME','RESOLVED_BY_ASSETS'}:states[symbol]='WAITING_CURRENT_SPECIFICATION'
            continue
        eligible[symbol]=state['epoch'];states[symbol]='ELIGIBLE'
    return eligible,states


def project_binding(binding, symbols):
    if binding is None:return None
    lanes=tuple((s,e) for s,e in binding[1] if s in symbols)
    if not lanes:return None
    # Include native ID membership where provided, without changing old callers.
    ids=tuple((s,i) for s,i in binding[2] if s in symbols) if len(binding)>2 else ()
    return (binding[0],lanes,ids) if len(binding)>2 else (binding[0],lanes)


def lane_matches(runtime,binding,symbol):
    if binding is None or symbol not in dict(binding[1]):return False
    account=runtime.accounts.current;authority=runtime.market.authority(symbol)
    if not account or not account.authenticated or account.scope_id!=binding[0] or account.origin.value!='LIVE_OBSERVED':return False
    if not authority or (authority.get('scope_id'),authority.get('source_epoch'),authority.get('origin'))!=(binding[0],dict(binding[1])[symbol],'LIVE_OBSERVED'):return False
    spec=runtime.market.spec(account.account_id,symbol)
    if not spec:return False
    if len(binding)>2 and dict(binding[2]).get(symbol)!=spec.broker_symbol_id:return False
    # Actual runtime carries the connector: recheck native metadata, not only DB.
    if hasattr(runtime,'connector'):
        eligible,_=eligible_lanes(runtime.connector)
        if eligible.get(symbol)!=dict(binding[1])[symbol]:return False
    return True


def prune_admissions(runtime,store,provider,binding):
    """Bound ephemeral membership; intersect only, never restore DB authority."""
    if binding is None or provider not in store.admissions:return
    from sfm_fx_new_age.contracts.analytics import digest
    from sfm_fx_new_age.contracts.domain import instant
    now=runtime.clock();retained=set()
    if hasattr(store,'live_admission_members'):
        indexed=store.live_admission_members(provider,binding,now)
        if indexed is not None:
            store.admissions[provider].intersection_update(indexed)
            return
    for symbol,epoch in binding[1]:
        for row in runtime.database.supplemental_candidates(scope=binding[0],epoch=epoch,symbol=symbol,origin='LIVE_OBSERVED',providers={provider:store.providers[provider]},cutoff=now):
            if row['provider_id']==provider and instant(now)<=instant(row['valid_until']):retained.add(digest(row))
    store.admissions[provider].intersection_update(retained)
