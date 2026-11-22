"""Native Kraken v2 top-ten L2 with every-message CRC32 validation.

No sequence number is invented. Verified L2 is not full-book/L3 or executions.
"""
from decimal import Decimal
from hashlib import sha256
from datetime import timedelta
import json
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.venue_book import book_checksum


class NativeBook:
    def __init__(self):
        self.bids={};self.asks={};self.ready=False;self.time=None;self.received_at=None;self.checksum=None;self.snapshot_hash=None;self.digest='';self.updates=0

    def apply(self,data,kind,received_at,raw):
        was_ready=self.ready
        self.ready=False
        if kind=='snapshot':bids={};asks={}
        elif kind=='update' and self.snapshot_hash and was_ready:bids=dict(self.bids);asks=dict(self.asks)
        else:raise ValueError('Native L2 snapshot required')
        at=instant(data['timestamp'])
        if at>instant(received_at) or kind=='update' and self.time and at<instant(self.time):raise ValueError('Invalid native book clock')
        for name,levels in (('bids',bids),('asks',asks)):
            rows=data.get(name,[])
            if not isinstance(rows,list) or len(rows)>200:raise ValueError('Native book update budget')
            for row in rows:
                p=Decimal(str(row['price']));q=Decimal(str(row['qty']))
                if not p.is_finite() or not q.is_finite() or p<=0 or q<0:raise ValueError('Invalid native displayed liquidity')
                if q==0:levels.pop(p,None)
                else:levels[p]=q
            ordered=sorted(levels,reverse=name=='bids')[:10]
            keep={p:levels[p] for p in ordered}
            if name=='bids':bids=keep
            else:asks=keep
        checksum=data['checksum']
        if type(checksum) is not int or not 0<=checksum<2**32 or checksum!=book_checksum(bids,asks):raise ValueError('Native L2 checksum mismatch')
        if not bids or not asks or max(bids)>=min(asks):raise ValueError('Two-sided uncrossed native book required')
        self.bids=bids;self.asks=asks;self.time=data['timestamp'];self.received_at=received_at;self.checksum=checksum
        if kind=='snapshot':self.snapshot_hash=sha256(raw.encode()).hexdigest();self.digest=self.snapshot_hash;self.updates=0
        else:self.digest=sha256((self.digest+raw).encode()).hexdigest();self.updates+=1
        self.ready=True

    def row(self,received_at):
        if not self.ready or self.received_at is None or not 0<=(instant(received_at)-instant(self.received_at)).total_seconds()<=5:return None
        return dict(id='KRAKEN:L2:'+self.digest,time=self.time,available_at=self.received_at,
                    bids=[[str(p),str(self.bids[p])] for p in sorted(self.bids,reverse=True)],
                    asks=[[str(p),str(self.asks[p])] for p in sorted(self.asks)],checksum=self.checksum)
