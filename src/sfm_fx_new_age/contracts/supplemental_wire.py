"""Exact wire shapes for opt-in file inputs; no arbitrary record payloads."""
from sfm_fx_new_age.contracts.domain import decimal,instant
from uuid import UUID

BASE={'id','time','available_at'}
FIELDS={
 'TRADED_PRINTS':{'price','quantity'},'AGGRESSOR_PRINTS':{'price','quantity','aggressor'},
 'EXECUTED_BAR_QUANTITIES':{'end_time','quantity','trade_count'},
 'EXECUTED_WEEK_QUANTITIES':{'end_time','quantity','trade_count'},
 'INTRABAR_PRICES':{'price'},'POINT_FIGURE_TICKS':{'price'},'VENUE_BOOK':{'sequence','bids','asks'},'VENUE_L2_CHECKSUM_BOOK':{'checksum','bids','asks'},'VENUE_NATIVE_CHAIN_BOOK':{'event_id','pre_event_id','bids','asks'},'BROKER_DEPTH':{'bids','asks'},
 'CFTC_REPORT':{'currency','report_type','report_as_of','long','short','open_interest'},
 'OFFICIAL_CALENDAR':{'currency','title','importance','scheduled_at'}}
PARAMS={'TRADED_PRINTS':{'tick_size'},'AGGRESSOR_PRINTS':set(),'EXECUTED_BAR_QUANTITIES':set(),'EXECUTED_WEEK_QUANTITIES':set(),'INTRABAR_PRICES':{'tick_size','slot_coverage_complete'},
 'POINT_FIGURE_TICKS':{'box_size','reversal_boxes','count_line','count_start','count_end','side'},'VENUE_BOOK':set(),
 'VENUE_L2_CHECKSUM_BOOK':{'depth','native_sequence','full_book_complete','checksum_algorithm','snapshot_hash','clock_basis'},
 'VENUE_NATIVE_CHAIN_BOOK':{'native_sequence','sequence_model','full_book_complete','scope','clock_basis','snapshot_hash','checkpoint_hash','chain_hash','full_order_count','checkpoint_verified'},
 'BROKER_DEPTH':{'clock_basis','native_sequence','full_book_complete','unknown_deleted_ids','subscription_acknowledged'},'CFTC_REPORT':{'availability_basis'},
 'OFFICIAL_CALENDAR':{'schedule_coverage_start','schedule_coverage_end','coverage_policy'}}


