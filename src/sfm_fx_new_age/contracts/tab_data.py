"""Additive TabApi v1 read-contract manifest. These names, not storage tables, belong to tabs."""
from dataclasses import dataclass
from typing import Any
from .domain import FRAMES,instant,symbol_check

DATASETS={
 '1.1':('watchlist',),'1.2':('bars','analytics'),'1.3':('bars','levels','overlays','annotations'),
 '1.4':('bars','levels','overlays'),'1.5':('bars',),'1.6':('levels','evidence'),
 '1.7':('geometry','analytics'),'1.8':('overlays','market_candidates'),'1.9':('replay',),'1.10':('orders','positions'),
 '2.1':('consumers','components'),'2.2':('scanner_nodes',),'2.3':('connector','accounts'),
 '2.4':('coverage','backfill'),'2.5':('specifications','calendars'),'2.6':('routes','router_metrics'),
 '2.7':('variables','variable_definitions'),'2.8':('parameters','parameter_definitions','mutable_surfaces'),
 '2.9':('components',),'2.10':('diagnostics','audit','configuration'),
 '3.1':('recipes','strategy_catalogue'),'3.2':('bars','analytics'),'3.3':('bars','analytics'),'3.4':('analytics','levels'),
 '3.5':('analytics','levels','evidence'),'3.6':('analytics','levels','evidence'),'3.7':('analytics','levels'),
 '3.8':('geometry','market_candidates'),'3.9':('market_candidates','evidence','analytics'),
 '3.10':('rules','variables','variable_definitions','rule_history','mutable_surfaces'),
 '3.11':('parameters','parameter_definitions','parameter_history','mutable_surfaces','pair_parameters','pair_parameter_history'),
 '3.12':('replay','replay_datasets','replay_runs','research_studies'),'3.13':('market_candidates','signal_history','signals'),
 '4.1':('signals','strategy_signals'),'4.2':('issue_preview','signals','market_candidates','strategy_signals','levels','evidence','specifications','capital_context'),'4.3':('orders','broker_pending'),'4.4':('order_history','signal_history'),
 '4.5':('accounts','connector'),'4.6':('positions',),'4.7':('capital_context',),
 '4.8':('order_history','audit','broker_history','broker_history_jobs'),'4.9':('optional_exit_capability',)}

for _identity in tuple(DATASETS):
    if _identity.startswith('1.'):
        DATASETS[_identity] += ('chart',)


@dataclass(frozen=True)
class DataRequest:
    dataset:str
    symbol:str|None=None
    timeframe:str|None=None
    as_of:str|None=None
    object_id:str|None=None
    run_id:str|None=None
    limit:int=500
    cursor:int=0
    history:bool=False
    expected_hash:str|None=None
    acknowledge_research:bool=False

    def __post_init__(self):
        if self.symbol:symbol_check(self.symbol)
        if self.timeframe and self.timeframe not in FRAMES:raise ValueError('Unsupported query timeframe')
        if self.as_of:instant(self.as_of)
        if type(self.limit) is not int or not 1<=self.limit<=5000 or type(self.cursor) is not int or self.cursor<0:
            raise ValueError('Bounded nonnegative pagination required')
        if type(self.history) is not bool:raise ValueError('Boolean history flag required')
        if type(self.acknowledge_research) is not bool:raise ValueError('Boolean preview acknowledgement required')
        if self.cursor and not self.expected_hash:raise ValueError('Continuation pages require a bound data_hash')
