"""Core-owned read adapters for the public tab datasets; no storage handles escape."""
from __future__ import annotations
from sfm_fx_new_age.contracts.domain import PAIRS,record,instant
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.analytics import digest


class TabDataService:
    def __init__(self,runtime):
        from sfm_fx_new_age.services.chart_studies import ChartStudyService
        self.r=runtime;self.chart_studies=ChartStudyService()

    def query(self,subtab_id:str,q:DataRequest)->dict:
        r=self.r; symbol=q.symbol or r.selected_pair;now=r.clock();as_of=q.as_of or now
        if instant(as_of)>instant(now):raise ValueError('Future query cutoff is not allowed')
        historical={'bars','chart','levels','evidence','market_candidates','overlays','geometry','signal_history'}
        if q.as_of is not None and q.dataset not in historical:raise ValueError('This dataset is current-state only; use historical/replay datasets for past cutoffs')
        scope=r.market.scope_id;authority=r.market.authority(symbol);epoch=authority['source_epoch'] if authority else None
        rows=[];status='NO_DATA';detail='';extra={};name=q.dataset
        if name in {'levels','evidence','market_candidates','overlays'}:
            kind={'levels':'level','evidence':'evidence','market_candidates':'market_candidate','overlays':'overlay'}[name]
            if epoch:rows=r.research.query(kind,scope=scope,epoch=epoch,symbol=symbol,as_of=as_of,history=q.history,limit=5000)
        elif name in {'bars','chart'}:
            default={'1.2':'W1','1.3':'D1','1.4':'H4','1.5':'H1','3.2':'D1','3.3':'W1','3.4':'H4'}.get(subtab_id,'D1')
            if epoch:rows=[record(b) for b in r.market.bars(symbol,q.timeframe or default,as_of,epoch)]
            extra['forming_bars'] = r.timeline.snapshot(symbol) if q.as_of is None else []
            if name=='chart':
                extra['strategy_layers']=r.analytics.projections.read(symbol,q.timeframe or default,as_of=q.as_of,dirty=symbol in r._analytics_dirty,apply_current_filters=True) if not q.run_id else []
                extra['studies']={k:v[q.cursor:q.cursor+q.limit] for k,v in self.chart_studies.query(rows,(scope,epoch,symbol,q.timeframe or default)).items()}
                extra['origin']=authority['origin'] if authority else 'NO_SOURCE'
                for kind in ('level','overlay'):
                    extra[kind+'s']=r.research.query(kind,scope=scope,epoch=epoch,symbol=symbol,as_of=as_of) if epoch else []
                extra['evidence']=r.research.query('evidence',scope=scope,epoch=epoch,symbol=symbol,as_of=as_of) if epoch else []
                extra['market_candidates']=r.research.query('market_candidate',scope=scope,epoch=epoch,symbol=symbol,as_of=as_of) if epoch else []
                if q.as_of is None:
                    # Recipe-owned zones are current projections only while their
                    # source owner is enabled/coherent. Historical research is retained.
                    methods={m['method_version']:node for node,m in r.analytics.producer_metadata.items() if m.get('enabled_by_recipe')}
                    snapshot=r.analytics.snapshot(symbol) or {}
                    states={n['id']:n['status'] for n in snapshot.get('nodes',[])}
                    def visible(row):
                        node=methods.get(row['lineage']['method_version'])
                        if node is None:return True
                        recipe_id=r.analytics.producer_metadata[node]['enabled_by_recipe']
                        recipe=r.analytics.composers[recipe_id][0];state=r.database.get('recipe_state',recipe_id) or {}
                        return bool(state.get('enabled') and state.get('version')==recipe.version and states.get(node)=='READY'
                                    and row['lineage']['profile_hash']==snapshot.get('profile_hash')
                                    and not r._analytics_dirty.intersection({symbol}) and r.consumers.enabled('analysis.scanner')
                                    and r.consumers.enabled('analysis.pair.'+symbol))
                    extra['levels']=[v for v in extra['levels'] if visible(v)]
                analytic=r.analytics.snapshot(symbol) if q.as_of is None else None
                context=r.market.context(symbol,as_of,epoch) if epoch else {'missing':list(('W1','D1','H4','H1'))}
                extra['readiness']={'classification':'HISTORICAL_CONTEXT_ONLY' if q.as_of is not None else analytic['classification'] if analytic else 'NOT_EVALUATED',
                    'missing_frames':context.get('missing',[]),'unavailable_methods':[n['id'] for n in analytic['nodes'] if n['status']=='UNAVAILABLE'] if analytic else [],
                    'disabled':None if q.as_of is not None else not r.consumers.enabled('analysis.scanner') or not r.consumers.enabled('analysis.pair.'+symbol),
                    'recipes':[] if q.as_of is not None else [{'recipe_id':v['recipe_id'],'state':(r.database.get('recipe_state',v['recipe_id']) or {}).get('enabled',False)} for v in r.research.recipes()],
                    'qualified_candidates':sum(not v['blockers'] for v in extra['market_candidates']),
                    'meaning':'Research status only; missing/unimplemented methods are not a no-setup verdict'}

                if q.run_id:
                    if subtab_id!='1.9':raise ValueError('Replay run rendering belongs to Chart Replay')
                    replay=r.replay.snapshot(q.run_id,symbol=symbol,timeframe=q.timeframe or default)
                    rows=replay['rows'];scope=epoch='REPLAY:'+q.run_id;as_of=replay['as_of'] or as_of
                    extra={'origin':'HISTORICAL_REPLAY','run':{k:v for k,v in replay.items() if k!='rows'},'forming_bars':[],
                           'levels':[],'overlays':[],'evidence':[],'market_candidates':[],
                           'studies':{k:v[q.cursor:q.cursor+q.limit] for k,v in self.chart_studies.query(rows,(scope,epoch,symbol,q.timeframe or default)).items()}}
                if q.as_of is None and not q.run_id:
                    position=r.positions.snapshot()
                    extra['position_observation']={'status':'LAST_KNOWN' if position and position['complete'] else 'INCOMPLETE' if position else 'UNKNOWN',
                        'observed_at':position.get('observed_at') if position else None,'complete':position.get('complete') if position else None}
                    account=r.accounts.current;calendar=r.continuity.calendar(symbol)
                    source_calendar=bool(calendar and authority and (authority['origin']!='LIVE_OBSERVED' or calendar.source_ref=='ProtoOASymbol.schedule / '+epoch))
                    market_open=calendar.is_open(now) if source_calendar else None
                    feed=r.connector.feed_status() if hasattr(r.connector,'feed_status') else {}
                    intent=getattr(r.connector,'feed_intents',{}).get(scope,{})
                    job=r.database.get('backfill',intent.get('jobs',{}).get(symbol+':'+(q.timeframe or default),''))
                    extra['health']={'authenticated':bool(account and account.authenticated),'account_type':account.account_type if account else None,
                        'market_open':market_open,'next_open':calendar.next_open(now) if market_open is False else None,
                        'schedule_timezone':calendar.timezone_name if source_calendar else None,
                        'feed_state':feed.get('state','NOT_STARTED'),'history_state':job['status'] if job else 'NOT_STARTED',
                        'history_detail':job.get('detail','') if job else '',
                        'completed_jobs':feed.get('completed_history_jobs',0),'total_jobs':feed.get('history_jobs',0),
                        'live_bar_subscriptions':feed.get('live_bar_subscriptions',{}),'native_live_bars_received':feed.get('native_live_bars_received',0),
                        'last_completed_at':rows[-1]['close_time'] if rows else None}
                    extra['orders']=[v for v in r.database.orders() if v.get('scope_id')==scope and v['symbol']==symbol]
                    extra['positions']=[v for v in (r.positions.snapshot() or {}).get('rows',[]) if v['symbol']==symbol]
                    pending=r.database.get('broker_pending_snapshot',scope)
                    extra['broker_pending']=[v for v in (pending or {}).get('display_orders',[]) if v.get('symbol')==symbol]
                    extra['pending_observation']={k:v for k,v in pending.items() if k not in {'orders','display_orders'}} if pending else {'status':'UNKNOWN'}
                    extra['signals']=[v for v in r.signals.all() if v['symbol']==symbol and v.get('source_epoch')==epoch]
                if not q.run_id:
                    from sfm_fx_new_age.services.chart_projection import setup_projection
                    candidates={v['candidate_id']:v for v in extra.get('market_candidates',[])}
                    extra['setup_projections']=[p for v in list(candidates.values())+extra.get('signals',[]) if (p:=setup_projection(v,scope=scope,epoch=epoch,symbol=symbol,as_of=as_of,candidate=candidates.get(v.get('market_candidate_id'))))]
        elif name=='watchlist':
            account=r.accounts.current
            for pair in PAIRS:
                quote=r.market.quote(account.account_id,pair) if account else None
                active=r.market.authority(pair)
                row={'symbol':pair,'selected':pair==symbol,'bid':None,'ask':None,'spread':None,'state':'NO_DATA',
                    'scope_id':scope,'source_epoch':active['source_epoch'] if active else None}
                if quote:
                    age=(instant(as_of)-instant(quote.available_at)).total_seconds()
                    row.update(bid=str(quote.bid),ask=str(quote.ask),spread=str(quote.ask-quote.bid),observed_at=quote.available_at,
                        state='INACTIVE_SOURCE' if not active or active['source_epoch']!=quote.source_epoch else 'FUTURE' if age<0 else 'STALE' if age>r.catalogues.parameter_value('feed.quote_max_age_seconds') else 'CURRENT')
                rows.append(row)
        elif name in {'analytics','scanner_nodes'}:
            value=r.analytics.snapshot(symbol)
            if value:
                rows=value['nodes'] if name=='scanner_nodes' else [{'node_id':k,'output':v} for k,v in value['outputs'].items()]
                extra['classification']=value['classification'];extra['d1_campaign_status']=value['d1_campaign_status']
            elif name=='scanner_nodes':rows=[{'id':key,'status':'NOT_EVALUATED','reason':'Waiting for source/core pump'} for key in r.analytics.scheduler.order]
        elif name=='geometry':
            if epoch:
                candidates=r.research.query('market_candidate',scope=scope,epoch=epoch,symbol=symbol,as_of=as_of)
                rows=[dict(v,candidate_id=c['candidate_id'],setup_id=c['setup_id']) for c in candidates for v in c['variants']]
        elif name=='strategy_catalogue':
            extra['input_sources']=r.supplemental_ingress.status()
            rows=r.analytics.projections.catalogue(symbol,q.timeframe or 'H4',dirty=symbol in r._analytics_dirty)
        elif name=='recipes':
            import json
            rows=[dict(recipe,requested=r.database.get('recipe_state',recipe['recipe_id']),
                evaluation=r.analytics.recipe_status.get(json.dumps([scope,epoch,recipe['recipe_id'],symbol]),{'state':'NOT_EVALUATED'})) for recipe in r.research.recipes()]
        elif name=='strategy_signals':
            rows=r.strategy_signals.read(symbol,q.timeframe)
            if q.object_id:rows=[v for v in rows if v.get('opportunity_id')==q.object_id]
            extra['meaning']='Uncalibrated method-specific research signals; explicit units/binding and separate human Issue. OFF / missing data / no setup are not hidden.'
        elif name=='signals':rows=r.signals.all()
        elif name=='signal_history':
            rows=r.research.signal_history(scope,signal_id=q.object_id,as_of=as_of)
            extra['state_history']=[v for v in r.database.list('signal_state_history') if v.get('scope_id')==scope and (not q.object_id or v['signal_id']==q.object_id)
                and (q.as_of is None or v.get('changed_at') and instant(v['changed_at'])<=instant(as_of))]
        elif name in {'orders','order_history'}:
            rows=[v for v in r.database.orders() if v.get('scope_id')==scope]
            if q.object_id:rows=[v for v in rows if q.object_id in {v['id'],v['signal_id'],v.get('broker_order_id')}]
            if name=='order_history':
                extra['native_activity']=[v for v in r.database.list('native_activity') if v.get('scope_id')==scope]
        elif name=='issue_preview':
            if not q.object_id:detail='Select a signal for a bound preflight';status='SELECTION_REQUIRED'
            else:
                signal=r.signals.get(q.object_id)
                if signal:
                    try:rows=[r.orders.preview(q.object_id,signal['revision'],acknowledge_research=q.acknowledge_research)]
                    except ValueError as exc:rows=[{'signal_id':q.object_id,'status':'BLOCKED','blocker':str(exc)}]
        elif name=='positions':
            value=r.positions.snapshot();rows=value['rows'] if value else [];extra['observation']=value
            status='LAST_KNOWN' if value and value['complete'] else 'INCOMPLETE' if value else 'UNKNOWN'
            if value:
                extra['observation']={k:v for k,v in value.items() if k!='rows'}
                extra['observation']['age_seconds']=(instant(now)-instant(value['observed_at'])).total_seconds()
        elif name=='accounts':rows=[record(a)|{'scope_id':a.scope_id,'selected':a==r.accounts.current} for a in r.accounts.sessions.values()]
        elif name=='broker_pending':
            value=r.database.get('broker_pending_snapshot',scope)
            if value:
                rows=value.get('display_orders',value['orders']);extra['observation']={k:v for k,v in value.items() if k not in {'orders','display_orders'}};status='LAST_KNOWN'
            else:status='UNKNOWN'
        elif name in {'broker_history','broker_history_jobs'}:
            rows=[v for v in r.database.list('native_history_record' if name=='broker_history' else 'native_history_job') if v['scope_id']==scope]
            if q.object_id:rows=[v for v in rows if q.object_id in {v.get('id'),v.get('native_id'),v.get('job_id')}]
        elif name=='connector':
            rows=[r.connector.status()] if hasattr(r,'connector') else [{'state':'DISCONNECTED','reason':'No connector configured'}]
        elif name in {'consumers','components'}:
            rows=r.consumers.rows() if name=='consumers' else [record(v) for v in r.components.states()]
        elif name=='coverage':rows=[r.continuity.coverage(symbol,q.timeframe or frame,as_of) for frame in ([q.timeframe] if q.timeframe else ['W1','D1','H4','H1'])]
        elif name=='backfill':rows=[v for v in r.database.list('backfill') if v['scope_id']==scope]
        elif name=='calendars':rows=[v for v in r.database.list('calendar') if v['scope_id']==scope]
        elif name=='specifications':rows=r.market.scoped_rows('spec')
        elif name=='routes':rows=[record(v) for v in r.routes]
        elif name=='router_metrics':rows=[r.router.metrics()]
        elif name in {'pair_parameters','pair_parameter_history'}:
            rows=[v for v in r.market.scoped_rows('pair_parameter' if name=='pair_parameters' else 'pair_parameter_revision') if v['symbol']==symbol and (not q.object_id or v['key']==q.object_id)]
        elif name in {'variables','variable_definitions','parameters','parameter_definitions','mutable_surfaces','rules','rule_history','parameter_history'}:
            kind={'variables':'variable','variable_definitions':'variable_definition','parameters':'parameter',
                'parameter_definitions':'parameter_definition','mutable_surfaces':'mutable_surface','rules':'rule',
                'rule_history':'rule_revision','parameter_history':'parameter_revision'}[name]
            rows=r.database.list(kind)
            if name=='variables':rows=r.catalogues.values()
            if q.object_id:rows=[v for v in rows if q.object_id in {v.get('key'),v.get('rule_id'),v.get('surface_id')}]
        elif name=='replay':
            if q.run_id:rows=[r.replay.snapshot(q.run_id,symbol=q.symbol,timeframe=q.timeframe)]
            else:rows=r.database.list('replay_run')
        elif name=='replay_runs':rows=r.database.list('replay_run')
        elif name=='research_studies':
            rows=[{k:v for k,v in row.items() if k in {'study_id','dataset_id','dataset_hash','status','origin','original_origin','execution_allowed','method_version','result_hash','bar_revisions','unique_bars','markers'}} for row in r.database.list('research_study')]
        elif name=='replay_datasets':rows=[{k:v for k,v in row.items() if k!='bars'}|{'series':sorted({(b['symbol'],b['timeframe']) for b in row['bars']})} for row in r.database.list('replay_dataset')]
        elif name=='audit':rows=r.database.query_events(scope_id=scope,limit=5000)
        elif name=='diagnostics':rows=[{'schema_version':2,'database':r.database.diagnostics(),'router':r.router.metrics(),
            'inbox_depth':r.inbox.qsize(),'recovered_unknown':r.orders.recovered,'analytics_errors':r.analytics.scheduler.errors}]
        elif name=='configuration':rows=[r.catalogues.export_configuration()]
        elif name=='capital_context':
            context=r.money.context();rows=[context];status=context['status']
            if epoch:
                extra['candidate_estimates']=[r.money.estimate_candidate(c,v) for c in r.research.query('market_candidate',scope=scope,epoch=epoch,symbol=symbol,as_of=as_of)
                    for v in c['variants']]
        elif name=='optional_exit_capability':status='OPTIONAL_NOT_INSTALLED';detail='Separate addon is not part of the signal core'
        elif name=='annotations':
            for workspace in r.database.list('chart_workspace'):
                if (workspace['scope_id'],workspace['source_epoch'],workspace['symbol'])==(scope,epoch,symbol):
                    rows.extend(dict(n,scope_id=scope,source_epoch=epoch,symbol=symbol,timeframe=workspace['timeframe'],origin='HUMAN_ANNOTATION_NOT_MARKET_EVIDENCE') for n in workspace['settings'].get('notes',[]))
        else:raise ValueError('Unhandled dataset: '+name)
        if q.object_id and name in {'levels','evidence','market_candidates','overlays'}:
            fields=('level_id','evidence_id','candidate_id','overlay_id')
            rows=[v for v in rows if q.object_id in [v.get(f) for f in fields]]
        for key,value in tuple(extra.items()):
            if isinstance(value,list):
                extra[key+'_total']=len(value);extra[key+'_truncated']=len(value)>q.limit
                extra[key]=value[:q.limit]
        if not r.consumers.enabled('display.'+subtab_id):rows=[];status='DISABLED';extra={}
        elif rows and status=='NO_DATA':status='AVAILABLE'
        total=len(rows);page=rows[q.cursor:q.cursor+q.limit]
        fingerprint=digest([name,scope,epoch,symbol,q.timeframe,q.object_id,q.run_id,q.as_of,q.history,rows])
        if q.expected_hash and q.expected_hash!=fingerprint:raise ValueError('Dataset changed; restart pagination at cursor zero')
        return {'schema_version':1,'subtab_id':subtab_id,'dataset':name,'status':status,'detail':detail,
            'scope_id':scope,'source_epoch':epoch,'symbol':symbol,'as_of':as_of,'rows':page,'total':total,
            'next_cursor':q.cursor+len(page) if q.cursor+len(page)<total else None,
            'data_hash':fingerprint,'analytical_history_window_limit':5000 if name in {'levels','evidence','market_candidates','overlays','geometry'} else None,**extra}
