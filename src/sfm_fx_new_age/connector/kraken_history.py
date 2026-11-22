"""Bounded range-only access to official Kraken hourly archives.

Never downloads the full multi-GB archive, and never extracts archive paths.
Range sizes, total transport and uncompressed member sizes are hard bounded.
CRC validates selected members; this is not a whole-archive SHA verification.
"""
from bisect import bisect_right
from io import RawIOBase
from pathlib import Path
from threading import Event
from urllib.request import Request,urlopen
from zipfile import ZipFile
from hashlib import sha256
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import csv,io,json,os,re

BASE='https://assets.kraken.com/marketing/institutions/Kraken_OHLCVT_Full.zip.part'
MAX_TRANSPORT=32_000_000


class RangeArchive(RawIOBase):
    def __init__(self,stop,receipt=None):
        self.stop=stop;self.receipt=receipt;self.sizes=[];self.offsets=[0];self.position=0;self.transferred=0
        for i in range(5):
            data,total=self._request(i,0,0)
            self.sizes.append(total);self.offsets.append(self.offsets[-1]+total)
        self.total=self.offsets[-1]

    def _request(self,part,start,end):
        if self.stop.is_set():raise InterruptedError('History source stopped')
        if not 0<=part<5 or end<start or end-start+1>10_000_000 or self.transferred+end-start+1>MAX_TRANSPORT:
            raise ValueError('Official archive transport budget')
        url=BASE+f'{part:02d}';request=Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'Mozilla/5.0 SFMFXReadOnly/1.0'})
        with urlopen(request,timeout=5) as r:
            if r.status!=206 or r.geturl()!=url:raise ValueError('Exact official range response required')
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',r.headers.get('Content-Range',''))
            if not match or (int(match[1]),int(match[2]))!=(start,end):raise ValueError('Wrong native archive range')
            raw=r.read(end-start+2)
            if len(raw)!=end-start+1:raise ValueError('Truncated or unbounded archive range')
            total=int(match[3]);etag=r.headers.get('ETag')
        self.transferred+=len(raw)
        if self.receipt is not None:self.receipt.append(dict(url=url,start=start,end=end,total=total,etag=etag,sha256=sha256(raw).hexdigest()))
        return raw,total

    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        target=offset if whence==0 else self.position+offset if whence==1 else self.total+offset
        if not 0<=target<=self.total:raise ValueError('Archive seek outside bounds')
        self.position=target;return target
    def read(self,size=-1):
        if size<0:size=self.total-self.position
        if size>10_000_000:raise ValueError('Unbounded archive read refused')
        size=min(size,self.total-self.position);chunks=[]
        while size:
            part=bisect_right(self.offsets,self.position)-1
            start=self.position-self.offsets[part];count=min(size,self.sizes[part]-start)
            raw,total=self._request(part,start,start+count-1)
            if total!=self.sizes[part]:raise ValueError('Archive size changed during read')
            chunks.append(raw);self.position+=count;size-=count
        return b''.join(chunks)


def acquire_hour_history(symbols,cache,stop,*,receipt=None):
    """Fetch six exact allowlisted H1 CSV members; cache sealed own originals."""
    from .kraken_public import stamp
    allowed={'EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD'}
    if not set(symbols)<=allowed:raise ValueError('No synthetic historical instrument')
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True,mode=0o700)
    manifest=cache/'hour-history.json';now=datetime.now(timezone.utc)
    if manifest.is_file() and not manifest.is_symlink():
        existing=json.loads(manifest.read_bytes())
        if existing.get('schema_version')==1 and set(symbols)<=set(existing.get('pairs',{})):
            for symbol,info in existing['pairs'].items():
                if symbol not in allowed:raise ValueError('Untrusted archive cache symbol')
                raw=(cache/(symbol+'-60.csv')).read_bytes()
                if sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Original archive cache changed')
            return existing
    ranges=[];reader=RangeArchive(stop,ranges);pairs={}
    with ZipFile(reader) as archive:
        names=archive.namelist()
        for symbol in symbols:
            candidates=[n for n in names if n.rsplit('/',1)[-1] in (symbol+'_60.csv',('X'+symbol[:3]+'Z'+symbol[3:])+'_60.csv')]
            if len(candidates)!=1:raise ValueError('Exact native hourly member not found: '+symbol)
            info=archive.getinfo(candidates[0])
            if info.file_size>16_000_000 or info.compress_size>8_000_000:raise ValueError('Native member size budget')
            raw=archive.read(info)  # ZipFile independently verifies CRC32.
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
            if not rows or any(len(r)!=7 for r in rows):raise ValueError('Native hourly CSV shape')
            first,last=int(rows[0][0]),int(rows[-1][0])
            if last>now.timestamp() or first>=last:raise ValueError('Native archive chronology')
            dest=cache/(symbol+'-60.csv');temporary=cache/(symbol+'-60.csv.new')
            temporary.write_bytes(raw);temporary.chmod(0o600);temporary.replace(dest)
            pairs[symbol]=dict(member=info.filename,sha256=sha256(raw).hexdigest(),crc32=info.CRC,bytes=len(raw),rows=len(rows),first=first,last=last)
    body=dict(schema_version=1,origin='KRAKEN_OFFICIAL_HOURLY_CSV',first_verified_at=stamp(datetime.now(timezone.utc)),
              complete_archive_sha_verified=False,selected_member_crc_verified=True,transport_bytes=reader.transferred,pairs=pairs,ranges=ranges)
    temporary=cache/'hour-history.json.new';temporary.write_text(json.dumps(body,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(manifest)
    if receipt is not None:receipt.extend(ranges)
    return body


def history_rows(cache,symbol,metadata,received_at):
    """Return actual closed H1 quantities only; never zero-fill missing CSV rows."""
    from .kraken_public import stamp
    info=metadata['pairs'][symbol];raw=(Path(cache)/(symbol+'-60.csv')).read_bytes()
    if sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Historical source hash changed')
    cutoff=datetime.fromisoformat(received_at.replace('Z','+00:00'))-timedelta(days=240)
    output=[];last=None
    for row in csv.reader(io.StringIO(raw.decode('utf-8-sig'))):
        timestamp=int(row[0]);start=datetime.fromtimestamp(timestamp,timezone.utc);end=start+timedelta(hours=1)
        if start<cutoff:continue
        q=Decimal(row[5]);count=int(row[6])
        if timestamp%3600 or last is not None and timestamp<=last or not q.is_finite() or q<=0 or count<=0:
            raise ValueError('Invalid original historical hourly quantity')
        last=timestamp
        if end>datetime.fromisoformat(received_at.replace('Z','+00:00')):continue
        output.append(dict(id='KRAKEN:H1:'+str(timestamp),time=stamp(start),end_time=stamp(end),available_at=received_at,quantity=str(q),trade_count=count))
    return tuple(output)
