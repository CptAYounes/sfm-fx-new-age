"""Strict cTrader FIX 4.4 QUOTE framing and full-book reconstruction.

No execution channel, trade prints or inferred tape. A native W snapshot with
IDs/sizes is necessary before X deltas can qualify a book. Sequence gaps/reset,
unknown deletions and malformed groups invalidate the session; never patch gaps.
"""
from datetime import datetime,timezone
from decimal import Decimal
SOH=b'\x01'
MAX_FRAME=262144
OUT_FIELDS={'A':{98,108,141,553,554},'0':{112},'1':{112},'5':set(),'x':{320,559},'V':{262,263,264,265,267,269,146,55}}

class FixError(ValueError):pass

def text(value):
    if not isinstance(value,str) or not 0<len(value)<=1024 or not value.isascii() or any(ord(c)<32 or ord(c)>126 or c=='|' for c in value):raise FixError('Bounded printable FIX value required')
    return value

def stamp(value):
    try:
        parsed=datetime.strptime(value,'%Y%m%d-%H:%M:%S.%f' if '.' in value else '%Y%m%d-%H:%M:%S').replace(tzinfo=timezone.utc)
    except (ValueError,TypeError):raise FixError('Native FIX UTC timestamp required') from None
    return parsed.isoformat().replace('+00:00','Z')

def encode_quote(message_type,sequence,sender,target,fields=(),*,sending_time=None):
    if message_type not in OUT_FIELDS:raise FixError('Only QUOTE administration, list and data requests permitted')
    if type(sequence) is not int or sequence<1:raise FixError('Positive FIX sequence required')
    pairs=list(fields)
    if any(type(k) is not int or k not in OUT_FIELDS[message_type] for k,v in pairs):raise FixError('Unsupported QUOTE request field')
    tags=[k for k,v in pairs]
    if message_type=='V':
        singles={k:v for k,v in pairs if k not in {269,55}}
        if len(singles)!=len(pairs)-tags.count(269)-tags.count(55) or set(singles)!={262,263,264,265,267,146} or singles[263] not in {'1','2'} or singles[264]!='0' or singles[265]!='1' or singles[267]!='2' or [v for k,v in pairs if k==269]!=['0','1']:raise FixError('Full-book bid/offer subscription only')
        symbols=[v for k,v in pairs if k==55]
        if not symbols or len(symbols)>7 or len(set(symbols))!=len(symbols) or any(not s.isdecimal() for s in symbols) or singles[146]!=str(len(symbols)):raise FixError('Unique native instrument IDs required')
        pairs=[(k,singles[k]) for k in (262,263,264,265,267)]+[(269,'0'),(269,'1'),(146,str(len(symbols)))]+[(55,s) for s in symbols]
    elif len(tags)!=len(set(tags)):raise FixError('Duplicate administrative field')
    required={'A':{98,108,141,553,554},'1':{112},'x':{320,559},'0':set(),'5':set()}
    if message_type in required and not required[message_type]<=set(tags):raise FixError('Required QUOTE field absent')
    if message_type=='A' and ({k:v for k,v in pairs}.get(98)!='0' or {k:v for k,v in pairs}.get(141)!='Y' or {k:v for k,v in pairs}.get(108)!='30'):raise FixError('Reset bounded-heartbeat TLS logon only')
    if message_type=='x' and dict(pairs)[559]!='0':raise FixError('Symbol security list only')
    now=sending_time or datetime.now(timezone.utc).strftime('%Y%m%d-%H:%M:%S.%f')[:-3]
    stamp(now)
    header=[(35,message_type),(49,sender),(56,target),(50,'QUOTE'),(57,'QUOTE'),(34,str(sequence)),(52,now)]
    body=b''.join(str(k).encode()+b'='+text(v).encode()+SOH for k,v in header+pairs)
    prefix=b'8=FIX.4.4\x019='+str(len(body)).encode()+SOH+body
    frame=prefix+b'10='+f'{sum(prefix)%256:03d}'.encode()+SOH
    if len(frame)>MAX_FRAME:raise FixError('FIX frame budget exhausted')
    return frame

class Decoder:
    def __init__(self):self.buffer=b''
    def feed(self,data):
        if not isinstance(data,bytes) or len(self.buffer)+len(data)>MAX_FRAME*2:raise FixError('FIX receive budget exhausted')
        self.buffer+=data;frames=[]
        while self.buffer:
            prefix=b'8=FIX.4.4\x019='
            if not self.buffer.startswith(prefix):
                if len(self.buffer)<len(prefix) and prefix.startswith(self.buffer):break
                raise FixError('Unexpected FIX frame prefix')
            end=self.buffer.find(SOH,len(prefix))
            if end<0:
                if len(self.buffer)>30:raise FixError('Unbounded FIX body length')
                break
            value=self.buffer[len(prefix):end]
            if not value.isdigit() or len(value)>6:raise FixError('Invalid body length')
            length=int(value);total=end+1+length+7
            if not 0<length<=MAX_FRAME-40:raise FixError('FIX body length budget')
            if len(self.buffer)<total:break
            raw=self.buffer[:total];self.buffer=self.buffer[total:]
            trailer=raw[-7:]
            if trailer[:3]!=b'10=' or not trailer[3:6].isdigit() or trailer[-1:]!=SOH or sum(raw[:-7])%256!=int(trailer[3:6]):raise FixError('FIX checksum/trailer mismatch')
            fields=[]
            for item in raw[:-1].split(SOH):
                k,sep,v=item.partition(b'=')
                if not sep or not k.isdigit():raise FixError('Invalid FIX tag')
                try:value=v.decode('ascii')
                except UnicodeError:raise FixError('FIX ASCII required') from None
                text(value);fields.append((int(k),value))
            if fields[0]!=(8,'FIX.4.4') or fields[1]!=(9,str(length)) or fields[2][0]!=35:raise FixError('Invalid FIX field order')
            frames.append((raw,tuple(fields)))
        return frames

