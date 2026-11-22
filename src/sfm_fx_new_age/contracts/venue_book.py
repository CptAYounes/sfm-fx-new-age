"""Pure numeric integrity for the Kraken documented top-ten L2 CRC32."""
import zlib


def book_checksum(bids,asks):
    parts=[]
    for levels,reverse in ((asks,False),(bids,True)):
        for price in sorted(levels,reverse=reverse)[:10]:
            for value in (price,levels[price]):
                parts.append(format(value,'f').replace('.','').lstrip('0'))
    return zlib.crc32(''.join(parts).encode())&0xffffffff
