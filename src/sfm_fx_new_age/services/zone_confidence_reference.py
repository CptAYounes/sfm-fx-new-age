#!/usr/bin/env python3
"""Deterministic, read-only RESEARCH reference for price-zone evidence confluence.

This is not a validated success-probability model, a trading signal generator,
or a broker integration. It accepts canonical sub-signal evidence records and an
entry zone, and returns a reproducible evidence-confidence assessment. Calibration,
configuration and production gates remain separate responsibilities.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import json
from typing import Any

ALLOWED_TIMEFRAMES = ("W1", "D1", "H4", "H1")
ALLOWED_DIRECTIONS = ("BUY", "SELL", "NEUTRAL")
ALLOWED_ZONE_KINDS = ("ENTRY_LOCAL", "CONTEXT", "UNLOCATED")

DEFAULT_PROFILE = {
    "id": "RESEARCH_ZONE_CONF_V1_2",
    "version": "1.2",
    "alpha": 0.90,
    "opposition_multiplier": 1.25,
    "opposition_score_penalty": 0.75,
    "min_effective_cluster_contribution": 0.10,
    "timeframe_weights": {"W1": 0.65, "D1": 1.00, "H4": 0.90, "H1": 0.80},
    "domain_caps": {
        "PRICE_STRUCTURE": 1.70,
        "CANDLE_ACTION": 1.35,
        "AUCTION_FLOW": 1.30,
        "MACRO_CONTEXT": 0.65,
        "CYCLE_HYPOTHESIS": 0.85,
    },
    "default_domain_cap": 1.0,
    "provisional_cap_factor": 0.40,
    "context_locality_cap": 0.35,
    "minimum_support_clusters_for_gate": 3,
    "minimum_distinct_timeframes_for_gate": 2,
    "minimum_entry_local_clusters_for_gate": 2,
    "minimum_confidence_for_gate": 80.0,
    "half_life_hours": {"W1": 672.0, "D1": 168.0, "H4": 72.0, "H1": 24.0},
}


def _timestamp(s: str) -> datetime:
    if not isinstance(s, str) or not s:
        raise ValueError("Timestamp must be nonempty RFC3339/ISO8601 UTC string")
    v = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError("Timezone-naive timestamp not allowed")
    return v.astimezone(timezone.utc)


def _finite_nonnegative(value: Any, field: str) -> float:
    try:
        v = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(v) or v < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return v


def _unit(value: Any, field: str) -> float:
    v = _finite_nonnegative(value, field)
    if v > 1:
        raise ValueError(f"{field} must be between 0 and 1")
    return v


def _normalised_interval(lo: Any, hi: Any, pip_size: float) -> tuple[float, float]:
    a = float(lo); b = float(hi)
    if not math.isfinite(a) or not math.isfinite(b) or a <= 0 or b <= 0 or b < a:
        raise ValueError("Invalid price zone")
    if a == b:
        a -= pip_size / 2
        b += pip_size / 2
    return (a, b)


def _locality(candidate: tuple[float, float], evidence: tuple[float, float], kind: str, profile: dict) -> float:
    a,b = candidate; c,d = evidence
    if kind == "UNLOCATED":
        return 0.0  # a non-price metric can inform context elsewhere, but not entry-zone confidence
    if kind == "CONTEXT":
        return profile["context_locality_cap"] if c <= (a + b) / 2 <= d else 0.0
    overlap = max(0.0, min(b,d) - max(a,c))
    union = max(b,d) - min(a,c)
    if not union:
        return 0.0
    # sqrt IoU acknowledges small matching zones, while penalising very broad levels.
    return math.sqrt(overlap / union)


def score_zone_confidence(
    zone: dict,
    evidences: list[dict],
    *,
    as_of_utc: str,
    pip_size: float,
    source_epoch: str,
    profile: dict | None = None,
) -> dict:
    """Score independent, eligible, located evidence supporting/opposing one entry zone.

    Important: these numbers are *uncalibrated evidence indices*, not probabilities.
    Do not hand this function an execution order; it never sends orders or chooses a stop.
    """
    cfg = dict(DEFAULT_PROFILE)
    if profile:
        cfg.update(profile)
    pip = _finite_nonnegative(pip_size, "pip_size")
    if pip <= 0:
        raise ValueError("pip_size must be positive")
    now = _timestamp(as_of_utc)
    symbol = zone["symbol"]
    side = zone["side"]
    if side not in ("BUY", "SELL"):
        raise ValueError("zone side must be BUY or SELL")
    interval = _normalised_interval(zone["low"], zone["high"], pip)
    if zone["timeframe"] not in ALLOWED_TIMEFRAMES:
        raise ValueError("Unsupported zone timeframe")
    if not zone.get("zone_id"):
        raise ValueError("zone_id required")

    # Ingest only eligible, causally available evidence. An excluded observation
    # remains in the upstream registry and can be audited; it cannot boost confidence.
    accepted: list[dict] = []
    excluded: dict[str, int] = {}
    observed_ids: dict[str,str] = {}
    for e in evidences:
        eid = e["evidence_id"]
        canonical = json.dumps(e, sort_keys=True, separators=(',',':'), allow_nan=False)
        if eid in observed_ids:
            if observed_ids[eid] != canonical:
                raise ValueError('CONFLICTING_EVIDENCE_ID: same ID, different bytes')
            excluded["DUPLICATE_DELIVERY"] = excluded.get("DUPLICATE_DELIVERY",0)+1
            continue
        observed_ids[eid] = canonical
        reason = None
        if e["symbol"] != symbol or e["source_epoch"] != source_epoch:
            reason = "SOURCE_SCOPE_MISMATCH"
        elif e["direction"] not in ALLOWED_DIRECTIONS or e["timeframe"] not in ALLOWED_TIMEFRAMES:
            reason = "INVALID_DIRECTION_OR_TIMEFRAME"
        elif e["direction"] == "NEUTRAL":
            reason = "NON_DIRECTIONAL"
        elif e["state"] not in ("CONFIRMED", "PROVISIONAL"):
            reason = "INACTIVE_OR_INVALID"
        elif e["zone_kind"] not in ALLOWED_ZONE_KINDS:
            reason = "INVALID_ZONE_KIND"
        elif _timestamp(e["available_at_utc"]) > now:
            reason = "FUTURE_UNAVAILABLE"
        elif e.get("valid_until_utc") and _timestamp(e["valid_until_utc"]) < now:
            reason = "EXPIRED"
        if reason:
            excluded[reason] = excluded.get(reason,0)+1
            continue
        strength = _unit(e["strength"], "strength")
        reliability = _unit(e["source_reliability"], "source_reliability")
        lifespan_factor = _unit(e.get("freshness_factor", 1.0), "freshness_factor")
        loc = _locality(interval, _normalised_interval(e["zone_low"],e["zone_high"],pip),e["zone_kind"],cfg)
        if loc <= 0:
            excluded["OUTSIDE_ZONE"] = excluded.get("OUTSIDE_ZONE",0)+1
            continue
        hours = max(0.0, (now - _timestamp(e["available_at_utc"])).total_seconds() / 3600)
        halflife = cfg["half_life_hours"][e["timeframe"]]
        decay = 2.0 ** (-hours / halflife) if halflife > 0 else 1.0
        provisional = cfg["provisional_cap_factor"] if e["state"] == "PROVISIONAL" else 1.0
        weight = (strength * reliability * lifespan_factor * decay *
                  cfg["timeframe_weights"][e["timeframe"]] * loc * provisional)
        accepted.append({**e, "weight": weight, "locality": loc})

    # Transitive union of root source events, correlation keys and causal fingerprints.
    # This is the REF implementation for the upstream cluster resolver: not a
    # statistical test that signals are independent in the real market.
    parent = list(range(len(accepted)))
    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def unite(i: int,j: int) -> None:
        i = find(i); j = find(j)
        if i != j:
            parent[max(i,j)] = min(i,j)
    owners: dict[tuple[str,str],int] = {}
    for i,e in enumerate(accepted):
        for tag in ("root_event_id", "correlation_cluster_id", "event_fingerprint"):
            val = e.get(tag)
            if val:
                key=(tag,str(val))
                if key in owners:unite(i, owners[key])
                else:owners[key] = i
    groups: dict[int,list[dict]] = {}
    for i,e in enumerate(accepted):
        groups.setdefault(find(i),[]).append(e)

    selections: dict[str,list[dict]] = {"support":[], "opposition":[]}
    ambiguous = 0
    for group in groups.values():
        support = sorted((e for e in group if e["direction"]==side),key=lambda e:(-e["weight"],e["evidence_id"]))
        opposition = sorted((e for e in group if e["direction"]!=side),key=lambda e:(-e["weight"],e["evidence_id"]))
        s = support[0]["weight"] if support else 0.0
        o = opposition[0]["weight"] if opposition else 0.0
        if s and o:ambiguous+=1
        if s>o: chosen = support[0]; bucket = "support"; net=s-o
        elif o>s:chosen = opposition[0]; bucket="opposition"; net=o-s
        else:continue
        selections[bucket].append({
            "cluster_id": min(str(e.get("root_event_id",e["evidence_id"])) for e in group),
            "selected_evidence_id": chosen["evidence_id"],
            "member_evidence_ids": sorted(e["evidence_id"] for e in group),
            "producer_id": chosen["producer_id"],
            "independence_domain": chosen["independence_domain"],
            "timeframe": chosen["timeframe"],
            "zone_kind": chosen["zone_kind"],
            "locality": round(chosen["locality"],8),
            "raw_weight": net,
        })

    # Correlated events within the same evidence domain can add support, but only
    # to a fixed capped contribution. Caps are independently applied by polarity.
    for bucket in ("support","opposition"):
        used: dict[str,float] = {}
        for c in sorted(selections[bucket],key=lambda x:(-x["raw_weight"],x["selected_evidence_id"])):
            domain = c["independence_domain"]
            cap = cfg["domain_caps"].get(domain,cfg["default_domain_cap"])
            remaining = max(0.0, cap - used.get(domain,0.0))
            contribution = min(remaining,c["raw_weight"])
            used[domain] = used.get(domain,0.0)+contribution
            c["effective_weight"] = contribution
        selections[bucket].sort(key=lambda x:x["selected_evidence_id"])

    threshold = cfg["min_effective_cluster_contribution"]
    supported = [c for c in selections["support"] if c["effective_weight"]>=threshold]
    opposed = [c for c in selections["opposition"] if c["effective_weight"]>=threshold]
    support_weight = sum(c["effective_weight"] for c in selections["support"])
    opposition_weight = sum(c["effective_weight"] for c in selections["opposition"])
    domains = sorted({c["independence_domain"] for c in supported})
    timeframes = [t for t in ALLOWED_TIMEFRAMES if any(c["timeframe"]==t for c in supported)]
    local_clusters = sum(1 for c in supported if c["zone_kind"]=="ENTRY_LOCAL")
    diversity = 0.72 + 0.18*min(len(domains)/3.0,1.0)+0.10*min(len(timeframes)/3.0,1.0)
    net = max(0.0,support_weight-cfg["opposition_multiplier"]*opposition_weight)
    base = 100.0*(-math.expm1(-cfg["alpha"]*net))
    contradiction = 1.0/(1.0+cfg["opposition_score_penalty"]*opposition_weight)
    score = round(max(0.0,min(100.0,base*diversity*contradiction)),2)
    blockers = []
    if not supported: blockers.append("NO_EFFECTIVE_ZONE_SUPPORT")
    if len(supported)<cfg["minimum_support_clusters_for_gate"]:blockers.append("INSUFFICIENT_INDEPENDENT_CLUSTERS")
    if len(timeframes)<cfg["minimum_distinct_timeframes_for_gate"]:blockers.append("INSUFFICIENT_TIMEFRAME_COVERAGE")
    if local_clusters<cfg["minimum_entry_local_clusters_for_gate"]:blockers.append("INSUFFICIENT_ENTRY_LOCAL_EVIDENCE")
    if score<cfg["minimum_confidence_for_gate"]:blockers.append("CONFIDENCE_BELOW_PROFILE_FLOOR")
    return {
        "status":"EVALUATED" if supported else "INSUFFICIENT_EVIDENCE",
        "metric_type":"RESEARCH_CONFLUENCE_INDEX",
        "is_win_probability":False,
        "score":score,
        "zone_id":zone["zone_id"],
        "zone_low":float(zone["low"]),
        "zone_high":float(zone["high"]),
        "zone_timeframe":zone["timeframe"],
        "zone_side":side,
        "supporting_subsignals_raw":sum(1 for e in accepted if e["direction"]==side),
        "opposing_subsignals_raw":sum(1 for e in accepted if e["direction"]!=side),
        "independent_support_clusters":len(supported),
        "independent_opposing_clusters":len(opposed),
        "independent_support_domains":len(domains),
        "entry_local_support_clusters":local_clusters,
        "support_timeframes":timeframes,
        "supporting_evidence_ids":sorted(e["evidence_id"] for e in accepted if e["direction"]==side),
        "opposing_evidence_ids":sorted(e["evidence_id"] for e in accepted if e["direction"]!=side),
        "support_weight":round(support_weight,8),
        "opposition_weight":round(opposition_weight,8),
        "diversity_factor":round(diversity,8),
        "contradiction_factor":round(contradiction,8),
        "ambiguous_event_clusters":ambiguous,
        "confidence_profile_id":cfg["id"],
        "as_of_utc":as_of_utc,
        "blocked_confidence_gate":bool(blockers),
        "blocker_codes":blockers,
        "excluded_evidence_counts":excluded,
        "supporting_clusters":selections["support"],
        "opposing_clusters":selections["opposition"],
    }

if __name__ == "__main__":
    print("Reference module only. Import score_zone_confidence(...) to evaluate synthetic evidence; no external data or order interfaces.")
