from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .checks import run_checks
from .core.runtime import ApplicationRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description='SFM FX New Age')
    parser.add_argument('--check', action='store_true', help='run architecture checks')
    parser.add_argument('--summary-json', action='store_true', help='print runtime summary')
    parser.add_argument('--offline-checkpoint', action='store_true', help='exercise synthetic shared backend and restart reconciliation, no network')
    parser.add_argument('--fixture-session', action='store_true', help='open explicitly labelled in-memory synthetic UI session, not real market data')
    parser.add_argument('--strict-genuine-data',action='store_true',help='disable tick/quote-activity substitutes; require genuine executions/aggressors or scoped displayed DOM as appropriate, without claiming a complete native venue book')
    parser.add_argument('--compute-workers',default='auto',help='pure analytical process ceiling: auto uses available CPUs/quota/memory and reserves a core slot; 1 is serial')
    parser.add_argument('--state-dir', type=Path, help='override local application state directory')
    parser.add_argument('--supplemental-config',type=Path,help='explicit local read-only analytical source configuration; never opens a network feed')
    parser.add_argument('--validate-supplemental-config',type=Path,help='validate source configuration without Qt, input admission, authentication or database writes')
    parser.add_argument('--acquire-official-context',type=Path,help='one-shot original CFTC/Federal Reserve Board HTTPS acquisition into a new directory, bound to saved source epochs; no GUI, credentials or broker calls')
    parser.add_argument('--acquire-original-inputs',type=Path,help='bounded read-only capture of original broker bars/ticks and CFTC/Board context into a new isolated directory; all SDK processes are joined before return')
    parser.add_argument('--capture-original-depth',type=Path,help='bounded native broker depth capture into a new private directory; no invented venue sequence or DOM admission')
    parser.add_argument('--audit-native-feed',type=Path,help='bounded real cTrader quote/history/depth health and installed-protocol capability audit; no trades or synthetic data')
    parser.add_argument('--prepare-original-point-figure',type=Path,help='validate a source-hash-bound operator count request and prepare original P&F ticks; no network or automatic count settings')
    parser.add_argument('--capture-fix-depth',type=Path,help='bounded TLS FIX Price full-book capture; fails before network if separate private FIX credentials are absent')
    parser.add_argument('--fix-price-credentials',type=Path,help='existing user-owned 0600 private FIX Price JSON; never OAuth, cTID or Trade credentials')
    args = parser.parse_args()
    try:
        compute_workers='auto' if args.compute_workers=='auto' else int(args.compute_workers)
        if compute_workers!='auto' and compute_workers<1:raise ValueError()
    except ValueError:parser.error('--compute-workers requires auto or a positive integer')
    if args.capture_fix_depth is not None or args.fix_price_credentials is not None:
        if args.capture_fix_depth is None or any((args.fixture_session,args.offline_checkpoint,args.check,args.summary_json,args.validate_supplemental_config,args.acquire_official_context,args.acquire_original_inputs,args.supplemental_config,args.capture_original_depth,args.prepare_original_point_figure,args.audit_native_feed)):
            parser.error('FIX Price capture runs alone; no fixture, trade or other acquisition modes')
        from .connector.fix_capture import capture_fix_price
        base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
        if not base.is_absolute():base=Path.home()/'.local/share'
        state=args.state_dir or base/'sfm-fx-new-age'
        try:result=capture_fix_price(state/'state.sqlite3',args.fix_price_credentials or state/'private/fix-price.json',args.capture_fix_depth)
        except (OSError,ValueError,KeyError,TypeError):
            print(json.dumps(dict(result='FIX_CONFIGURATION_OR_OUTPUT_REFUSED',network_state='NOT_ASSERTED_ON_CONFIGURATION_OR_OUTPUT_IO_FAILURE',broker_mutations=0,background_jobs_left=0)));return 2
        print(json.dumps(result,indent=2));return 0 if result['result']=='FIX_ORIGINAL_FULL_BOOK_CAPTURED_CLOSED_EPOCH' else 2
    if args.capture_original_depth is not None or args.prepare_original_point_figure is not None or args.audit_native_feed is not None:
        if sum(value is not None for value in (args.capture_original_depth,args.prepare_original_point_figure,args.audit_native_feed))!=1 or args.fixture_session or args.offline_checkpoint or args.check or args.summary_json or args.validate_supplemental_config or args.acquire_official_context or args.acquire_original_inputs or args.supplemental_config:
            parser.error('Original depth/count commands must run alone without fixture/check/input modes')
        try:
            if args.capture_original_depth is not None or args.audit_native_feed is not None:
                base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
                if not base.is_absolute():base=Path.home()/'.local/share'
                if args.audit_native_feed is not None:
                    from .connector.native_feed_audit import audit_native_feed
                    receipt=audit_native_feed((args.state_dir or base/'sfm-fx-new-age')/'state.sqlite3',args.audit_native_feed)
                else:
                    from .connector.depth_capture import acquire_original_depth
                    receipt=acquire_original_depth((args.state_dir or base/'sfm-fx-new-age')/'state.sqlite3',args.capture_original_depth)
            else:
                from .services.point_figure_preparation import prepare_original_point_figure
                receipt=prepare_original_point_figure(args.prepare_original_point_figure)
        except (OSError,ValueError,TypeError,KeyError,ArithmeticError,TimeoutError) as exc:
            print(json.dumps(dict(result='ORIGINAL_INPUT_PREPARATION_FAILED',error_type=type(exc).__name__,background_jobs_left=0)));return 2
        display=dict(receipt)
        if 'symbols' in display:display['symbols']={key:{k:v for k,v in row.items() if k!='observed_levels'} for key,row in display['symbols'].items()}
        print(json.dumps(display,indent=2))
        return 0 if receipt['result'] in {'ORIGINAL_DEPTH_CAPTURED_NOT_ADMITTED_AS_VENUE_BOOK','ORIGINAL_POINT_FIGURE_PREPARED_EXPLICIT_COUNT','CTRADER_NATIVE_FEED_AUDITED'} else 2
    if args.acquire_original_inputs is not None:
        if args.fixture_session or args.offline_checkpoint or args.check or args.summary_json or args.validate_supplemental_config or args.acquire_official_context or args.supplemental_config:
            parser.error('Original acquisition cannot be combined with fixture/check/input modes')
        from .connector.original_capture import acquire_original_inputs
        base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
        if not base.is_absolute():base=Path.home()/'.local/share'
        state=args.state_dir or base/'sfm-fx-new-age'
        try:receipt=acquire_original_inputs(state/'state.sqlite3',args.acquire_original_inputs)
        except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
            print(json.dumps(dict(result='ACQUISITION_FAILED',error_type=type(exc).__name__,background_jobs_left=0)));return 2
        print(json.dumps({k:v for k,v in receipt.items() if k not in {'original_quote_jobs','official_responses'}},indent=2))
        return 0 if receipt['result']=='ORIGINAL_ACQUISITION_COMPLETE_NOT_ALL_STRATEGIES_COMPLETE' else 2
    if args.acquire_official_context is not None:
        from .connector.official_context import binding_from_database,acquire_official_context
        if args.fixture_session or args.offline_checkpoint or args.check or args.summary_json or args.validate_supplemental_config or args.supplemental_config:
            parser.error('Original official acquisition cannot be combined with fixture/check modes')
        base=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
        if not base.is_absolute():base=Path.home()/'.local/share'
        state=args.state_dir or base/'sfm-fx-new-age'
        try:receipt=acquire_official_context(binding_from_database(state/'state.sqlite3'),args.acquire_official_context)
        except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
            print(json.dumps(dict(result='ACQUISITION_FAILED',error_type=type(exc).__name__,broker_requests=0,background_jobs_started=0)));return 2
        print(json.dumps(dict(result='ORIGINAL_OFFICIAL_CONTEXT_ACQUIRED',configuration=receipt['configuration'],envelopes=receipt['envelopes'],fed_coverage=receipt['fed_coverage'],cot_availability_basis=receipt['cot_availability_basis'],broker_requests=0,background_jobs_started=0),indent=2));return 0
    if args.validate_supplemental_config is not None:
        from .services.supplemental_files import load_config
        try:config=load_config(args.validate_supplemental_config,allow_fixture=args.fixture_session)
        except (OSError,ValueError,TypeError,KeyError,RecursionError):
            print(json.dumps(dict(result='REJECTED',reason='Invalid supplemental source configuration',network_started=False,records_admitted=0)));return 2
        print(json.dumps(dict(result='VALID_CONFIGURATION_ONLY',providers=len(config['providers']),kinds=sorted({k for p in config['providers'] for k in p['kinds']}),input_files_read=False,network_started=False,records_admitted=0)));return 0
    if args.check:
        result = run_checks()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['ok'] else 1
    if args.summary_json:
        runtime = ApplicationRuntime()
        try:
            print(json.dumps(runtime.architecture_summary(), indent=2, sort_keys=True))
        finally:
            runtime.close()
        return 0
    if args.offline_checkpoint:
        from .testing.checkpoint import run_checkpoint
        result = run_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['ok'] else 1
    if args.fixture_session:
        from .testing.fixtures import fixture_runtime
        runtime = fixture_runtime()
        if args.supplemental_config is not None:
            from .services.supplemental_files import SupplementalFileIngress
            runtime.supplemental_ingress=SupplementalFileIngress(runtime.analytics.supplemental,args.supplemental_config,allow_fixture=True)
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))
        if not base.is_absolute():
            base = Path.home()/'.local/share'
        state_dir = args.state_dir or base/'sfm-fx-new-age'
        runtime = ApplicationRuntime(state_dir/'state.sqlite3',supplemental_config=args.supplemental_config,native_analytical_feed=True,activity_alternatives=not args.strict_genuine_data,compute_workers=compute_workers)
    # Headless CLI commands above must never import Qt or fall through to GUI startup.
    from .app import run_app
    return run_app(runtime)


if __name__ == '__main__':
    raise SystemExit(main())