def one(fields,tag,default=None) -> str:
    values=[v for k,v in fields if k==tag]
    if len(values)>1 or (not values and default is None):raise FixError('Missing/duplicate FIX scalar')
    result=values[0] if values else default
    if not isinstance(result,str):raise FixError('Textual FIX scalar required')
    return result

def groups(fields,count_tag,delimiter,allowed):
    starts=[i for i,(tag,value) in enumerate(fields) if tag==count_tag]
    if len(starts)!=1:raise FixError('Unique FIX group count required')
    i=starts[0];count=fields[i][1]
    if not count.isdigit() or int(count)>5000:raise FixError('FIX group count budget')
    rows=[];current=None
    for tag,value in fields[i+1:]:
        if tag==10:break
        if tag==delimiter:
            if current is not None:rows.append(current)
            current={tag:value}
        elif current is None or tag not in allowed or tag in current:raise FixError('Unexpected/duplicate repeating-group field')
        else:current[tag]=value
    if current is not None:rows.append(current)
    if len(rows)!=int(count):raise FixError('FIX repeating-group count mismatch')
    return rows

def positive(value):
    try:r=Decimal(value)
    except Exception:raise FixError('FIX price/size decimal required') from None
    if not r.is_finite() or r<=0:raise FixError('Positive FIX price/size required')
    return r

class QuoteBook:
    def __init__(self,symbol_ids):
        if not symbol_ids or len(symbol_ids)>7 or len(set(symbol_ids.values()))!=len(symbol_ids):raise FixError('Exact native book mapping required')
        self.symbol_ids=dict(symbol_ids);self.books={s:{} for s in symbol_ids.values()};self.initialized=set();self.failed=False
    def invalidate(self):
        self.failed=True;self.initialized.clear()
        for book in self.books.values():book.clear()
    def apply(self,fields):
        if self.failed:raise FixError('Book session was invalidated')
        try:return self._apply(fields)
        except (ValueError,KeyError,ArithmeticError):self.invalidate();raise
    def _apply(self,fields):
        kind=one(fields,35);changed=set()
        if kind=='W':
            symbol=self.symbol_ids[one(fields,55)];rows=groups(fields,268,269,{269,299,270,271,278});book={}
            for row in rows:
                if row.get(269) not in {'0','1'} or not {270,271,278}<=set(row) or row[278] in book:raise FixError('Full native snapshot IDs/sizes required; spot is insufficient')
                book[row[278]]=(row[269],positive(row[270]),positive(row[271]))
            self.books[symbol]=book;self.initialized.add(symbol);changed.add(symbol)
        elif kind=='X':
            updates={s:dict(book) for s,book in self.books.items()}
            for row in groups(fields,268,279,{279,269,278,55,270,271}):
                if not {278,55}<=set(row):raise FixError('Native delta identity absent')
                symbol=self.symbol_ids[row[55]]
                if symbol not in self.initialized:raise FixError('Delta before full native W snapshot; no inferred initialization')
                book=updates[symbol];identity=row[278]
                if row[279]=='0':
                    if identity in book or row.get(269) not in {'0','1'} or not {270,271}<=set(row):raise FixError('Invalid native NEW depth entry')
                    book[identity]=(row[269],positive(row[270]),positive(row[271]))
                elif row[279]=='2':
                    if identity not in book:raise FixError('Unknown native deletion invalidates book')
                    del book[identity]
                else:raise FixError('Only cTrader NEW/DELETE deltas supported')
                changed.add(symbol)
            self.books=updates
        else:raise FixError('Only native FIX W/X form book updates')
        if any(len(b)>5000 for b in self.books.values()):raise FixError('Native book ID budget')
        return changed
    def levels(self,symbol):
        if self.failed or symbol not in self.initialized:raise FixError('Native full snapshot not initialized')
        sides={'0':{},'1':{}}
        for side,price,quantity in self.books[symbol].values():sides[side][price]=sides[side].get(price,Decimal(0))+quantity
        bids=[[str(p),str(q)] for p,q in sorted(sides['0'].items(),reverse=True)];asks=[[str(p),str(q)] for p,q in sorted(sides['1'].items())]
        if not bids or not asks or len(bids)>100 or len(asks)>100 or Decimal(bids[0][0])>=Decimal(asks[0][0]):return None
        return dict(bids=bids,asks=asks)
