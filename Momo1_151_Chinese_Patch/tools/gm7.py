"""Momodora 1.51 resource reader and rewriter (this exact release only)."""
import hashlib
import struct
import zlib
from pathlib import Path

ORIGINAL = '97b6419b3def0f9133a6b1322d113f3ed22b395fbf5d3eaa6dd8dc2dd406e84a'
OFFSET = 0x224B3D
START = 9352
SCRIPTS = 154105
FONT = 179995


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def u32(data, pos):
    return struct.unpack_from('<I', data, pos)[0]


def pack(*values):
    return struct.pack('<' + 'I' * len(values), *values)


def field(value):
    return pack(len(value)) + value


def tables(seed):
    table = list(range(256))
    for i in range(1, 10001):
        j = 1 + (i * (6 + seed % 250) + seed // 250) % 254
        table[j], table[j+1] = table[j+1], table[j]
    return bytes(table), bytes(sorted(range(256), key=table.__getitem__))


def inflate(blob):
    decoder = zlib.decompressobj()
    data = decoder.decompress(blob) + decoder.flush()
    need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'Invalid zlib boundary')
    return data


def unpack_exe(exe, original=False):
    if original:
        need(digest(exe) == ORIGINAL, 'Not the supported original Momodora 1.51 EXE (SHA-256 mismatch)')
    need(u32(exe, OFFSET) == len(exe) - OFFSET - 4, 'Invalid game data length')
    raw = inflate(exe[OFFSET+4:])
    n, m = struct.unpack_from('<II', raw)
    seed = u32(raw, 8 + 4*n)
    start = 12 + 4*(n+m)
    need((n,m,seed,start)==(700,1635,10836,START), 'Invalid game data header')
    _, inv = tables(seed)
    decoded = raw[START+1:].translate(inv)
    plain = raw[:START+1] + bytes((v-i)&255 for i,v in enumerate(decoded, START+1))
    need(u32(plain, START) == 2*seed-1, 'Invalid game data sentinel')
    if original:
        need(digest(plain[START:]) == '359504f3a5ac9a60c1d94541c1ab8ce617ff7a6ce35df4a9b23844948465c58b', 'Unexpected decoded payload')
    return plain


def repack_exe(exe, plain):
    tab, _ = tables(10836)
    raw = plain[:START+1] + bytes((v+i)&255 for i,v in enumerate(plain[START+1:], START+1)).translate(tab)
    if raw == inflate(exe[OFFSET+4:]):
        return exe
    return exe[:OFFSET] + field(zlib.compress(raw, 6))


def scripts(plain):
    need(struct.unpack_from('<II', plain, SCRIPTS) == (400,129), 'Invalid script table')
    p = SCRIPTS+8
    tab, inv = tables(12345)
    results = {}
    for _ in range(129):
        present = u32(plain,p)
        p += 4
        need(present in (0,1), 'Invalid script flag')
        if present:
            namelen = u32(plain,p)
            name = plain[p+4:p+4+namelen].decode('ascii')
            p += 4+namelen
            need(u32(plain,p)==400, 'Invalid script version')
            p += 4
            end = p+4+u32(plain,p)
            body = inflate(plain[p+4:end]).translate(inv)
            need(u32(body,0)==len(body)-4 and name not in results, 'Invalid script body')
            results[name] = (p,end,body[4:])
            p=end
    need(p == FONT and len(results)==95, 'Invalid script table end')
    return results


def script_record(code):
    return field(zlib.compress(field(code).translate(tables(12345)[0]), 6))


def apply_edits(plain, edits):
    result = bytearray()
    cursor = 0
    for start,end,value in sorted(edits):
        need(cursor <= start <= end <= len(plain), 'Overlapping or out-of-bounds resource edits')
        result.extend(plain[cursor:start])
        result.extend(value)
        cursor = end
    result.extend(plain[cursor:])
    return bytes(result)


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[2]
    exe = (root/'momo1_v151.exe').read_bytes()
    plain = unpack_exe(exe, original=True)
    need(repack_exe(exe, plain) == exe, 'Round-trip mismatch')
    items = scripts(plain)
    print('Round trip OK; parsed', len(items), 'scripts.')
    if '--dump' in sys.argv:
        out = Path(__file__).parent/'scratch'
        out.mkdir(exist_ok=True)
        for name,(p,end,code) in items.items():
            need(name.isidentifier(), 'Invalid script name')
            (out/(name+'.gml')).write_bytes(code)
        (out/'outer.bin').write_bytes(plain)
        for name,p in [('menu',222760), ('intro',230063)]:
            (out/(name+'.gml')).write_bytes(plain[p+4:p+4+u32(plain,p)])
