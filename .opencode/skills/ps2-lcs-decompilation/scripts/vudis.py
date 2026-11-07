#!/usr/bin/env python3
"""Minimal PS2 VU1 microcode disassembler (upper/lower pairs, 8 bytes each)."""
import struct, sys

BC = "xyzw"
def dest(w):
    d = (w >> 21) & 0xf
    return "".join(c for i, c in enumerate(BC) if d & (8 >> i))

def vf(n): return "vf%02d" % n
def vi(n): return "vi%02d" % n

UP_FMAC = {0x28:"add",0x29:"madd",0x2a:"mul",0x2b:"max",0x2c:"sub",0x2d:"msub",0x2e:"opmsub",0x2f:"mini"}
UP_Q = {0x1c:"mulq",0x20:"addq",0x21:"maddq",0x24:"subq",0x25:"msubq"}
UP_I = {0x1d:"maxi",0x1e:"muli",0x1f:"minii",0x22:"addi",0x23:"maddi",0x26:"subi",0x27:"msubi"}
UP_BC = {0x00:"add",0x04:"sub",0x08:"madd",0x0c:"msub",0x10:"max",0x14:"mini",0x18:"mul"}
UPS_BC = {0x00:"adda",0x04:"suba",0x08:"madda",0x0c:"msuba",0x18:"mula"}
UPS = {0x10:"itof0",0x11:"itof4",0x12:"itof12",0x13:"itof15",0x14:"ftoi0",0x15:"ftoi4",0x16:"ftoi12",0x17:"ftoi15",
       0x1c:"mulaq",0x1d:"abs",0x1e:"mulai",0x1f:"clipw",0x20:"addaq",0x21:"maddaq",0x22:"addai",0x23:"maddai",
       0x24:"subaq",0x25:"msubaq",0x26:"subai",0x27:"msubai",0x28:"adda",0x29:"madda",0x2a:"mula",0x2b:"nop",
       0x2c:"suba",0x2d:"msuba",0x2e:"opmula",0x2f:"nop"}

def upper(w):
    op = w & 0x3f
    d = dest(w); ft = (w>>16)&31; fs = (w>>11)&31; fd = (w>>6)&31
    flags = "".join(c for b,c in ((31,"I"),(30,"E"),(29,"M"),(28,"D"),(27,"T")) if w>>b&1)
    bc = BC[op & 3]
    if op in UP_FMAC: s = "%s.%s %s, %s, %s" % (UP_FMAC[op], d, vf(fd), vf(fs), vf(ft))
    elif op in UP_Q: s = "%s.%s %s, %s, Q" % (UP_Q[op], d, vf(fd), vf(fs))
    elif op in UP_I: s = "%s.%s %s, %s, I" % (UP_I[op], d, vf(fd), vf(fs))
    elif op < 0x1c and (op & 0x3c) in UP_BC: s = "%s%s.%s %s, %s, %s%s" % (UP_BC[op&0x3c], bc, d, vf(fd), vf(fs), vf(ft), bc)
    elif op >= 0x3c:
        idx = ((w >> 4) & 0x7c) | (w & 3)
        if idx < 0x1c and (idx & 0x3c) in UPS_BC and idx not in UPS:
            s = "%s%s.%s ACC, %s, %s%s" % (UPS_BC[idx&0x3c], BC[idx&3], d, vf(fs), vf(ft), BC[idx&3])
        elif idx in UPS:
            n = UPS[idx]
            if n == "nop": s = "nop"
            elif n.startswith(("itof","ftoi","abs")): s = "%s.%s %s, %s" % (n, d, vf(ft), vf(fs))
            elif n == "clipw": s = "clipw.xyz %s, %sw" % (vf(fs), vf(ft))
            elif n.endswith("q"): s = "%s.%s ACC, %s, Q" % (n, d, vf(fs))
            elif n.endswith("i"): s = "%s.%s ACC, %s, I" % (n, d, vf(fs))
            else: s = "%s.%s ACC, %s, %s" % (n, d, vf(fs), vf(ft))
        else: s = "?upper idx=%#x" % idx
    else: s = "?upper op=%#x" % op
    return (flags + " " if flags else "") + s

LO = {0x00:"lq",0x01:"sq",0x04:"ilw",0x05:"isw",0x08:"iaddiu",0x09:"isubiu",0x10:"fceq",0x11:"fcset",0x12:"fcand",0x13:"fcor",
      0x14:"fseq",0x15:"fsset",0x16:"fsand",0x17:"fsor",0x18:"fmeq",0x1a:"fmand",0x1b:"fmor",0x1c:"fcget",
      0x20:"b",0x21:"bal",0x24:"jr",0x25:"jalr",0x28:"ibeq",0x29:"ibne",0x2c:"ibltz",0x2d:"ibgtz",0x2e:"iblez",0x2f:"ibgez"}
