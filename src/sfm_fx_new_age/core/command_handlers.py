"""Non-broker shared command owners. Presentation workers never need raw service handles."""
from __future__ import annotations
from pathlib import Path
import json

from sfm_fx_new_age.contracts.domain import Bar,FRAMES,PAIRS,instant,symbol_check
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.connector.oauth import OAuthConfig,SecretStore

PARAMETER_COMMANDS={'TUNE_H4','TUNE_RULES','TUNE_BANDS','TUNE_QUALIFIER'}


class SharedCommandHandlers:
    def __init__(self,runtime):self.r=runtime

    def dispatch(self,command,p)->str|None:
        r=self.r;name=command.name
        if name=='SET_RESEARCH_POLICY':
            if not r.accounts.current or p['expected_scope_id']!=r.accounts.current.scope_id:raise ValueError('Selected account changed; reload the research policy')
            body=r.money.set_policy(p['policy'],expected_version=p['expected_version'])
            return 'Research-only monetary policy version '+str(body['version'])+' saved; no account-risk permission or broker operation'
        if name in {'IMPORT_CTRADER_PROFILE','IMPORT_CTRADER_SESSION','REMEMBER_CTRADER_LOGIN','SIGN_OUT_CTRADER'}:
            if r.fixture_mode:raise ValueError('Fixture session cannot modify a real login')
            if name=='IMPORT_CTRADER_PROFILE':
                r.connector.import_profile(Path(p['path']).expanduser());return 'Application configured; no login or network started'
            if name=='IMPORT_CTRADER_SESSION':
                r.connector.import_session(Path(p['path']).expanduser());return 'Application linked; renewing authorization and discovering accounts asynchronously. No order request.'
            if name=='REMEMBER_CTRADER_LOGIN':
                r.connector.remember(p['enabled']);return 'Automatic cTrader login preference saved'
            r.connector.sign_out();return 'Saved cTrader login removed; no broker order changed'
        if name=='REFRESH_HISTORY' and ('start' in p or 'end' in p):
            if set(p)!={'start','end'}:raise ValueError('Native history requires both bounds, without order_id')
            account=r.accounts.current
            if not account or not account.authenticated:raise ValueError('Authenticated selected account required')
            state=r.connector.native.get((account.endpoint_class,account.account_id),{})
            if not state.get('connected'):raise ValueError('Native history connector is not connected')
            job=r.connector.history.start(account,state['epoch'],p['start'],p['end'])
            return 'Read-only native history '+job['id']+' requested; completeness is not yet known'
        if name in {'CONNECT','RECONNECT'}:
            if r.fixture_mode:raise ValueError('Fixture session cannot connect to real accounts')
            r.connector.connect();return 'Asynchronous connection requested; inspect connector state'
        if name=='HUMAN_OAUTH_LOGIN':
            if r.fixture_mode:raise ValueError('Fixture session cannot start real OAuth')
            if p:
                if not {'client_id','redirect_uri'}<=set(p):raise ValueError('Public client ID and registered redirect required together')
                if r.database.path==':memory:':raise ValueError('Persistent application state directory required for OAuth configuration')
                store=SecretStore(Path(p['credential_path']).expanduser() if p.get('credential_path') else Path(r.database.path).parent/'private'/'connector-secrets.json')
                try:
                    credential=store.load()
                except (OSError,ValueError):raise ValueError('Choose an existing private credential JSON file: file mode 0600, parent directory 0700') from None
                if not credential.get('client_secret'):raise ValueError('Private application credential file must contain client_secret')
                r.connector.configure(OAuthConfig(p['client_id'],p['redirect_uri'],p.get('scope','accounts')),store)
            r.connector.begin_oauth();return 'Human OAuth URL is available through the connector snapshot; no order operation'
        if name=='START_MARKET_FEED':
            if r.fixture_mode:raise ValueError('Fixture data cannot start a real feed')
            r.connector.start_market_feed();return 'Read-only quotes and initial chart history requested; inspect feed status'
        if name=='DISCONNECT_FEED':
            r.connector.disconnect();return 'cTrader feed disconnected; persisted observations remain last-known only'
        if name=='REQUEST_BACKFILL':
            job=r.continuity.request_backfill(p['symbol'],p['timeframe'],p['start'],p['end'])
            if r.connector.workers:r.connector.start_backfill(job)
            return 'Backfill '+job['id']+': '+job['status']
        if name=='ENABLE_PAIR':
            symbol_check(p['symbol']);r.consumers.set_enabled('analysis.pair.'+p['symbol'],p['enabled'])
            r._analytics_dirty.add(p['symbol']);return 'Pair analytical consumer changed; native order/position monitoring remains enabled'
        if name=='START_STOP_NONCRITICAL':
            r.consumers.set_enabled(p['consumer_id'],p['enabled'])
            r._analytics_dirty.update(PAIRS);return 'Registered noncritical consumer changed'
        if name=='OPEN_OWNER_EDITOR':
            surface=r.catalogues.surfaces.get(p['surface_id'])
            if not surface:raise ValueError('Unknown mutable surface')
            r.emit('UI.OWNER_EDITOR','GUI_STATE_CONTROLLER',{'surface_id':surface.surface_id,'owner':surface.owner,'subtab_id':surface.subtab_id})
            return 'Owner editor: '+surface.subtab_id
        if name in PARAMETER_COMMANDS:
            definition=r.catalogues.parameters.get(p['key'])
            if not definition or definition.owner!=command.target_component:raise ValueError('Parameter is not owned by this editor')
            body=r.catalogues.set_parameter(p['key'],p['value'],expected_version=p['expected_version'])
            return f"Parameter {body['key']} version {body['version']}"
        if name=='SAVE_PREVIEW_ACTIVATE_RULE':
            action=p.get('action','preview');c=r.catalogues
            if action=='preview':return 'Pure preview: '+c.preview_rule(p['rule_id'],p['rule'],as_of=r.clock())['preview']
            if 'expected_version' not in p:raise ValueError('Explicit expected_version required for rule mutation')
            if action=='save':
                body=c.save_rule(p['rule_id'],p['rule'],expected_version=p['expected_version'],output=p.get('output','DISPLAY'))
                return 'Draft rule version '+str(body['version'])+' saved; active version unchanged'
            if action in {'activate','rollback'}:
                c.activate_rule(p['rule_id'],p['version'],expected_version=p['expected_version'])
                return 'Saved analytical rule version activated; no execution outputs permitted'
            if action=='suspend':
                old=c.db.get('rule',p['rule_id'])
                if not old or old['version']!=p['expected_version']:raise ValueError('Rule version conflict')
                c.suspend_rule(p['rule_id']);return 'Rule suspended'
            raise ValueError('Unknown rule lifecycle action')
        if name=='START_REPLAY':
            action=p.get('action','create')
            if action=='import':
                if not p.get('bars') or len(p['bars'])>100000:raise ValueError('Bounded nonempty replay bars required')
                r.replay.import_dataset(p['dataset_id'],tuple(Bar(**b) for b in p['bars']),source_ref=p['source_ref'])
                return 'Immutable replay dataset imported; broker execution is unavailable to replay'
            if action!='create':raise ValueError('Unknown replay action')
            r.replay.create(p['run_id'],p['dataset_id'],p.get('configuration',{}))
            return 'Isolated replay run created, paused'
        if name=='START_PAUSE_STEP':
            body=r.replay.control(p['run_id'],p['action'],cursor=p.get('cursor'))
            return f"Replay {body['state']}; cursor {body['cursor']}"
        if name=='SELECT_OOS':
            splits=r.replay.walk_forward(p['dataset_id'],p['train'],p['test'])
            body={'dataset_id':p['dataset_id'],'train':p['train'],'test':p['test'],'splits':splits,'classification':'RESEARCH_UNCALIBRATED'}
            r.database.put('walk_forward',digest(body),body)
            return str(len(splits))+' chronological train/test windows recorded; no inferred fills or returns'
        if name=='ENABLE_OPTIONAL_SENSOR':
            node=p['node_id'];identity='analysis.node.'+node
            if identity not in r.consumers.owners:raise ValueError('Only registered optional analytical methods can be switched')
            r.consumers.set_enabled(identity,p['enabled']);r._analytics_dirty.update(PAIRS)
            return 'Requested method state changed; inspect runtime capability before treating it as available'
        if name=='ENABLE_RECIPE':
            rows=[v for v in r.research.recipes() if v['recipe_id']==p['recipe_id'] and v['version']==p['version']]
            if len(rows)!=1:raise ValueError('Known source-backed recipe version required')
            body={'recipe_id':p['recipe_id'],'version':p['version'],'enabled':p['enabled']}
            r.database.put('recipe_state',p['recipe_id'],body);r._analytics_dirty.update(PAIRS)
            r.emit('CONFIG.VERSION','STRATEGY_RECIPE_HOST',body)
            return 'Research recipe state changed; absent prerequisites remain blockers'
        if name=='SELECT_METHOD':
            if p['node_id'] not in r.analytics.scheduler.nodes:raise ValueError('Unknown method identity')
            r.database.put('setting','selected_method',{'value':p['node_id']})
            r.emit('UI.SELECTION','GUI_STATE_CONTROLLER',{'method_id':p['node_id']})
            return 'Selected source-declared method'
        if name=='CONFIRM_SELECTED_SIGNAL':
            preview=r.orders.preview(p['signal_id'],p['revision'],acknowledge_research=p.get('acknowledge_research',False))
            return 'Preflight '+preview['preview_hash']+' valid; use Issue deliberately to send a pending order'
        if name=='BIND_RESEARCH_CANDIDATE':
            body=r.candidate_binding.bind(**p)
            return 'Local signal '+body['signal_id']+' revision '+str(body['revision'])+' queued; no broker request sent'
        if name=='DRAW_ANNOTATION':
            r.workflow.legacy_note(p)
            return 'Human chart note saved in the shared local workspace; never market evidence'
        if name=='SELECT_LEVEL':
            from sfm_fx_new_age.contracts.tab_data import DataRequest
            levels=r.query_data(command.source_view,DataRequest('levels',object_id=p['level_id']))
            if not levels['rows']:raise ValueError('No causally available level in current source scope')
            r.emit('UI.SELECTION','GUI_STATE_CONTROLLER',{'level_id':p['level_id']})
            return 'Selected source-owned level'
        if name=='EXPORT_IMPORT_CONFIG':
            if p['action']=='export':return 'Read-only configuration available through the configuration dataset'
            if p['action']!='import':raise ValueError('Unknown configuration action')
            r.catalogues.import_configuration(p['configuration'],p['expected_versions'])
            return 'Owner-validated configuration imported atomically; no authentication or broker state imported'
        return None
