"""Version-pinned, reproducible MAX9295/3Gbps adaptation of Waveshare GPL module.

Keeps kernel ABI, symbol versions, CSI mappings, probe framework, stream hooks.
Changes only two serializer ID comparisons and three register tables.
No sensor/EEPROM/GPIO writes are introduced on the camera side.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parent
src = ROOT / 'isx031-gmsl-camera-b.original.ko'
out = ROOT / 'isx031-gmsl-camera-b.max9295-3g.ko'
b = bytearray(src.read_bytes())
expected = 'a7262ef59b09d9013670dc41dfe9ef4476011e294a6e04918802fadff437cd6d'
assert hashlib.sha256(b).hexdigest() == expected, 'Wrong original module'
assert b[:6] == b'\x7fELF\x02\x01'
shoff = struct.unpack_from('<Q', b, 40)[0]
shentsize, shnum, shstridx = struct.unpack_from('<HHH', b, 58)
assert shentsize == 64
headers = [list(struct.unpack_from('<IIQQQQIIQQ', b, shoff+i*64)) for i in range(shnum)]
strings_h = headers[shstridx]
strings = b[strings_h[4]:strings_h[4]+strings_h[5]]
def name_at(buf, pos):
    return bytes(buf[pos:buf.index(0, pos)]).decode()
sections = {name_at(strings, h[0]): (i,h) for i,h in enumerate(headers)}
def section(name):
    _, h = sections[name]
    return bytes(b[h[4]:h[4]+h[5]])
sym_h = sections['.symtab'][1]
symstrings_h = headers[sym_h[6]]
symstrings = b[symstrings_h[4]:symstrings_h[4]+symstrings_h[5]]
symbols = {}
for off in range(sym_h[4], sym_h[4]+sym_h[5], 24):
    nm, info, other, idx, val, size = struct.unpack_from('<IBBHQQ', b, off)
    symbols[name_at(symstrings,nm)] = (off,idx,val,size)
ro_i, ro_h = sections['.rodata']
ro = bytearray(section('.rodata'))
text_h = sections['.text'][1]
for offset in (0xcfc, 0xdc4):
    at = text_h[4]+offset
    assert struct.unpack_from('<I',b,at)[0] == 0x7102fc1f  # cmp w0,#0xbf
    struct.pack_into('<I',b,at,0x7102441f)  # cmp w0,#0x91; fail-closed

DSER, SER = -1, -2
def wr(addr,reg,val): return (addr,1,reg,val)
def delay(ms): return (0,0,0,ms)
def ser_video(addr,stream):
    # NVIDIA max9295.c: pipe Z, CSI port B, 1x4 input; YUV422 8-bit DT=0x1e.
    # Lane count/map retained from identical live A/B baseline registers.
    return [wr(addr,2,3),wr(addr,0x330,0),wr(addr,0x331,0x33),
            wr(addr,0x332,0xe0),wr(addr,0x333,4),
            wr(addr,0x318,0x5e),wr(addr,0x311,0x20),wr(addr,0x308,0x64),
            wr(addr,0x5b,stream),wr(addr,2,0x43)]
manifest = {'original_sha256':expected,'id':{'old':'0xbf','new':'0x91'},'tables':{}}
for array,listname in [('gmsl_common_reg','gmsl_common_reg_list'),
                       ('gmsl_1ch_reg','gmsl_1ch_reg_list'),
                       ('gmsl_2ch_reg','gmsl_2ch_reg_list')]:
    _, idx, value, size = symbols[array]
    assert idx == ro_i and size % 12 == 0
    entries = [struct.unpack_from('<iiHH',ro,value+n) for n in range(0,size,12)]
    updated=[]
    reset_pending=False
    for addr,op,reg,val in entries:
        if addr == DSER and op == 1 and reg == 0x10 and val == 0x80:
            reset_pending=True
        if op == 0:
            updated.append((addr,op,reg,val))
            if reset_pending:
                updated.append(wr(DSER,1,1))
                reset_pending=False
            continue
        if addr in (SER,0x44,0x42):
            if reg == 0x383:
                updated.extend(ser_video(addr,2 if addr==0x42 else 1))
                continue
            if reg in (0x2c7,0x318,0x5b):
                continue # remove vendor-camera GPIO and replaced video entries
            assert reg in (0,0x6b,0x73,0x7b,0x83,0x8b,0x93,0x9b,0xa3,0xab), hex(reg)
        updated.append((addr,op,reg,val))
    assert not reset_pending
    while len(ro)%8:ro.append(0)
    new_value=len(ro)
    for entry in updated:ro.extend(struct.pack('<iiHH',*entry))
    list_offset=symbols[listname][2]
    struct.pack_into('<I',ro,list_offset,len(updated))
    # ELF table pointers are relocated against the .rodata section symbol.
    rela_h=sections['.rela.rodata'][1]
    matches=0
    for at in range(rela_h[4],rela_h[4]+rela_h[5],24):
        offset,info,addend=struct.unpack_from('<QQq',b,at)
        if offset == list_offset+8:
            assert (info & 0xffffffff)==257 and addend==value
            struct.pack_into('<q',b,at+16,new_value)
            matches+=1
    assert matches==1
    struct.pack_into('<QQ',b,symbols[array][0]+8,new_value,len(updated)*12)
    manifest['tables'][array]=[{'target':a,'write':bool(o),'register':hex(r),'value':hex(v)}
                              for a,o,r,v in updated]
# Move the complete extended .rodata to an aligned append-only location.
while len(b)%16:b.append(0)
ro_h[4],ro_h[5]=len(b),len(ro)
b.extend(ro)
struct.pack_into('<IIQQQQIIQQ',b,shoff+ro_i*64,*ro_h)
out.write_bytes(b)
manifest['patched_sha256']=hashlib.sha256(b).hexdigest()
(ROOT/'wrist_driver_patch_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'file':str(out),'sha256':manifest['patched_sha256'],
                  'entries':{k:len(v) for k,v in manifest['tables'].items()}},indent=2))
