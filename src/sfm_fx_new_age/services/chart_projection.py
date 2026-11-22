"""Pure source-bound chart geometry. No qualification, sizing or broker authority."""
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import decimal, instant


def setup_projection(row, *, scope, epoch, symbol, as_of, candidate=None):
    line=row.get('lineage',{})
    kind='market_candidate' if row.get('candidate_id') else 'signal' if row.get('signal_id') else None
    if not kind:return None
    source=(line.get('source_scope'),line.get('source_epoch'),line.get('symbol')) if line else (row.get('scope_id'),row.get('source_epoch'),row.get('symbol'))
    available=line.get('available_at') or row.get('available_at')
    if source!=(scope,epoch,symbol) or not available or instant(available)>instant(as_of):return None
    linked=candidate if kind=='signal' and candidate and digest(candidate)==row.get('source_candidate_hash') else None
    source_frame=line.get('timeframe') or (linked or {}).get('lineage',{}).get('timeframe')
    lines=[]
    def add(role,price,variant_id=None):
        if price is not None and decimal(price)>0:lines.append({'role':role,'price':str(price),'variant_id':variant_id})
    add('entry',row.get('entry',row.get('entry_price')))
    if kind=='market_candidate':
        add('structural anchor',row.get('anchor'))
        for v in row.get('variants',[])[:16]:add('internal invalidation · '+v['buffer_code'],v['stop_price'],v['variant_id'])
    else:add('internal invalidation',row.get('invalidation_price'),row.get('variant_id'))
    add('research target',row.get('target') if kind=='market_candidate' else (linked or {}).get('target'))
    expiry=row.get('expires_at')
    return {'category':'RESEARCH_CANDIDATE' if kind=='market_candidate' else 'LOCAL_SIGNAL',
        'object_kind':kind,'object_id':row.get('candidate_id') or row['signal_id'],'revision':row['revision'],'object_hash':digest(row),
        'scope_id':scope,'source_epoch':epoch,'symbol':symbol,'source_timeframe':source_frame,'available_at':available,
        'expires_at':expiry,'expired':bool(expiry and instant(expiry)<=instant(as_of)),
        'blockers':row.get('blockers',[]),'lines':lines,'variants_total':len(row.get('variants',[])),
        'variants_truncated':len(row.get('variants',[]))>16,'meaning':'Geometry only; internal invalidation is not broker SL or bounded monetary risk'}


def scenario_projection(context):
    s=context.get('scenario') or {}
    if not s.get('entry'):return None
    result={'category':'MANUAL_SCENARIO','scope_id':context['scope_id'],'source_epoch':context['source_epoch'],
        'symbol':context['symbol'],'source_timeframe':context['timeframe'],'available_at':context['as_of'],
        'context_id':context['context_id'],'object_id':context['object_id'],'object_hash':context['object_hash'],
        'lines':[{'role':'scenario '+k,'price':s[k]} for k in ('entry','exit') if s.get(k)],
        'meaning':'Manual gross estimate; not risk sizing, funding, signal evidence or broker instruction'}
    if all(s.get(k) for k in ('entry','exit','side','lots','contract','pip_size')):
        from .tool_calculator import calculate
        value=calculate(context['symbol'],s['side'],s['entry'],s['exit'],s['lots'],s['contract'],s['pip_size'])
        result.update(lots=s['lots'],gross_quote_pnl=str(value['pnl']),quote_currency=value['quote'])
    return result
