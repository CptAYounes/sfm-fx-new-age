"""Narrow install-time capability for trusted Tab 3 analytical code, not a Python sandbox."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import json

from sfm_fx_new_age.contracts.analytics import ParameterDefinition,MutableSurface,Recipe,MarketCandidate,digest,VariableDefinition
from sfm_fx_new_age.contracts.domain import FRAMES,record,instant
from sfm_fx_new_age.contracts.extensions import AnalyticalResult
from sfm_fx_new_age.contracts.models import freeze
from sfm_fx_new_age.services.scanner import Computation


class AnalyticalExtensionApi:
    def __init__(self,analytics,catalogues,research):
        self.__analytics,self.__catalogues,self.__research=analytics,catalogues,research
        analytics.research=research
        self.__closed=False
        self.__variable_owners={}

    def _check(self):
        if self.__closed:raise RuntimeError('Analytical installation window has closed')

    def register_parameter(self,definition:ParameterDefinition,*,validator=None):
        self._check()
        if definition.owner!='STRATEGY_RECIPE_HOST':raise ValueError('Tab 3 cannot own another service configuration')
        self.__catalogues.register_parameter(definition,validator)

    def register_variable(self,node_id:str,definition:VariableDefinition):
        self._check()
        if (node_id not in self.__analytics.scheduler.nodes or self.__analytics.scheduler.nodes[node_id]['layer']!='sensor'
            or definition.owner!='STRATEGY_RECIPE_HOST' or not definition.symbol or not definition.timeframe):raise ValueError('Source sensor-owned pair/timeframe variable required')
        if definition.key in self.__variable_owners and self.__variable_owners[definition.key]!=node_id:raise ValueError('Variable producer cannot be rebound')
        self.__catalogues.register_variable_definition(definition)
        self.__variable_owners[definition.key]=node_id

    def register_surface(self,surface:MutableSurface):
        self._check()
        if not surface.subtab_id.startswith('3.'):raise ValueError('Analytical surface must belong to Tab 3')
        self.__catalogues.register_surface(surface)

    def register_producer(self,node_id:str,handler:Callable,*,method_version:str,source_ref:str,trigger_frames:tuple[str,...],enabled_by_recipe:str|None=None):
        self._check();analytics=self.__analytics;scheduler=analytics.scheduler
        if (node_id not in scheduler.nodes or scheduler.nodes[node_id]['layer']!='sensor' or not method_version or not source_ref
            or not trigger_frames or any(f not in FRAMES for f in trigger_frames)):
            raise ValueError('Source-backed declared sensor and explicit trigger frames required')
        if node_id in scheduler.handlers:raise ValueError('Existing producer authority cannot be overridden')
        def execute(inputs,dependencies):
            selected,selected_dependencies=selector(inputs,dependencies)
            selected['_evaluation_at']=inputs['_evaluation_at']
            selected['prior_objects']={kind:[row for row in self.__research.query(kind,scope=inputs['scope_id'],
                epoch=inputs['authority']['source_epoch'],symbol=inputs['symbol'],as_of=inputs['_evaluation_at'])
                if row['lineage']['method_version']==method_version] for kind in ('level','evidence','overlay')}
            result=handler(freeze(selected),freeze(selected_dependencies))
            if type(result) is not AnalyticalResult:raise ValueError('Typed analytical result required')
            if len(json.dumps(result.value,allow_nan=False))>1000000:raise ValueError('Analytical value exceeds serialized output budget')
            if result.state!='EVALUATED':return Computation({'NO_DATA':'NO_DATA','WARMUP':'WARMUP','UNSUPPORTED':'UNAVAILABLE'}[result.state],None,result.reason)
            for item in result.objects:
                line=item.lineage
                if (line.source_scope,line.source_epoch,line.symbol,line.method_version)!=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],method_version):
                    raise ValueError('Analytical output source/method lineage mismatch')
                if line.profile_hash!=inputs['profile_hash'] or instant(line.available_at)>instant(inputs['_evaluation_at']):raise ValueError('Analytical output profile/causality mismatch')
            for update in result.variables:
                definition=self.__catalogues.variables.get(update.key)
                if self.__variable_owners.get(update.key)!=node_id or not definition or definition.symbol!=inputs['symbol'] or definition.timeframe not in trigger_frames:
                    raise ValueError('Variable source ownership mismatch')
                if instant(update.available_at)>instant(inputs['_evaluation_at']):raise ValueError('Future variable observation')
            self.__research.publish_many(result.objects)
            for update in result.variables:
                definition=self.__catalogues.variables[update.key]
                self.__catalogues.register_variable(update.key,update.value,definition.unit,owner=definition.owner,
                    available_at=update.available_at,source_epoch=inputs['authority']['source_epoch'],scope_id=inputs['scope_id'],freshness=update.freshness)
            return Computation('READY',result.value)
        def selector(inputs,dependencies):
            selected={k:v for k,v in inputs.items() if not k.startswith('_')}
            selected['bars']={f:rows for f,rows in inputs['bars'].items() if f in trigger_frames}
            times=[row['available_at'] for rows in selected['bars'].values() for row in rows]
            selected['cutoff']=max(times,key=instant) if times else None
            def relevant(output):
                if isinstance(output,dict) and set(output).issubset(set(FRAMES)):
                    return {key:value for key,value in output.items() if key in trigger_frames}
                return output
            return selected,{key:{'state':value.state,'output':relevant(value.output)} for key,value in dependencies.items()}
        scheduler.register(node_id,execute,selector=selector)
        analytics.producer_metadata[node_id]={'method_version':method_version,'source_ref':source_ref,'trigger_frames':list(trigger_frames)}
        if enabled_by_recipe:
            analytics.producer_metadata[node_id]['enabled_by_recipe']=enabled_by_recipe

    def register_recipe(self,recipe:Recipe,composer:Callable,*,selection_upgrade_from_version:int|None=None):
        self._check()
        if any(node not in self.__analytics.scheduler.nodes for node in recipe.required_nodes):raise ValueError('Recipe has unknown required producers')
        if recipe.recipe_id in self.__analytics.composers:raise ValueError('Recipe implementation already owned')
        if selection_upgrade_from_version is not None and (type(selection_upgrade_from_version) is not int or selection_upgrade_from_version<1 or selection_upgrade_from_version+1!=recipe.version):
            raise ValueError('Explicit adjacent recipe selection upgrade required')
        self.__research.publish(recipe)
        # Publish the new immutable definition first. A declared compatible
        # install-time upgrade preserves an existing literal on/OFF choice;
        # absent, malformed or unknown-version preferences are never invented.
        if selection_upgrade_from_version is not None:
            db=self.__research.db
            state=db.get('recipe_state',recipe.recipe_id)
            if state and state.get('version')==selection_upgrade_from_version and type(state.get('enabled')) is bool:
                db.put('recipe_state',recipe.recipe_id,dict(state,version=recipe.version))
        self.__analytics.composers[recipe.recipe_id]=(recipe,composer)

    def register_projection_method(self,definition,handler,feature_factory):
        from sfm_fx_new_age.contracts.public_strategies import ProjectionMethod
        self._check()
        if type(definition) is not ProjectionMethod or not definition.sources or definition.warmup<1:
            raise ValueError('Versioned independently documented projection required')
        self.__analytics.projections.register(definition,handler,feature_factory)

    def close(self):self.__closed=True
