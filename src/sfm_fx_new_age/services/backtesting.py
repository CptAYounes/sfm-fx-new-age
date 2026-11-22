"""Causal marker-based research studies. No account, quote, signal or transport access."""
from bisect import bisect_left
from collections import Counter
from decimal import Decimal
from sfm_fx_new_age.contracts.backtest import StudyRequest,MODEL_VERSION
from sfm_fx_new_age.contracts.domain import Bar,Origin,instant,record,decimal
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.models import freeze


def summary(trades,missing=0):
    counts=Counter(t['outcome'] for t in trades)
    resolved=[decimal(t['r_multiple']) for t in trades if t['r_multiple'] is not None]
    total=sum(resolved,Decimal(0));equity=peak=drawdown=Decimal(0)
    for r in resolved:
        equity+=r;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
    return dict(trades=len(trades),resolved=len(resolved),ambiguous=counts['AMBIGUOUS_INTRABAR'],unresolved=len(trades)-len(resolved),
        wins=sum(r>0 for r in resolved),losses=sum(r<0 for r in resolved),net_r=str(total),mean_r=str(total/len(resolved)) if resolved else None,
        max_closed_trade_drawdown_r=str(drawdown),outcomes=dict(counts),signals_without_causal_entry=missing)


def evaluate_study(replay,request,methods):
    if type(request) is not StudyRequest:raise ValueError('Typed StudyRequest required')
    data=replay.db.get('replay_dataset',request.dataset_id)
    if not data:raise ValueError('Known immutable replay dataset required')
    if digest(data['bars'])!=data['dataset_hash']:raise ValueError('Replay dataset hash mismatch')
    configuration=record(request);old=replay.db.get('research_study',request.study_id)
    if old:
        if old['configuration']!=configuration or old['dataset_hash']!=data['dataset_hash']:raise ValueError('Study identity is immutable')
        return replay.study_result(request.study_id)
    observations=[r for r in data['bars'] if (r['symbol'],r['timeframe'])==(request.symbol,request.timeframe)]
    if not 2<=len(observations)<=2000 or len(observations)!=len(data['bars']):raise ValueError('Study requires 2–2000 original revisions of one pair/timeframe')
    if request.method_id not in methods:raise ValueError('Installed analytical method required')
    definition,handler,factory=methods[request.method_id]
    if definition.data_kind or definition.required_nodes or definition.input_frames:raise ValueError('Historical auxiliary inputs are not supplied by this study')
    configs=replay.parameter_sweep(dict(stop_bps=list(request.stop_bps),reward_r=list(request.reward_r)),max_runs=64)
    if len(configs)*len(observations)>64000:raise ValueError('Historical study work budget exceeded')
    first={}
    for r in sorted(observations,key=lambda r:(instant(r['available_at']),r['revision'])):first.setdefault(r['open_time'],r)
    # This is an explicitly selected historical simulation assumption, NEVER a
    # new observation or an alteration of replay/source data. First revisions
    # prevent later corrected prices entering the historical model unnoticed.
    historical=request.information_clock=='HISTORICAL_CLOSE_ASSUMPTION'
    model_rows=[dict(r,available_at=r['close_time']) for r in first.values()] if historical else observations
    latest={};events=[];last_decision_close=None
    # Every calculation sees only revisions available in its availability batch.
    batches={}
    for r in model_rows:batches.setdefault(instant(r['available_at']),[]).append(r)
    for at in sorted(batches):
        for row in batches[at]:latest[row['open_time']]=row
        prefix=sorted(latest.values(),key=lambda r:instant(r['open_time']))
        end=prefix[-1]['close_time']
        if len(prefix)<definition.warmup or last_decision_close is not None and instant(end)<=last_decision_close:continue
        last_decision_close=instant(end)
        out=handler(factory(prefix,()),freeze(dict(bars={request.timeframe:prefix},symbol=request.symbol,frame=request.timeframe,
            scope_id='REPLAY:'+request.study_id,authority=dict(source_epoch='REPLAY:'+request.study_id,origin='HISTORICAL_REPLAY'),
            _evaluation_at=at.isoformat(),profile_hash=definition.profile_hash)),freeze({}))
        choices=[m for m in out['markers'] if m['side'] in {'BUY','SELL'} and instant(m['available_at'])==at]
        # Conflicting same-time directions are unknown, never a chosen winner.
        if len({m['side'] for m in choices})==1:
            events.append(dict(side=choices[0]['side'],known_at=at.isoformat(),marker_time=choices[0]['time'],
                marker_hash=digest(choices),source_prefix_hash=digest(prefix)))
    # Outcomes use the FIRST observed version, not a future correction of price.
    bars=sorted((dict(r,available_at=r['close_time']) if historical else r for r in first.values()),key=lambda r:instant(r['open_time']));opens=[instant(r['open_time']) for r in bars]
    def simulate(parameters,lo,hi):
        trades=[];missing=0;occupied=-1
        for event in events:
            i=bisect_left(opens,instant(event['known_at']))
            if i>=len(bars):missing+=1;continue
            # Decisions and outcomes must be wholly in this period. No training
            # payoff crossing into test is allowed in model selection.
            if i<lo or i>=hi or i<=occupied:continue
            known=instant(event['known_at']);entry=decimal(bars[i]['open'],positive=True)
            risk=entry*decimal(parameters['stop_bps'])/10000
            side=event['side'];sign=Decimal(1) if side=='BUY' else Decimal(-1)
            stop=entry-sign*risk;target=entry+sign*risk*decimal(parameters['reward_r'])
            t=dict(side=side,decision_at=event['known_at'],marker_time=event['marker_time'],marker_hash=event['marker_hash'],
                source_prefix_hash=event['source_prefix_hash'],entry_at=bars[i]['open_time'],entry_price=str(entry),stop=str(stop),target=str(target),
                exit_at=None,exit_price=None,outcome='OPEN_AT_PERIOD_END',r_multiple=None)
            for j in range(i,min(i+request.holding_bars,hi)):
                row=bars[j];bar=Bar(**row)
                if instant(row['available_at'])>instant(bars[hi-1]['available_at']):break
                op=decimal(row['open']);exit_price=None
                if (op<=stop if side=='BUY' else op>=stop):outcome='STOP_GAP';exit_price=op
                elif (op>=target if side=='BUY' else op<=target):outcome='TARGET_GAP';exit_price=op
                else:
                    outcome=replay.classify_bar_outcome(bar,side,stop,target)
                    if outcome=='STOP_TOUCHED':exit_price=stop
                    elif outcome=='TARGET_TOUCHED':exit_price=target
                    elif outcome=='NEITHER_TOUCHED' and j==i+request.holding_bars-1:outcome='TIME_EXIT';exit_price=decimal(row['close'])
                if outcome!='NEITHER_TOUCHED':
                    if outcome=='AMBIGUOUS_INTRABAR' or exit_price is not None:
                        t.update(outcome=outcome,exit_at=row['available_at'],exit_price=str(exit_price) if exit_price is not None else None)
                        if exit_price is not None:t['r_multiple']=str((sign*(exit_price-entry)-entry*decimal(request.cost_bps)/10000)/risk)
                        occupied=j;break
            else:occupied=min(i+request.holding_bars-1,hi-1)
            if t['exit_at'] is None:occupied=hi-1
            trades.append(t)
        return dict(parameters=parameters,trades=trades,summary=summary(trades,missing))
    runs=[simulate(p,0,len(bars)) for p in configs]
    # Explicit modelled baseline is first configuration, not the ex-post winner.
    if historical:
        times=sorted({b['close_time'] for b in bars},key=instant)
        windows=[dict(train_from=times[i],train_through=times[i+request.train-1],test_from=times[i+request.train],test_through=times[i+request.train+request.test-1]) for i in range(0,len(times)-request.train-request.test+1,request.test)]
    else:windows=replay.walk_forward(request.dataset_id,request.train,request.test)
    folds=[];oos=[]
    for window in windows:
        start,end=instant(window['train_from']),instant(window['train_through'])
        test_start,test_end=instant(window['test_from']),instant(window['test_through'])
        train_ids=[i for i,b in enumerate(bars) if start<=instant(b['available_at'])<=end]
        test_ids=[i for i,b in enumerate(bars) if test_start<=instant(b['available_at'])<=test_end]
        if not train_ids or not test_ids:continue
        training=[simulate(p,min(train_ids),max(train_ids)+1) for p in configs]
        # Unknown outcomes are not gains. Prefer fewer unknowns when resolved
        # training expectancy ties, then the canonical parameter ordering.
        def rank(x):
            s=x['summary'];return (s['resolved']>0,decimal(s['mean_r']) if s['mean_r'] is not None else Decimal('-1e100'),-s['unresolved'])
        chosen=max(range(len(training)),key=lambda k:rank(training[k]));best=training[chosen]
        valid=best['summary']['resolved']>0
        test_run=simulate(configs[chosen],min(test_ids),max(test_ids)+1) if valid else dict(parameters=None,trades=[],summary=summary([]))
        oos.extend(test_run['trades'])
        folds.append(dict(window=window,selection_state='TRAINING_ONLY' if valid else 'NO_RESOLVED_TRAINING_TRADES',selected_parameters=configs[chosen] if valid else None,
            training=[dict(parameters=t['parameters'],summary=t['summary']) for t in training],test=test_run))
    result=dict(study_id=request.study_id,dataset_id=request.dataset_id,dataset_hash=data['dataset_hash'],source_ref=data['source_ref'],configuration=configuration,
        origin='HISTORICAL_REPLAY',original_origin=data['original_origin'],execution_allowed=False,status='COMPLETE',schema_version=1,
        model_version=MODEL_VERSION,method_version=definition.method_version,method_definition_hash=definition.profile_hash,
        information_clock=request.information_clock,original_availability_preserved=True,source_observation_hash=data['dataset_hash'],
        model_input_hash=digest(model_rows),as_observed_execution_proof=False,
        interpretation='Historical marker-to-next-observed-open research model; not original strategy execution equivalence or a profitable edge',
        assumptions=dict(entry='FIRST_ORIGINAL_BAR_OPEN_AT_OR_AFTER_MARKER_AVAILABILITY',risk='FIXED_ENTRY_BASIS_POINTS',intrabar='BOTH_TOUCHES_UNKNOWN',
            gap='FIRST_ORIGINAL_OPEN',overlap='ONE_POSITION_PER_CONFIGURATION_PER_PERIOD',cost='EXPLICIT_MODEL_ROUNDTRIP_BPS_NOT_OBSERVED_COSTS',cost_bps=request.cost_bps,
            windows='AVAILABILITY_BATCHES_TEST_NONOVERLAP_TRAIN_PAYOFF_PURGED_AT_BOUNDARY',source_corrections='CAUSAL_DECISIONS_FIRST_OBSERVED_OUTCOMES',unknown_outcomes='EXCLUDED_FROM_REALIZED_R'),
        bar_revisions=len(observations),unique_bars=len(bars),markers=len(events),backtest=runs[0],parameter_runs=runs,
        walk_forward=dict(folds=folds,summary=summary(oos),selection='RESOLVED_TRAIN_MEAN_R_THEN_FEWER_UNKNOWN_THEN_PARAMETER_ORDER'),
        limitations=['Historical close-time information, if selected, is a modelling assumption—not an observed opportunity','No tick bid/ask fill model; OHLC ambiguity is retained','Price-only marker profiles; supplemental and discretionary entry systems are not invented','Zero model cost is gross, not net profit','Not a broker order, candidate, financial recommendation or profitability certification'])
    result['result_hash']=digest(result)
    if len(str(result))>4000000:raise ValueError('Study output exceeds storage budget')
    replay.db.put('research_study',request.study_id,result)
    replay.emit('REPLAY.STUDY','REPLAY_CLOCK',dict(study_id=request.study_id,result_hash=result['result_hash'],execution_allowed=False))
    return result
