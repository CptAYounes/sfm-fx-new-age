"""CPU-only projection math. No database, connector, Qt or execution handles."""
from sfm_fx_new_age.contracts.models import freeze
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable


def calculate(entries,inputs,deps,results,*,registered=None):
    # Loaded here so importing the scheduling policy starts no analytical work.
    from sfm_fx_new_age.contracts.public_strategies import BY_KEY
    from sfm_fx_new_age.tabs.tab3.public_features import Features
    from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
    from sfm_fx_new_age.services.public_projections import PublicProjectionService
    from functools import partial
    features={};immutable=freeze(inputs);immutable_deps=freeze(deps);bodies=[];runs={};builds=0
    for body in entries:
        body=dict(body);key=body['strategy_id'];frame=body['timeframe']
        definition,handler,factory=(registered[key] if registered is not None else (BY_KEY[key],partial(evaluate,key),Features))
        rows=list(inputs['bars'][frame])[-2048:]
        unavailable=[k for k in definition.required_nodes if k not in results or results[k]['state'] not in {'READY','DEGRADED'}]
        if len(rows)>=definition.warmup and unavailable:
            body.update(state='UNAVAILABLE',reason='Required analytical owner not ready: '+', '.join(unavailable))
        elif len(rows)>=definition.warmup:
            try:
                feature_key=factory
                if feature_key not in features:
                    swings=deps.get('SWING_MAP',{}).get('output') or {};features[feature_key]=factory(rows,swings.get(frame,()));builds+=1
                output=handler(features[feature_key],immutable,immutable_deps)
                if not isinstance(output,dict) or set(output)!={'series','zones','markers','metrics'}:
                    raise ValueError('Only bounded analytical geometry fields permitted')
                body.update(output);PublicProjectionService._validate(body,inputs['_evaluation_at'])
                if body['metrics'].get('alternative'):
                    body['name']=body['metrics']['interpretation_name'];body['classification']='EXPLICIT_ACTIVITY_ALTERNATIVE_NOT_GENUINE_EXECUTION_FLOW'
                elif body['metrics'].get('genuine_displayed_depth'):
                    body['name']=body['metrics']['interpretation_name'];body['classification']='BROKER_SCOPED_DISPLAYED_DEPTH_NOT_EXECUTED_VOLUME'
                has_output=any(body[k] for k in ('series','zones','markers'))
                if key=='order_block':
                    node=results.get('ORDER_BLOCK');ready=node and node['state']=='READY'
                    found=bool(ready and node['output'] and node['output'].get('frames',{}).get(frame))
                    body['state']='READY' if found else 'NO_SETUP' if ready else 'WARMUP'
                    body['reason']='Typed ORDER_BLOCK levels use the existing causal projection owner' if ready else 'Waiting for structure / displacement prerequisites'
                else:body.update(state='READY' if has_output else 'NO_SETUP',reason='' if has_output else 'Evaluated; no qualifying closed-bar pattern')
            except ProjectionInputUnavailable as exc:
                body.update(state=exc.state,reason=exc.reason,series=[],zones=[],markers=[],metrics={})
            except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
                body.update(state='ERROR',reason=type(exc).__name__,series=[],zones=[],markers=[],metrics={})
            runs[key]=runs.get(key,0)+1
        bodies.append(body)
    return dict(bodies=bodies,runs=runs,feature_builds=builds)


def compute_frame(job):
    import os,time
    begin=time.process_time()
    result=calculate(job['entries'],job['inputs'],job['deps'],job['results'])
    return dict(result,token=job['token'],pid=os.getpid(),cpu_seconds=time.process_time()-begin)
