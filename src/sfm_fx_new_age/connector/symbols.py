"""Pure source-native instrument resolution; no suffix repair or network access."""
from dataclasses import dataclass
from collections import Counter
from sfm_fx_new_age.contracts.domain import PAIRS


@dataclass(frozen=True)
class SymbolResolution:
    symbols: dict[int, str]
    native_names: dict[int, str]
    assets: dict[int, tuple[str, str]]
    states: dict[str, str]


def native_id(value):
    """Validate native protobuf integer tokens before conversion; never repair."""
    if type(value) is int and value > 0:
        return value
    if isinstance(value,str) and value.isascii() and value.isdecimal() and value == str(int(value)) and int(value)>0:
        return int(value)
    raise ValueError('Positive literal native ID required')


def resolve_symbols(rows, asset_names):
    """Map a unique enabled broker Forex contract by source asset orientation.

    An exact canonical native name is retained as the legacy explicit identity
    when optional asset IDs are absent. Once either asset is supplied, both must
    resolve and agree; a canonical name cannot override contradictory assets.
    Noncanonical names require authoritative asset IDs. Duplicate contracts/IDs
    are unavailable, not selected by order or by a name preference.
    """
    if not isinstance(rows,(list,tuple)) or not isinstance(asset_names,dict):
        raise ValueError('Native symbol list and asset directory required')
    candidates={s:[] for s in PAIRS};states={s:'NOT_LISTED' for s in PAIRS}
    ids=Counter()
    for row in rows:
        try:ids[native_id(row['symbolId'])]+=1
        except (KeyError,TypeError,ValueError):continue
    for row in rows:
        if not isinstance(row,dict):continue
        name=row.get('symbolName');named=name if name in PAIRS else None
        pair=named;assets=None
        try:
            sid=native_id(row.get('symbolId'))
            if not isinstance(name,str) or not name or len(name)>256 or any(ord(c)<32 for c in name):
                raise ValueError('Literal native name required')
            if 'baseAssetId' in row or 'quoteAssetId' in row:
                assets=(str(native_id(row.get('baseAssetId'))),str(native_id(row.get('quoteAssetId'))))
                base,quote=(asset_names.get(v) for v in assets)
                if not isinstance(base,str) or not isinstance(quote,str):
                    if named:states[named]='WAITING_ASSET_METADATA'
                    continue
                pair=base+quote
                if named and named!=pair:
                    states[named]='CONTRADICTORY_ASSET_IDENTITY';continue
                if pair not in candidates:continue
            elif not named:continue
            if pair is None:continue
            if row.get('enabled',True) is not True:
                states[pair]='DISABLED_NATIVE_SYMBOL';continue
            if any(row.get(k) not in (None,False,0,'') for k in ('isFuture','expirationTimestamp','expiryTimestamp')) or row.get('instrumentType') in {'FUTURE','FUTURES','CRYPTO','OPTION'}:
                states[pair]='INCOMPATIBLE_NATIVE_CONTRACT';continue
            if ids[sid]!=1:
                states[pair]='DUPLICATE_NATIVE_ID';continue
            candidates[pair].append((sid,name,assets))
        except (ValueError,TypeError):
            if named:states[named]='INVALID_NATIVE_IDENTITY'
    symbols={};names={};asset_ids={}
    for pair,values in candidates.items():
        if len(values)>1:states[pair]='AMBIGUOUS_NATIVE_CONTRACT';continue
        if len(values)==1 and states[pair] not in {'CONTRADICTORY_ASSET_IDENTITY','DUPLICATE_NATIVE_ID','INVALID_NATIVE_IDENTITY'}:
            sid,name,assets=values[0];symbols[sid]=pair;names[sid]=name
            if assets:asset_ids[sid]=assets
            states[pair]='RESOLVED_BY_ASSETS' if assets else 'EXACT_NATIVE_NAME'
    return SymbolResolution(symbols,names,asset_ids,states)