LS1 = {0x30:"iadd",0x31:"isub",0x32:"iaddi",0x34:"iand",0x35:"ior"}
LS2 = {0x30:"move",0x31:"mr32",0x34:"lqi",0x35:"sqi",0x36:"lqd",0x37:"sqd",0x38:"div",0x39:"sqrt",0x3a:"rsqrt",0x3b:"waitq",
       0x3c:"mtir",0x3d:"mfir",0x3e:"ilwr",0x3f:"iswr",0x40:"rnext",0x41:"rget",0x42:"rinit",0x43:"rxor",0x64:"mfp",
       0x68:"xtop",0x69:"xitop",0x6c:"xgkick",0x70:"esadd",0x71:"ersadd",0x72:"eleng",0x73:"erleng",0x74:"eatanxy",
       0x75:"eatanxz",0x76:"esum",0x78:"ercpr",0x79:"esqrt",0x7a:"ersqrt",0x7b:"ercpr",0x7c:"esin",0x7d:"eatan",0x7e:"eexp",0x7f:"waitp"}

def s11(v): return v - 0x800 if v & 0x400 else v
def s5(v): return v - 32 if v & 16 else v

def lower(w, pc):
    op = (w >> 25) & 0x7f
    d = dest(w); it = (w>>16)&31; is_ = (w>>11)&31; id_ = (w>>6)&31
    imm11 = w & 0x7ff
    fsf = (w>>21)&3; ftf = (w>>23)&3
    if op == 0x00: return "lq.%s %s, %d(%s)" % (d, vf(it), s11(imm11), vi(is_))
    if op == 0x01: return "sq.%s %s, %d(%s)" % (d, vf(is_), s11(imm11), vi(it))
    if op == 0x04: return "ilw.%s %s, %d(%s)" % (d, vi(it), s11(imm11), vi(is_))
    if op == 0x05: return "isw.%s %s, %d(%s)" % (d, vi(it), s11(imm11), vi(is_))
    if op in (0x08,0x09): return "%s %s, %s, %#x" % (LO[op], vi(it), vi(is_), ((w>>21)&0xf)<<11 | imm11)
    if op in (0x20,0x21): return "%s %#x" % (LO[op], pc + 1 + s11(imm11))
    if op in (0x24,0x25): return "%s %s" % (LO[op], vi(is_))
    if op in (0x28,0x29): return "%s %s, %s, %#x" % (LO[op], vi(it), vi(is_), pc + 1 + s11(imm11))
    if op in (0x2c,0x2d,0x2e,0x2f): return "%s %s, %#x" % (LO[op], vi(is_), pc + 1 + s11(imm11))
    if op in LO: return "%s imm=%#x" % (LO[op], w & 0xffffff)
    if op == 0x40:
        o = w & 0x3f
        if o in LS1:
            if o == 0x32: return "iaddi %s, %s, %d" % (vi(it), vi(is_), s5(id_))
            return "%s %s, %s, %s" % (LS1[o], vi(id_), vi(is_), vi(it))
        if o >= 0x3c:
            idx = ((w >> 4) & 0x7c) | (w & 3)
            n = LS2.get(idx, "?lower idx=%#x" % idx)
            if n == "move" and it == 0 and is_ == 0: return "nop"
            if n in ("move","mr32"): return "%s.%s %s, %s" % (n, d, vf(it), vf(is_))
            if n == "lqi": return "lqi.%s %s, (%s++)" % (d, vf(it), vi(is_))
            if n == "sqi": return "sqi.%s %s, (%s++)" % (d, vf(is_), vi(it))
            if n == "lqd": return "lqd.%s %s, (--%s)" % (d, vf(it), vi(is_))
            if n == "sqd": return "sqd.%s %s, (--%s)" % (d, vf(is_), vi(it))
            if n in ("div","rsqrt"): return "%s Q, %s%s, %s%s" % (n, vf(is_), BC[fsf], vf(it), BC[ftf])
            if n == "sqrt": return "sqrt Q, %s%s" % (vf(it), BC[ftf])
            if n == "mtir": return "mtir %s, %s%s" % (vi(it), vf(is_), BC[fsf])
            if n == "mfir": return "mfir.%s %s, %s" % (d, vf(it), vi(is_))
            if n == "ilwr": return "ilwr.%s %s, (%s)" % (d, vi(it), vi(is_))
            if n == "iswr": return "iswr.%s %s, (%s)" % (d, vi(it), vi(is_))
            if n in ("xtop","xitop"): return "%s %s" % (n, vi(it))
            if n == "xgkick": return "xgkick %s" % vi(is_)
            if n in ("rnext","rget"): return "%s.%s %s, R" % (n, d, vf(it))
            if n in ("rinit","rxor"): return "%s R, %s%s" % (n, vf(is_), BC[fsf])
            if n == "mfp": return "mfp.%s %s, P" % (d, vf(it))
            if n.startswith("e"): return "%s P, %s" % (n, vf(is_))
            return n
    return "?lower op=%#x w=%08x" % (op, w)

def dis(data, base_va=0, pc0=0):
    out = []
    for i in range(len(data) // 8):
        lo, hi = struct.unpack_from("<II", data, i*8)
        pc = pc0 + i
        up = upper(hi)
        if hi >> 31 & 1:
            lw = "loi %g (0x%08x)" % (struct.unpack("<f", struct.pack("<I", lo))[0], lo)
        else:
            lw = lower(lo, pc)
        out.append("%04x %08x %-40s %s" % (pc, base_va + i*8, up, lw))
    return "\n".join(out)

if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    import elf_tools as E
    E.load(sys.argv[2])
    start, end = int(sys.argv[3], 16), int(sys.argv[4], 16)
    va0, off, size = E.SEC[".text"]
    data = E.D[off + start - va0: off + end - va0]
    print(dis(data, start))
