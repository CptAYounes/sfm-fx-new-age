from __future__ import annotations

import json
from typing import Any
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.domain import record, instant, decimal
from sfm_fx_new_age.contracts.analytics import VariableDefinition, ParameterDefinition, MutableSurface, digest
from sfm_fx_new_age.storage.database import Database, StateConflict
from .rules import Truth, evaluate_rule, validate_rule


class CatalogueService:
    """Single owner registry and atomic configuration/rule lifecycle. No broker authority."""
    OUTPUTS = frozenset({'DISPLAY', 'OBSERVATION', 'NOTIFICATION', 'PARAMETER_PROPOSAL'})

    def __init__(self, db: Database, emit: Any, scope=lambda: 'UNBOUND', enabled=lambda: True, clock=None) -> None:
        self.db, self.emit = db, emit
        self.parameters: dict[str, ParameterDefinition] = {}
        self.variables: dict[str, VariableDefinition] = {}
        self.surfaces: dict[str, MutableSurface] = {}
        self.validators: dict[str, Any] = {}
        self.scope = scope
        self.enabled = enabled
        from sfm_fx_new_age.contracts.models import utc_now
        self.clock=clock or utc_now
        for row in db.list('variable_definition'):
            definition = VariableDefinition(**row)
            self.variables[definition.key] = definition

    def values(self) -> list[dict[str, Any]]:
        rows=[r for r in self.db.list('variable') if r.get('scope_id') == self.scope()]
        from .market import market_key
        for row in rows:
            definition=self.variables.get(row['key'])
            if not definition:continue
            row['max_age_seconds']=definition.max_age_seconds
            if definition.symbol:
                authority=self.db.get('authority',market_key(self.scope(),definition.symbol))
                if not authority or row['source_epoch']!=authority['source_epoch']:
                    row['freshness']='STALE';row['stale_reason']='SOURCE_EPOCH_CHANGED'
        return rows

    def parameter_value(self, key: str) -> Any:
        if key not in self.parameters: raise ValueError('Unknown parameter')
        current = self.db.get('parameter', key)
        return current['value'] if current else self.parameters[key].default

    def register_parameter(self, definition: ParameterDefinition, validator=None) -> None:
        if definition.key in self.parameters and self.parameters[definition.key] != definition:
            raise ValueError('Parameter owner/definition cannot be rebound')
        self.parameters[definition.key] = definition
        if validator: self.validators[definition.key] = validator
        self.db.put('parameter_definition', definition.key, record(definition))

    def pair_parameters(self, symbol: str) -> list[dict]:
        from sfm_fx_new_age.contracts.domain import symbol_check
        symbol_check(symbol)
        return [r for r in self.db.list('pair_parameter') if r['scope_id']==self.scope() and r['symbol']==symbol]

    def set_pair_parameter(self, key, value, *, symbol, expected_version, expected_scope_id):
        from sfm_fx_new_age.contracts.domain import symbol_check
        symbol_check(symbol)
        if expected_scope_id!=self.scope() or expected_scope_id=='UNBOUND':raise ValueError('Selected account changed; reload the pair profile')
        d=self.parameters.get(key)
        if not d or d.owner!='STRATEGY_RECIPE_HOST':raise ValueError('Only registered research-host parameters permit pair overrides')
        d.validate(value);json.dumps(value,allow_nan=False)
        if key in self.validators:self.validators[key](value)
        identity=json.dumps([self.scope(),symbol,key]);body={'key':key,'value':value,'symbol':symbol,'scope_id':self.scope(),
            'version':expected_version+1,'owner':d.owner,'effect_boundary':d.activation_boundary,'status':'EFFECTIVE'}
        with self.db.transaction() as conn:
            old=self.db.get('pair_parameter',identity)
            if (old or {}).get('version',0)!=expected_version:raise StateConflict('Pair parameter version conflict')
            self.db.write(conn,'pair_parameter',identity,body)
            self.db.write(conn,'pair_parameter_revision',json.dumps([self.scope(),symbol,key,body['version']]),body)
        self.emit('PARAM.EFFECTIVE','GLOBAL_PARAMETER_REGISTRY',{'changes':[body],'symbols':[symbol]},Priority.P2)
        return body

    def register_surface(self, surface: MutableSurface) -> None:
        for key in surface.parameter_keys:
            if key not in self.parameters or self.parameters[key].owner != surface.owner:
                raise ValueError('Mutable surface must reference same-owner registered parameters')
        if surface.surface_id in self.surfaces and self.surfaces[surface.surface_id] != surface:
            raise ValueError('Surface cannot be rebound')
        self.surfaces[surface.surface_id] = surface
        self.db.put('mutable_surface', surface.surface_id, record(surface))

    def set_parameter(self, key: str, value: Any, *, expected_version: int) -> dict[str, Any]:
        return self.set_parameters({key: (value, expected_version)})[0]

    def set_parameters(self, changes: dict[str, tuple[Any, int]]) -> list[dict[str, Any]]:
        if not changes: raise ValueError('At least one parameter change required')
        for key, (value, version) in changes.items():
            if key not in self.parameters: raise ValueError('Unknown parameter owner')
            if type(version) is not int or version < 0: raise ValueError('Invalid parameter version')
            self.parameters[key].validate(value)
            json.dumps(value, allow_nan=False)
            if key in self.validators: self.validators[key](value)
        if any(key.startswith('geometry.band_') for key in changes):
            bounds = [decimal(changes[f'geometry.band_{i}'][0]) if f'geometry.band_{i}' in changes else
                      decimal(self.parameter_value(f'geometry.band_{i}')) for i in range(5)]
            if sorted(set(bounds)) != bounds: raise ValueError('ATR bands must be strictly increasing')
        bodies=[]
        with self.db.transaction() as conn:
            for key,(value,expected) in changes.items():
                row=conn.execute("SELECT body FROM records WHERE kind='parameter' AND id=?",(key,)).fetchone()
                old=json.loads(row[0]) if row else {'version':0}
                if old['version']!=expected: raise StateConflict('Parameter version conflict')
                body={'key':key,'value':value,'version':expected+1,'owner':self.parameters[key].owner,
                      'effect_boundary':self.parameters[key].activation_boundary,'status':'EFFECTIVE'}
                self.db.write(conn,'parameter',key,body)
                self.db.write(conn,'parameter_revision',json.dumps([key,expected+1]),body)
                bodies.append(body)
        self.emit('PARAM.EFFECTIVE','GLOBAL_PARAMETER_REGISTRY',{'changes':bodies},Priority.P2)
        return bodies

    def register_variable_definition(self, definition: VariableDefinition) -> None:
        if definition.key in self.variables and self.variables[definition.key] != definition:
            raise ValueError('Variable definition cannot be rebound')
        self.variables[definition.key] = definition
        self.db.put('variable_definition', definition.key, record(definition))

    def set_variable(self, key: str, value: Any, unit: str, *, freshness: str = 'CURRENT') -> None:
        """Compatibility producer ingress; new producers register typed definitions first."""
        self.register_variable(key, value, unit, freshness=freshness)

    def register_variable(self, key: str, value: Any, unit: str, *, freshness: str = 'CURRENT',
                          owner: str = 'TEST_OR_LEGACY', available_at: str | None = None,
                          source_epoch: str = 'UNBOUND', scope_id: str | None = None) -> None:
        scope_id = self.scope() if scope_id is None else scope_id
        if scope_id != self.scope(): raise ValueError('Variable publication must match the active source scope')
        if key not in self.variables:
            inferred='boolean' if type(value) is bool else 'number' if type(value) in {int,float} else 'string'
            self.register_variable_definition(VariableDefinition(key, owner, inferred, unit, 'GLOBAL'))
        definition=self.variables[key]
        if definition.owner != owner or definition.unit != unit: raise ValueError('Variable owner/unit mismatch')
        if definition.data_type=='boolean' and type(value) is not bool: raise ValueError('Boolean value required')
        if definition.data_type=='integer' and type(value) is not int: raise ValueError('Integer value required')
        if definition.data_type in {'string','enum'} and type(value) is not str:raise ValueError('String value required')
        if definition.data_type=='number': decimal(value)
        if definition.symbol and (not available_at or source_epoch == 'UNBOUND'):
            raise ValueError('Market variable requires causal source epoch and availability')
        if available_at: instant(available_at)
        if freshness not in {'CURRENT','STALE','MISSING','ERROR'}: raise ValueError('Unknown freshness')
        storage_key=json.dumps([scope_id,key])
        old=self.db.get('variable',storage_key)
        if old and old.get('scope_id')==scope_id and old.get('source_epoch')==source_epoch and old.get('available_at') and available_at and instant(available_at)<instant(old['available_at']):
            raise ValueError('Variable publication cannot regress availability')
        body={'key':key,'value':value,'unit':unit,'freshness':freshness,'owner':owner,
              'available_at':available_at,'source_epoch':source_epoch,'scope_id':scope_id,
              'revision':(old or {}).get('revision',0)+1}
        history=[] if not old or old.get('scope_id')!=scope_id or old.get('source_epoch')!=source_epoch else list(old.get('history',[]))
        body['history']=(history+[{k:v for k,v in body.items() if k!='history'}])[-129:]
        self.db.put('variable',storage_key,body)
        self.emit('VARIABLE.CATALOGUE','GLOBAL_VARIABLE_REGISTRY',{'variables':[body]},Priority.P2)
        self.evaluate_active(key)

    def preview_rule(self, rule_id: str, rule: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
        references=validate_rule(rule)
        values={row['key']:row for row in self.values()}
        result=evaluate_rule(rule,values,as_of=as_of)
        return {'rule_id':rule_id,'rule':rule,'preview':result.value,'active':False,'references':list(references)}

    def save_rule(self, rule_id: str, rule: dict[str, Any], *, expected_version: int | None = None,
                  output: str = 'DISPLAY') -> dict[str, Any]:
        if output not in self.OUTPUTS: raise ValueError('Rule outputs cannot publish broker commands')
        body=self.preview_rule(rule_id,rule)
        with self.db.transaction() as conn:
            row=conn.execute("SELECT body FROM records WHERE kind='rule' AND id=?",(rule_id,)).fetchone()
            old=json.loads(row[0]) if row else {}
            if expected_version is not None and old.get('version',0)!=expected_version: raise StateConflict('Rule version conflict')
            body.update(version=old.get('version',0)+1,output=output,state='DRAFT',content_hash=digest(rule),
                        active_version=old.get('active_version'))
            body['active']=body['active_version'] is not None
            self.db.write(conn,'rule',rule_id,body)
            self.db.write(conn,'rule_revision',json.dumps([rule_id,body['version']]),body)
        self.emit('RULE.PREVIEW','LOGICTILES_TABBRIDGE',body,Priority.P2,rule_id)
        return body

    def activate_rule(self, rule_id: str, version: int, *, expected_version: int) -> dict:
        with self.db.transaction() as conn:
            current=conn.execute("SELECT body FROM records WHERE kind='rule' AND id=?",(rule_id,)).fetchone()
            revision=conn.execute("SELECT body FROM records WHERE kind='rule_revision' AND id=?",(json.dumps([rule_id,version]),)).fetchone()
            if not current or not revision: raise ValueError('Saved rule version required')
            body=json.loads(current[0]); selected=json.loads(revision[0])
            if body['version']!=expected_version: raise StateConflict('Rule version conflict')
            values={row['key']:row for row in self.values()}
            if any(key not in self.variables for key in selected['references']): raise ValueError('Unresolved variable binding')
            evaluate_rule(selected['rule'],values)
            body.update(active=True,active_version=version,state='ACTIVE')
            self.db.write(conn,'rule',rule_id,body)
        self.emit('RULE.PREVIEW','LOGICTILES_TABBRIDGE',body,Priority.P2,rule_id)
        return body

    def suspend_rule(self, rule_id: str) -> None:
        body=self.db.get('rule',rule_id)
        if not body: raise ValueError('Unknown rule')
        body.update(active=False,state='SUSPENDED',active_version=None)
        self.db.put('rule',rule_id,body)
        self.emit('RULE.PREVIEW','LOGICTILES_TABBRIDGE',body,Priority.P2,rule_id)

    def evaluate_active(self, changed_key: str) -> list[dict]:
        if not self.enabled(): return []
        outputs=[]
        values={row['key']:row for row in self.values()}
        for rule in self.db.list('rule'):
            if not rule.get('active'): continue
            active=self.db.get('rule_revision',json.dumps([rule['rule_id'],rule['active_version']]))
            if active is None: raise StateConflict('Active rule revision missing')
            if changed_key not in active['references']: continue
            result=evaluate_rule(active['rule'],values,as_of=self.clock())
            body={'rule_id':rule['rule_id'],'version':active['version'],'output':active['output'],'result':result.value}
            self.db.put('rule_output',rule['rule_id'],body)
            self.emit('RULE.ANALYTICAL_OUTPUT','LOGICTILES_EVALUATOR',body,Priority.P2,rule['rule_id'])
            outputs.append(body)
        return outputs

    def export_configuration(self) -> dict:
        return {'schema_version': 1,
                'parameters': [{'key': row['key'], 'value': row['value']} for row in self.db.list('parameter')],
                'rules': [{'rule_id': row['rule_id'], 'rule': row['rule'], 'output': row['output']}
                          for row in self.db.list('rule')]}

    def import_configuration(self, configuration: dict, expected_versions: dict) -> None:
        if (type(configuration) is not dict or set(configuration) != {'schema_version','parameters','rules'}
            or configuration['schema_version'] != 1 or type(configuration['parameters']) is not list
            or type(configuration['rules']) is not list or len(configuration['parameters']) + len(configuration['rules']) > 500):
            raise ValueError('Bounded schema-v1 configuration required')
        json.dumps(configuration, allow_nan=False)
        parameters, rules, keys = [], [], set()
        for row in configuration['parameters']:
            if type(row) is not dict or set(row) != {'key','value'} or row['key'] not in self.parameters:
                raise ValueError('Unknown parameter or configuration fields')
            key = 'parameter:' + row['key']
            if key in keys: raise ValueError('Duplicate configuration key')
            keys.add(key); self.parameters[row['key']].validate(row['value'])
            if row['key'] in self.validators: self.validators[row['key']](row['value'])
            parameters.append(row)
        for row in configuration['rules']:
            if type(row) is not dict or set(row) != {'rule_id','rule','output'} or row['output'] not in self.OUTPUTS:
                raise ValueError('Invalid analytical rule configuration')
            key = 'rule:' + row['rule_id']
            if key in keys: raise ValueError('Duplicate configuration key')
            keys.add(key); rules.append((row, self.preview_rule(row['rule_id'], row['rule'])))
        if set(expected_versions) != keys or any(type(v) is not int or v < 0 for v in expected_versions.values()):
            raise ValueError('Explicit expected versions required for every imported item')
        changed = []
        with self.db.transaction() as conn:
            for row in parameters:
                key = row['key']; old = self.db.get('parameter', key) or {'version': 0}
                if old['version'] != expected_versions['parameter:' + key]: raise StateConflict('Parameter version conflict')
                body = {**row, 'version': old['version']+1, 'owner': self.parameters[key].owner,
                        'effect_boundary': 'CORE_EVENT', 'status': 'EFFECTIVE'}
                self.db.write(conn, 'parameter', key, body)
                self.db.write(conn, 'parameter_revision', json.dumps([key,body['version']]), body)
                changed.append(body)
            if any(row['key'].startswith('geometry.band_') for row in parameters):
                bounds = [decimal(self.parameter_value(f'geometry.band_{i}')) for i in range(5)]
                if sorted(set(bounds)) != bounds: raise ValueError('ATR bands must be strictly increasing')
            for row, preview in rules:
                key = row['rule_id']; old = self.db.get('rule', key) or {'version': 0}
                if old['version'] != expected_versions['rule:' + key]: raise StateConflict('Rule version conflict')
                body = {**preview, 'version': old['version']+1, 'output': row['output'], 'state': 'DRAFT',
                        'content_hash': digest(row['rule']), 'active_version': old.get('active_version'),
                        'active': bool(old.get('active'))}
                self.db.write(conn, 'rule', key, body)
                self.db.write(conn, 'rule_revision', json.dumps([key,body['version']]), body)
        self.emit('PARAM.EFFECTIVE', 'GLOBAL_PARAMETER_REGISTRY', {'changes': changed}, Priority.P2)
