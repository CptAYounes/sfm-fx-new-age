"""Exact SDK protocol mapping. Values are validated before protobuf serialization."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from sfm_fx_new_age.contracts.domain import Bar,Origin,SymbolSpec,instant,decimal


def milliseconds(value:str)->int:return int(instant(value).timestamp()*1000)
def timestamp(value:int)->str:return datetime.fromtimestamp(int(value)/1000,timezone.utc).isoformat().replace('+00:00','Z')


def new_limit_request(order:dict,spec:SymbolSpec):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq
    from ctrader_open_api.messages import OpenApiModelMessages_pb2 as D
    if order.get('order_type')!='LIMIT' or order.get('side') not in {'BUY','SELL'}:raise ValueError('Human pending LIMIT orders only')
    if order.get('scope_id')!=spec.scope_id or str(order['account_id'])!=spec.account_id:raise ValueError('Native order/specification scope mismatch')
    if order.get('broker_stop_loss') is not None or order.get('broker_take_profit') is not None:raise ValueError('Broker SL/TP not enabled by this connector')
    price,units=decimal(order['entry_price'],positive=True),decimal(order['units'],positive=True)
    spec.validate_order(price,units)
    volume=units*100
    if volume!=volume.to_integral_value():raise ValueError('Protocol volume must be exact hundredths of units')
    identity=order['client_order_id']
    if not identity or len(identity)>50:raise ValueError('Native clientOrderId length invalid')
    request=ProtoOANewOrderReq(ctidTraderAccountId=int(order['account_id']),symbolId=spec.broker_symbol_id,
        orderType=D.LIMIT,tradeSide=D.BUY if order['side']=='BUY' else D.SELL,volume=int(volume),limitPrice=float(price),
        timeInForce=D.GOOD_TILL_DATE,expirationTimestamp=milliseconds(order['expires_at']),
        label='SFM_NEW_AGE',comment='Human Issue / '+identity,clientOrderId=identity)
    if not request.IsInitialized():raise ValueError('Incomplete native pending-order request')
    return request


def symbol_spec(account_id:str,symbol:str,raw:dict,*,scope_id:str,origin=Origin.LIVE_OBSERVED)->SymbolSpec:
    required=('symbolId','digits','pipPosition','minVolume','maxVolume','stepVolume','lotSize')
    if any(k not in raw for k in required):raise ValueError('Complete native volume and precision metadata required')
    return SymbolSpec(account_id,symbol,int(raw['symbolId']),Decimal(10)**-int(raw['pipPosition']),
        Decimal(10)**-int(raw['digits']),Decimal(raw['minVolume'])/100,Decimal(raw['maxVolume'])/100,
        Decimal(raw['stepVolume'])/100,Decimal(raw['lotSize'])/100,origin,scope_id)


def trendbar(raw:dict,*,symbol:str,timeframe:str,source_epoch:str,scope_id:str,received_at:str,
             close_time:str,revision:int=1)->Bar:
    if 'utcTimestampInMinutes' not in raw or 'low' not in raw:raise ValueError('Timestamped native trendbar required')
    opened=timestamp(int(raw['utcTimestampInMinutes'])*60000)
    low=Decimal(raw['low'])/100000
    value=lambda key:low+Decimal(raw.get(key,0))/100000
    return Bar(symbol,timeframe,opened,close_time,received_at,value('deltaOpen'),value('deltaHigh'),low,value('deltaClose'),
               source_epoch,Origin.LIVE_OBSERVED,scope_id,revision,quote_basis='BID',
               tick_volume=int(raw['volume']) if 'volume' in raw else None)


def execution_state(event:dict)->str:
    code=event.get('executionType')
    return {'ORDER_ACCEPTED':'ACCEPTED_PENDING','ORDER_PARTIAL_FILL':'PARTIALLY_FILLED','ORDER_FILLED':'FILLED',
            'ORDER_REJECTED':'REJECTED','ORDER_CANCELLED':'CANCELED','ORDER_EXPIRED':'EXPIRED'}.get(code,'UNKNOWN')
