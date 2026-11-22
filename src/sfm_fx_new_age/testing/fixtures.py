from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sfm_fx_new_age.contracts.domain import AccountContext, Bar, Candidate, Origin, PAIRS, Quote, SymbolSpec
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.orders import FixtureBroker

FIXTURE_NOW = '2026-11-05T12:00:00Z'
FIXTURE_EPOCH = 'SYNTHETIC-FIXTURE-EPOCH-1'


def stamp(value: datetime) -> str:
    return value.isoformat().replace('+00:00', 'Z')


def populate_fixture(runtime: ApplicationRuntime, *, account_type: str = 'UNSPECIFIED') -> None:
    """All active pairs × four frames. This is test data, not strategy evidence."""
    if not runtime.fixture_mode:
        raise ValueError('Explicit fixture transport required to seed fixtures')
    now = datetime.fromisoformat(FIXTURE_NOW.replace('Z', '+00:00'))
    origin = Origin.SYNTHETIC_FIXTURE
    account = AccountContext('FIXTURE-ACCOUNT', 'FIXTURE', 'USD', True, True, origin, account_type)
    runtime.accounts.select(account)
    for symbol in PAIRS:
        jpy = symbol.endswith('JPY')
        base = Decimal('150') if jpy else Decimal('1.10000')
        pip = Decimal('0.01') if jpy else Decimal('0.0001')
        tick = pip / 10
        runtime.market.activate_source(symbol, FIXTURE_EPOCH, origin.value)
        runtime.market.set_spec(SymbolSpec(account.account_id, symbol, PAIRS.index(symbol)+1,
            pip, tick, Decimal('1000'), Decimal('10000000'), Decimal('1000'), Decimal('100000'), origin))
        monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        for index in range(15):
            end = monday - timedelta(weeks=14-index)
            runtime.market.ingest(Bar(symbol, 'W1', stamp(end-timedelta(weeks=1)), stamp(end), stamp(end),
                base, base+pip*200, base-pip*200, base+pip*10, FIXTURE_EPOCH, origin))
        for frame, duration in [('D1', timedelta(days=1)), ('H4', timedelta(hours=4)), ('H1', timedelta(hours=1))]:
            end = now.replace(hour=0) if frame == 'D1' else now
            runtime.market.ingest(Bar(symbol, frame, stamp(end-duration), stamp(end), stamp(end),
                base, base+pip*40, base-pip*40, base+pip*10, FIXTURE_EPOCH, origin))
        runtime.market.set_quote(Quote(account.account_id, symbol, base+pip*10, base+pip*12,
                                      FIXTURE_NOW, FIXTURE_EPOCH, origin))
    runtime.catalogues.set_variable('fixture.d1_ready', True, 'boolean')
    from sfm_fx_new_age.contracts.analytics import ParameterDefinition
    runtime.catalogues.register_parameter(ParameterDefinition('fixture.atr_buffer', 'SYNTHETIC_FIXTURE', 'number', 'ATR_MULTIPLE'))
    runtime.catalogues.set_parameter('fixture.atr_buffer', '0.50', expected_version=0)
    runtime.catalogues.save_rule('fixture.rule', {'op': 'EQ', 'variable': 'fixture.d1_ready', 'unit': 'boolean', 'value': True})
    context = runtime.market.context('EURUSD', FIXTURE_NOW, FIXTURE_EPOCH)
    entry = Decimal(context['bars']['H4']['low'])
    atr = Decimal(context['w1_atr14'])
    # Deliberately simple synthetic reference recipe, NOT a New Age scanner implementation.
    runtime.signals.propose(Candidate('FIXTURE-SIGNAL-1', 'FIXTURE-SETUP-1', 1, 'EURUSD', 'BUY',
        entry, entry-atr*Decimal('0.50'), Decimal('1000'), stamp(now+timedelta(days=2)),
        FIXTURE_NOW, FIXTURE_EPOCH, origin))


def fixture_runtime(path: str | Path = ':memory:', *, broker: FixtureBroker | None = None,
                    account_type: str = 'UNSPECIFIED') -> ApplicationRuntime:
    runtime = ApplicationRuntime(path, clock=lambda: FIXTURE_NOW, transport=broker or FixtureBroker())
    populate_fixture(runtime, account_type=account_type)
    return runtime
