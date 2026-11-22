"""Bounded declarative LogicTiles evaluator; no executable expressions or broker effects."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Any

from sfm_fx_new_age.contracts.domain import decimal, instant


class Truth(str, Enum):
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    UNKNOWN = 'UNKNOWN'


@dataclass(frozen=True)
class Value:
    value: Any
    unit: str
    unknown: bool = False


def _unknown(unit='unknown'): return Value(None, unit, True)

def _truth(value: Value) -> Truth:
    if value.unknown: return Truth.UNKNOWN
    if type(value.value) is not bool: raise ValueError('Boolean rule result required')
    return Truth.TRUE if value.value else Truth.FALSE


def evaluate_rule(node: dict, variables: dict[str, dict], *, as_of: str | None = None) -> Truth:
    """Read-only evaluation with explicit units, causality, historical offsets and bounded work."""
    count = [0]
    def run(n, depth=0, offset=0):
        count[0] += 1
        if count[0] > 2048 or depth > 24 or type(n) is not dict: raise ValueError('Rule complexity limit exceeded')
        op = n.get('op')
        child = lambda value, off=offset: run(value, depth + 1, off)
        def variable(key, shift=0):
            entry = variables.get(key)
            if not entry: return _unknown()
            if entry.get('freshness')!='CURRENT':return _unknown(entry.get('unit','unknown'))
            series = entry.get('history', [])
            if as_of:
                series = [row for row in series if row.get('available_at') and instant(row['available_at']) <= instant(as_of)]
            if offset + shift:
                if len(series) <= offset + shift: return _unknown(entry.get('unit', 'unknown'))
                entry = {**entry, **series[-1-offset-shift]}
            elif as_of and entry.get('available_at') and instant(entry['available_at']) > instant(as_of):
                return _unknown(entry.get('unit', 'unknown'))
            if entry.get('freshness') != 'CURRENT': return _unknown(entry.get('unit', 'unknown'))
            if not offset+shift and as_of and entry.get('max_age_seconds') is not None:
                if not entry.get('available_at'):return _unknown(entry.get('unit','unknown'))
                age=(instant(as_of)-instant(entry['available_at'])).total_seconds()
                if age<0 or age>entry['max_age_seconds']:return _unknown(entry.get('unit','unknown'))
            return Value(entry.get('value'), entry['unit'], entry.get('value') is None)
        if op == 'CONST':
            val = n.get('value')
            if type(val) not in {str, int, float, bool}: raise ValueError('Primitive literal required')
            if type(val) in {int, float}: decimal(val)
            return Value(val, n['unit'])
        if op == 'VAR': return variable(n['variable'])
        if op == 'HISTORY':
            bars = n.get('bars')
            if type(bars) is not int or not 1 <= bars <= 128: raise ValueError('History offset must be 1..128')
            return variable(n['variable'], bars)
        if op in {'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'}:
            left = variable(n['variable']) if 'variable' in n else child(n['left'])
            right = Value(n['value'], n['unit']) if 'value' in n else child(n['right'])
            if left.unknown or right.unknown: return _unknown('boolean')
            if left.unit != right.unit: raise ValueError('Variable unit mismatch')
            a,b = left.value,right.value
            if isinstance(a, bool) != isinstance(b, bool): raise ValueError('Boolean/numeric mismatch')
            if op in {'LT', 'LE', 'GT', 'GE'} or type(a) is not bool and left.unit not in {'string', 'enum'}:
                a,b = decimal(a),decimal(b)
            return Value({'EQ':lambda:a==b,'NE':lambda:a!=b,'LT':lambda:a<b,
                          'LE':lambda:a<=b,'GT':lambda:a>b,'GE':lambda:a>=b}[op](), 'boolean')
        if op in {'AND', 'OR'}:
            nodes = n.get('children', [])
            if not 1 <= len(nodes) <= 64: raise ValueError('Boolean rule needs 1..64 children')
            values = [_truth(child(c)) for c in nodes]
            if op == 'AND':
                if Truth.FALSE in values: return Value(False, 'boolean')
                return _unknown('boolean') if Truth.UNKNOWN in values else Value(True, 'boolean')
            if Truth.TRUE in values: return Value(True, 'boolean')
            return _unknown('boolean') if Truth.UNKNOWN in values else Value(False, 'boolean')
        if op == 'NOT':
            result = _truth(child(n['child']))
            return _unknown('boolean') if result is Truth.UNKNOWN else Value(result is Truth.FALSE, 'boolean')
        if op in {'ADD','SUB','MUL','DIV'}:
            a,b = child(n['left']),child(n['right'])
            if a.unknown or b.unknown: return _unknown(a.unit)
            if isinstance(a.value,bool) or isinstance(b.value,bool): raise ValueError('Arithmetic needs numbers')
            if op in {'ADD','SUB'}:
                if a.unit != b.unit: raise ValueError('Arithmetic unit mismatch')
                unit = a.unit
            elif op == 'MUL':
                if a.unit != 'ratio' and b.unit != 'ratio': raise ValueError('Multiplication requires dimensionless factor')
                unit = b.unit if a.unit == 'ratio' else a.unit
            else:
                if a.unit != b.unit and b.unit != 'ratio': raise ValueError('Division unit mismatch')
                unit = 'ratio' if a.unit == b.unit else a.unit
            x,y=decimal(a.value),decimal(b.value)
            if op=='DIV' and y==0: return _unknown(unit)
            return Value({'ADD':lambda:x+y,'SUB':lambda:x-y,'MUL':lambda:x*y,'DIV':lambda:x/y}[op](),unit)
        if op == 'BETWEEN':
            value, low, high = child(n['value']),child(n['low']),child(n['high'])
            if any(v.unknown for v in (value,low,high)): return _unknown('boolean')
            if len({v.unit for v in (value,low,high)}) != 1: raise ValueError('Range unit mismatch')
            lo,hi=decimal(low.value),decimal(high.value)
            if lo>hi: raise ValueError('Inverted range')
            return Value(lo<=decimal(value.value)<=hi,'boolean')
        if op in {'CROSSES_ABOVE','CROSSES_BELOW'}:
            a,b,prev_a,prev_b = child(n['left']),child(n['right']),child(n['left'],offset+1),child(n['right'],offset+1)
            if any(v.unknown for v in (a,b,prev_a,prev_b)): return _unknown('boolean')
            if len({v.unit for v in (a,b,prev_a,prev_b)})!=1: raise ValueError('Cross unit mismatch')
            x,y,p,q=map(lambda v:decimal(v.value),(a,b,prev_a,prev_b))
            return Value(p<=q and x>y if op=='CROSSES_ABOVE' else p>=q and x<y,'boolean')
        if op in {'FOR_BARS','WITHIN_BARS'}:
            bars=n.get('bars')
            if type(bars) is not int or not 1<=bars<=128: raise ValueError('Temporal window must be 1..128')
            values=[_truth(child(n['child'],offset+i)) for i in range(bars)]
            if op=='FOR_BARS':
                if Truth.FALSE in values: return Value(False,'boolean')
                return _unknown('boolean') if Truth.UNKNOWN in values else Value(True,'boolean')
            if Truth.TRUE in values: return Value(True,'boolean')
            return _unknown('boolean') if Truth.UNKNOWN in values else Value(False,'boolean')
        raise ValueError(f'Unsupported declarative operator: {op}')
    return _truth(run(node))


def validate_rule(node: dict, *, max_nodes: int = 256, max_depth: int = 16) -> tuple[str, ...]:
    refs=set(); count=0
    ops={'CONST','VAR','HISTORY','EQ','NE','LT','LE','GT','GE','AND','OR','NOT',
         'ADD','SUB','MUL','DIV','BETWEEN','CROSSES_ABOVE','CROSSES_BELOW','FOR_BARS','WITHIN_BARS'}
    allowed={'op','variable','unit','value','left','right','child','children','low','high','bars'}
    def visit(n,depth):
        nonlocal count
        count+=1
        if type(n) is not dict or depth>max_depth or count>max_nodes or n.get('op') not in ops or set(n)-allowed:
            raise ValueError('Invalid or oversized declarative rule')
        op=n['op'];fields=set(n)-{'op'}
        def exact(keys):
            if fields!=set(keys):raise ValueError('Missing or extraneous fields for '+op)
        if op=='CONST':
            exact({'value','unit'})
            if type(n['unit']) is not str or not n['unit']:raise ValueError('Literal unit required')
        elif op in {'VAR','HISTORY'}:
            exact({'variable','bars'} if op=='HISTORY' else {'variable'})
        elif op in {'AND','OR'}:
            exact({'children'})
            if type(n['children']) is not list or not 1<=len(n['children'])<=64:raise ValueError('Boolean rule needs 1..64 children')
        elif op in {'NOT','FOR_BARS','WITHIN_BARS'}:exact({'child'} if op=='NOT' else {'child','bars'})
        elif op in {'EQ','NE','LT','LE','GT','GE'}:
            left={'variable'} if 'variable' in n else {'left'};right={'value','unit'} if 'value' in n else {'right'};exact(left|right)
        elif op=='BETWEEN':exact({'value','low','high'})
        else:exact({'left','right'})
        if op in {'HISTORY','FOR_BARS','WITHIN_BARS'} and (type(n.get('bars')) is not int or not 1<=n['bars']<=128):raise ValueError('Temporal offset/window must be 1..128')
        required_children=({'child'} if op in {'NOT','FOR_BARS','WITHIN_BARS'} else {'value','low','high'} if op=='BETWEEN' else {'left','right'}&fields)
        if any(type(n[k]) is not dict for k in required_children):raise ValueError('Declarative child object required')
        if op in {'EQ','NE','LT','LE','GT','GE'} and 'value' in n:
            if type(n['value']) not in {str,int,float,bool} or type(n['unit']) is not str:raise ValueError('Typed comparison literal required')
        if 'variable' in n:
            if type(n['variable']) is not str or not n['variable']: raise ValueError('Variable identity required')
            refs.add(n['variable'])
        for key in ('left','right','child','low','high','value'):
            if type(n.get(key)) is dict: visit(n[key],depth+1)
        for c in n.get('children',[]): visit(c,depth+1)
    visit(node,0)
    evaluate_rule(node,{})
    return tuple(sorted(refs))
