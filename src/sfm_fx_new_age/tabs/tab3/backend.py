"""Headless analytical contribution. No GUI, transport or runtime handles."""
from decimal import Decimal
from sfm_fx_new_age.contracts.analytics import Recipe,ParameterDefinition,digest
from sfm_fx_new_age.contracts.domain import FRAMES
from .order_blocks import PROFILE,METHOD,RECIPE_ID,SOURCE_REF,structure_producer,order_block_producer
from .candidates import CANDIDATE_RECIPE,compose_candidates


def install(api):
    for key,kind,lo,hi,default in (
        ('lookback','integer',2,100,14),('body_fraction','number','0.01','1','0.60'),
        ('range_multiple','number','0.01',10,'1.00'),('source_lookback','integer',1,100,20)):
        api.register_parameter(ParameterDefinition('order_block.'+key,'STRATEGY_RECIPE_HOST',kind,'RESEARCH_PROFILE',
            minimum=Decimal(lo),maximum=Decimal(hi),default=default))
    api.register_producer('SMC_STRUCTURE',structure_producer,method_version='SFM_CLOSED_PIVOT_BREAK_RESEARCH_V1',
                          source_ref=SOURCE_REF,trigger_frames=FRAMES)
    api.register_producer('ORDER_BLOCK',order_block_producer,method_version=METHOD,source_ref=SOURCE_REF,trigger_frames=FRAMES,
                          enabled_by_recipe=RECIPE_ID)
    api.register_recipe(Recipe(RECIPE_ID,1,'Order Block · confirmed pivot-break research zones',('ORDER_BLOCK',),
                               SOURCE_REF,digest(PROFILE)),lambda inputs,deps:())
    for key,kind,lo,hi,default in (
        ('expiry_seconds','integer',60,604800,14400),('max_spread_pips','number','0.01',100,'3'),
        ('min_reward_r','number','0.01',100,'1'),('evidence_reliability','number','0.01',1,'0.75')):
        api.register_parameter(ParameterDefinition('ob_candidate.'+key,'STRATEGY_RECIPE_HOST',kind,'RESEARCH_PROFILE',
            minimum=Decimal(lo),maximum=Decimal(hi),default=default))
    api.register_recipe(Recipe(CANDIDATE_RECIPE,1,'Order Block · D1 campaign / H4 candidate qualification',
        ('ORDER_BLOCK','SMC_STRUCTURE','SWING_MAP','RANGE_VOL'),SOURCE_REF+'#10',digest([PROFILE,'MTF_RESEARCH_V1'])),compose_candidates)
    from sfm_fx_new_age.contracts.public_strategies import METHODS
    from .public_features import Features
    from .public_algorithms import evaluate
    from functools import partial
    for method in METHODS:
        api.register_projection_method(method,partial(evaluate,method.key),Features)
        if method.key!='order_block':
            api.register_recipe(Recipe(method.recipe_id,method.version,method.name,('FEATURE_CACHE',),
                ';'.join(method.sources),method.profile_hash),lambda inputs,deps:(),
                selection_upgrade_from_version=1 if method.key=='dom_imbalance' and method.version==2 else None)