def validate_wire_shape(e):
    for field in ('source_ref','venue','instrument','window_start','window_end','available_at','valid_until'):
        if not isinstance(getattr(e,field),str) or not 0<len(getattr(e,field))<=2048:raise ValueError('Bounded textual source metadata required')
    if not set(e.parameters)<=PARAMS[e.kind]:raise ValueError('Unknown source parameter')
    for row in e.records:
        if set(row)!=BASE|FIELDS[e.kind] or not isinstance(row['id'],str) or len(row['id'])>160:raise ValueError('Exact bounded source observation fields required')
        if e.kind in {'VENUE_BOOK','BROKER_DEPTH','VENUE_L2_CHECKSUM_BOOK','VENUE_NATIVE_CHAIN_BOOK'}:
            if e.kind=='VENUE_BOOK' and (type(row['sequence']) is not int or row['sequence']<1):raise ValueError('Positive venue sequence required')
            if e.kind=='VENUE_NATIVE_CHAIN_BOOK':
                if any(not isinstance(row[k],str) or str(UUID(row[k]))!=row[k] for k in ('event_id','pre_event_id')) or row['event_id']==row['pre_event_id'] or row['id']!='BITSTAMP:L3:'+row['event_id']:
                    raise ValueError('Literal distinct native event/predecessor UUIDs required')
            parsed=[]
            for name,reverse in (('bids',True),('asks',False)):
                levels=row[name]
                if not isinstance(levels,list) or not 0<len(levels)<=(4096 if e.kind=='VENUE_NATIVE_CHAIN_BOOK' else 100):raise ValueError('Bounded two-sided book required')
                values=[]
                for level in levels:
                    if not isinstance(level,list) or len(level)!=2:raise ValueError('Price/quantity book tuple required')
                    values.append(tuple(decimal(v,positive=True) for v in level))
                if values!=sorted(values,key=lambda v:v[0],reverse=reverse) or len({p for p,q in values})!=len(values):raise ValueError('Ordered unique book prices required')
                parsed.append(values)
            if parsed[0][0][0]>=parsed[1][0][0]:raise ValueError('Crossed or locked book rejected')
            if e.kind=='VENUE_L2_CHECKSUM_BOOK':
                from .venue_book import book_checksum
                if type(row['checksum']) is not int or row['checksum']!=book_checksum(dict(parsed[0]),dict(parsed[1])):
                    raise ValueError('Verified native top-ten checksum required')
                if any(len(v)>10 for v in parsed):raise ValueError('Exactly bounded top-ten scope')
        elif e.kind in {'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES'}:
            q=decimal(row['quantity']);count=row['trade_count']
            if (q<0 or type(count) is not int or count<0 or (q==0)!=(count==0)
                or not instant(row['time'])<instant(row['end_time'])<=instant(e.window_end)
                or instant(row['end_time'])>instant(row['available_at'])):
                raise ValueError('Closed actual executed-quantity intervals required')
            if e.kind=='EXECUTED_WEEK_QUANTITIES' and not 6*86400<=(instant(row['end_time'])-instant(row['time'])).total_seconds()<=8*86400:
                raise ValueError('Actual exact broker-week interval required')
        elif e.kind=='CFTC_REPORT':
            currency=e.symbol[3:] if e.symbol.startswith('USD') else e.symbol[:3]
            if row['currency']!=currency or row['report_type']!='LEGACY_NONCOMMERCIAL' or instant(row['report_as_of'])>instant(row['time']):raise ValueError('Published report mapping required')
            long,short,interest=[decimal(row[k]) for k in ('long','short','open_interest')]
            if min(long,short)<0 or interest<=0 or max(long,short)>interest:raise ValueError('Invalid report quantities')
        elif e.kind=='OFFICIAL_CALENDAR':
            if row['currency'] not in {e.symbol[:3],e.symbol[3:]} or not isinstance(row['title'],str) or not 0<len(row['title'])<=200 or row['importance'] not in {'HIGH','MEDIUM','LOW','UNSPECIFIED'}:raise ValueError('Bounded relevant official release required')
            instant(row['scheduled_at'])
    if 'tick_size' in e.parameters:decimal(e.parameters['tick_size'],positive=True)
    if e.kind=='VENUE_NATIVE_CHAIN_BOOK':
        p=e.parameters
        if (set(p)!=PARAMS[e.kind] or p['native_sequence'] is not True or p['full_book_complete'] is not True
            or p['sequence_model']!='NATIVE_UUID_PREDECESSOR_CHAIN' or p['scope']!='FULL_PUBLIC_DISPLAYED_ORDERS'
            or p['clock_basis']!='NATIVE_EVENT_TIME' or p['checkpoint_verified'] is not True
            or type(p['full_order_count']) is not int or not 2<=p['full_order_count']<=20000
            or e.venue!='BITSTAMP_SPOT_FIAT' or e.symbol not in {'EURUSD','GBPUSD'}
            or any(not isinstance(p[k],str) or len(p[k])!=64 or any(c not in '0123456789abcdef' for c in p[k]) for k in ('snapshot_hash','checkpoint_hash','chain_hash'))):
            raise ValueError('Corroborated full public native-chain scope required')
    if e.kind=='VENUE_L2_CHECKSUM_BOOK':
        p=e.parameters
        if (set(p)!=PARAMS[e.kind] or p['depth']!=10 or type(p['depth']) is not int or p['native_sequence'] is not False
            or p['full_book_complete'] is not False or p['checksum_algorithm']!='KRAKEN_V2_CRC32_TOP10' or p['clock_basis']!='LOCAL_RECEIPT_OF_VERIFIED_SNAPSHOT_OR_UPDATE'
            or not isinstance(p['snapshot_hash'],str) or len(p['snapshot_hash'])!=64
            or any(c not in '0123456789abcdef' for c in p['snapshot_hash'])):
            raise ValueError('Explicit checksum L2 scope required; no invented sequence')
    if e.kind=='BROKER_DEPTH':
        p=e.parameters
        if (set(p)!=PARAMS[e.kind] or p['clock_basis']!='LOCAL_RECEIPT_NOT_VENDOR_EVENT_TIME'
            or p['native_sequence'] is not False or p['full_book_complete'] is not False
            or p['subscription_acknowledged'] is not True or type(p['unknown_deleted_ids']) is not int or p['unknown_deleted_ids']<0):
            raise ValueError('Explicit observed broker-depth limitations required')
    if e.kind=='INTRABAR_PRICES' and e.parameters.get('slot_coverage_complete') is not True:raise ValueError('Complete slot declaration required')
    if e.kind=='OFFICIAL_CALENDAR':
        if not {'schedule_coverage_start','schedule_coverage_end'}<=set(e.parameters)<=PARAMS[e.kind] or not instant(e.parameters['schedule_coverage_start'])<instant(e.parameters['schedule_coverage_end']):raise ValueError('Exact schedule coverage required')
        if 'coverage_policy' in e.parameters and e.parameters['coverage_policy']!='FED_BOARD_EXACT_TIMED_EVENTS_ONLY':raise ValueError('Unknown calendar coverage policy')
    if e.kind=='CFTC_REPORT' and 'availability_basis' in e.parameters and e.parameters['availability_basis']!='FIRST_VERIFIED_HTTP_OBSERVATION':raise ValueError('Unknown official observation availability basis')
    if e.kind=='POINT_FIGURE_TICKS':
        if set(e.parameters)!=PARAMS[e.kind] or type(e.parameters['reversal_boxes']) is not int or e.parameters['reversal_boxes']!=3 or e.parameters['side'] not in {'BUY','SELL'}:raise ValueError('Exact P&F count configuration required')
        decimal(e.parameters['box_size'],positive=True);decimal(e.parameters['count_line'],positive=True)
        if not instant(e.window_start)<=instant(e.parameters['count_start'])<instant(e.parameters['count_end'])<=instant(e.window_end):raise ValueError('P&F count interval mismatch')
