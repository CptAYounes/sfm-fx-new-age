"""Core-owned inspection, local workspace and read-only cross-tab handoff services.
Navigation is not candidate binding, acknowledgement or broker authority.
"""
from copy import deepcopy
from datetime import timedelta
import json,re
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import FRAMES,PAIRS,instant,record,decimal
from sfm_fx_new_age.contracts.registry import load_subtabs

KINDS={'level':'level_id','evidence':'evidence_id','market_candidate':'candidate_id','overlay':'overlay_id'}
SETTINGS={'style','volume','grid','crosshair','show_bid','show_ask','wheel_mode','studies','window','drawings','notes','display'}


class WorkflowService:
    def __init__(self,r):self.r=r;self.current=None
    def capture(self,*,symbol=None,timeframe='D1',as_of=None,object_kind=None,object_id=None,revision=None,run_id=None,scenario=None):
        r=self.r;symbol=symbol or r.selected_pair
        if symbol not in PAIRS or timeframe not in FRAMES:raise ValueError('Known pair and timeframe required')
        if run_id:
            run=r.replay.snapshot(run_id,symbol=symbol,timeframe=timeframe)
            scope=epoch='REPLAY:'+run_id;origin='HISTORICAL_REPLAY';as_of=run['as_of'] or r.clock()
        else:
            authority=r.market.authority(symbol)
            if not authority:raise ValueError('No active market source for inspection')
            scope=r.market.scope_id;epoch=authority['source_epoch'];origin=authority['origin']
        as_of=as_of or r.clock()
        if instant(as_of)>instant(r.clock()):raise ValueError('Inspection time is future-dated')
        if (object_kind is None)!=(object_id is None):raise ValueError('Object kind and identity required together')
        body={'schema_version':1,'scope_id':scope,'source_epoch':epoch,'symbol':symbol,'timeframe':timeframe,'as_of':as_of,
              'origin':origin,'mode':'REPLAY' if run_id else 'MARKET','run_id':run_id,
              'object_kind':object_kind,'object_id':object_id,'revision':revision,'scenario':scenario,'object_hash':None}
        if object_id:
            obj=self.resolve(body)
            if not obj:raise ValueError('Selected object is not available in this source/time')
            body['revision']=revision if revision is not None else obj.get('revision',1)
            body['object_hash']=digest(obj)
        self._validate_scenario(scenario)
        body['context_id']=digest(body);self.validate(body);return deepcopy(body)
    @staticmethod
    def _validate_scenario(scenario):
        if scenario is None:return
        if type(scenario) is not dict or set(scenario)-{'entry','exit','side','lots','contract','pip_size'}:raise ValueError('Only display scenario prices, side and manual contract estimates accepted')
        for k in ('entry','exit','lots','contract','pip_size'):
            if k in scenario:decimal(scenario[k],positive=True)
        if scenario.get('side','BUY') not in {'BUY','SELL'}:raise ValueError('Directional scenario required')
    def with_scenario(self,context,scenario):
        body=self.validate(context)
        if body['mode']!='MARKET' or body['object_kind'] in {'order','broker_pending','position'}:raise ValueError('Broker/replay records cannot become calculator scenarios')
        self._validate_scenario(scenario);body['scenario']=deepcopy(scenario)
        body['context_id']=digest({k:v for k,v in body.items() if k!='context_id'})
        return self.validate(body)
    def validate(self,body):
        body=deepcopy(body)
        expected={'schema_version','scope_id','source_epoch','symbol','timeframe','as_of','origin','mode','run_id','object_kind','object_id','revision','scenario','object_hash','context_id'}
        if set(body)!=expected or body['schema_version']!=1 or body['context_id']!=digest({k:v for k,v in body.items() if k!='context_id'}):raise ValueError('Inspection context changed; recapture it')
        if body['symbol'] not in PAIRS or body['timeframe'] not in FRAMES or instant(body['as_of'])>instant(self.r.clock()):raise ValueError('Invalid inspection coordinates')
        self._validate_scenario(body['scenario'])
        if body['mode']=='REPLAY':
            run=self.r.replay.snapshot(body['run_id'])
            if body['scope_id']!='REPLAY:'+body['run_id'] or body['source_epoch']!=body['scope_id'] or body['origin']!='HISTORICAL_REPLAY':raise ValueError('Replay provenance mismatch')
            if body['object_id']:raise ValueError('Market objects cannot be attached to replay navigation')
            return body
        authority=self.r.market.authority(body['symbol'])
        if body['mode']!='MARKET' or not authority or (body['scope_id'],body['source_epoch'],body['origin'])!=(self.r.market.scope_id,authority['source_epoch'],authority['origin']):raise ValueError('Inspection source changed; return to current source')
        if body['object_id']:
            obj=self.resolve(body)
            if not obj or obj.get('revision',1)!=body['revision'] or digest(obj)!=body['object_hash']:raise ValueError('Selected object revision changed or disappeared')
        return body
    def resolve(self,body):
        kind=body['object_kind'];identity=body['object_id'];r=self.r
        if kind in KINDS:
            rows=r.research.query(kind,scope=body['scope_id'],epoch=body['source_epoch'],symbol=body['symbol'],as_of=body['as_of'],limit=5000)
            matches=[v for v in rows if v[KINDS[kind]]==identity]
            # Historical inspection can display a revision, but stale selections cannot bind later.
            return matches[0] if len(matches)==1 else None
        if kind=='signal':
            v=r.signals.get(identity)
            return v if v and instant(v['available_at'])<=instant(body['as_of']) and (v.get('scope_id'),v.get('source_epoch'),v['symbol'])==(body['scope_id'],body['source_epoch'],body['symbol']) else None
        if kind in {'order','broker_pending','position'}:
            rows=(r.database.orders() if kind=='order' else (r.database.get('broker_pending_snapshot',body['scope_id']) or {}).get('display_orders',[]) if kind=='broker_pending' else (r.positions.snapshot() or {}).get('rows',[]))
            return next((v for v in rows if str(v.get('id') or v.get('broker_order_id') or v.get('position_id'))==identity and v.get('scope_id',body['scope_id'])==body['scope_id'] and v['symbol']==body['symbol']),None)
        raise ValueError('Unknown inspection object kind')
    def navigate(self,target,context):
        body=self.validate(context)
        if target not in {d.subtab_id for d in load_subtabs()} and target!='calculator':raise ValueError('Unknown workspace destination')
        if target.startswith('2.'):raise ValueError('Trading Tools contracts are internal; use a registered tool destination')
        if body['object_kind'] in {'order','broker_pending','position'} and (target.startswith('3.') or target=='calculator'):raise ValueError('Broker/local order context stays in Chart / Trading Operations; select chart context for research or calculator')
        if body['mode']=='REPLAY' and target not in {'1.9','3.12'}:raise ValueError('Replay context stays in isolated Chart Replay / Research Replay; it cannot enter live datasets')
        self.current=body
        if body['mode']=='MARKET':
            self.r.selected_pair=body['symbol'];self.r.database.put('setting','selected_pair',{'value':body['symbol']})
            self.r.emit('UI.SELECTION','GUI_STATE_CONTROLLER',{'symbol':body['symbol']})
        self.r.emit('UI.NAVIGATE','GUI_STATE_CONTROLLER',{'target':target,'context':body})
    def workspace(self,context):
        body=self.validate(context);identity=digest([body[k] for k in ('scope_id','source_epoch','symbol','timeframe')])
        row=self.r.database.get('chart_workspace',identity) or {'version':0,'settings':{}}
        archives=[v for v in self.r.database.list('chart_workspace') if v['scope_id']==body['scope_id'] and v['symbol']==body['symbol'] and v['timeframe']==body['timeframe'] and v['source_epoch']!=body['source_epoch']]
        archives.sort(key=lambda v:(v.get('saved_at',''),v['version']))
        if not row['version'] and archives:
            row['settings']={k:v for k,v in archives[-1]['settings'].items() if k not in {'drawings','notes'}}
        return deepcopy(row)|{'archives':archives[-32:],'archives_total':len(archives),'archives_truncated':len(archives)>32}
    def save_workspace(self,context,settings,expected_version):
        body=self.validate(context)
        if body['mode']!='MARKET':raise ValueError('Replay does not overwrite market workspace notes')
        if type(settings) is not dict or set(settings)-SETTINGS or type(expected_version) is not int or expected_version<0:raise ValueError('Exact local display settings required')
        settings=deepcopy(settings)
        for key in ('volume','grid','crosshair','show_bid','show_ask'):
            if key in settings and type(settings[key]) is not bool:raise ValueError('Boolean display settings required')
        if settings.get('style','Candles') not in {'Candles','OHLC','Line','Dot'} or settings.get('wheel_mode','Zoom') not in {'Zoom','Scroll'}:raise ValueError('Unknown chart preference')
        if set(settings.get('studies',[]))-{'SMA 20','EMA 50'}:raise ValueError('Unknown display study')
        if 'window' in settings and (type(settings['window']) is not int or not 8<=settings['window']<=2000):raise ValueError('Chart window outside display budget')
        from sfm_fx_new_age.contracts.chart_display import validate_drawing,validate_display
        if 'display' in settings:validate_display(settings['display'])
        drawings=settings.get('drawings',[]);notes=settings.get('notes',[])
        if type(drawings) is not list or len(drawings)>100 or type(notes) is not list or len(notes)>100:raise ValueError('Workspace notes exceed budget')
        identities=set()
        for d in drawings:
            validate_drawing(d)
            if d['id'] in identities:raise ValueError('Duplicate local drawing identity')
            identities.add(d['id'])

        for note in notes:
            if set(note)!={'annotation_id','points','text','version'} or type(note['text']) is not str or len(note['text'])>4096 or not 1<=len(note['points'])<=100:raise ValueError('Invalid human note')
            for point in note['points']:instant(point['time']);decimal(point['price'],positive=True)
        if len(json.dumps(settings,allow_nan=False))>100000:raise ValueError('Workspace payload budget exceeded')
        key=digest([body[k] for k in ('scope_id','source_epoch','symbol','timeframe')])
        with self.r.database.transaction() as conn:
            raw=conn.execute("SELECT body FROM records WHERE kind='chart_workspace' AND id=?",(key,)).fetchone()
            old=json.loads(raw[0]) if raw else {'version':0,'settings':{}}
            if old['version']!=expected_version:raise ValueError('Workspace version conflict; reload before saving')
            value={k:body[k] for k in ('scope_id','source_epoch','symbol','timeframe')}
            value.update(settings=old['settings']|settings,version=expected_version+1,saved_at=self.r.clock(),origin='HUMAN_ANNOTATION_NOT_MARKET_EVIDENCE')
            self.r.database.write(conn,'chart_workspace',key,value)
        self.r.emit('UI.WORKSPACE','GUI_STATE_CONTROLLER',{'scope_id':body['scope_id'],'symbol':body['symbol']})
        return value
    def legacy_note(self,p):
        context=self.capture(timeframe=p['timeframe']);ws=self.workspace(context);notes=ws['settings'].get('notes',[])
        old=next((n for n in notes if n['annotation_id']==p['annotation_id']),None)
        if (old or {}).get('version',0)!=p['expected_version']:raise ValueError('Annotation version conflict')
        note={k:p[k] for k in ('annotation_id','points','text')};note['version']=p['expected_version']+1
        return self.save_workspace(context,{'notes':[n for n in notes if n['annotation_id']!=p['annotation_id']]+[note]},ws['version'])
    def replay_from_context(self,context,run_id):
        body=self.validate(context)
        if body['mode']!='MARKET':raise ValueError('Select market history to create a new isolated replay')
        bars=tuple(self.r.market.bars(body['symbol'],body['timeframe'],body['as_of'],body['source_epoch']))
        if not bars or len(bars)>5000:raise ValueError('Bounded nonempty observed history required')
        dataset='INSPECT:'+digest([record(b) for b in bars]);self.r.replay.import_dataset(dataset,bars,source_ref='Observed chart selection '+body['context_id'])
        return self.r.replay.create(run_id,dataset,{'inspection':body})
    def older_history(self,context,days):
        body=self.validate(context)
        if body['mode']!='MARKET' or type(days) is not int or not 1<=days<=366:raise ValueError('Historical request requires 1–366 days, market source only')
        bars=self.r.market.bars(body['symbol'],body['timeframe'],self.r.clock(),body['source_epoch'])
        end=bars[0].open_time if bars else self.r.clock();start=(instant(end)-timedelta(days=days)).isoformat().replace('+00:00','Z')
        if not self.r.fixture_mode:
            account=self.r.accounts.current;state=self.r.connector.native.get((account.endpoint_class,account.account_id),{}) if account else {}
            if not state.get('connected') or state.get('epoch')!=body['source_epoch']:raise ValueError('Current authenticated native connection required')
            spec=self.r.market.spec(account.account_id,body['symbol']);calendar=self.r.continuity.calendar(body['symbol'])
            if not spec or str(spec.broker_symbol_id) not in {str(k) for k in state.get('specs',{})} or not calendar or calendar.source_ref!='ProtoOASymbol.schedule / '+body['source_epoch']:raise ValueError('Current-epoch native symbol and session metadata required')
        job=self.r.continuity.request_backfill(body['symbol'],body['timeframe'],start,end)
        if not self.r.fixture_mode and job['status']=='QUEUED' and not any((v.get('context') or {}).get('job_id')==job['id'] for v in self.r.connector.requests.values()):self.r.connector.start_backfill(job)
        return job
