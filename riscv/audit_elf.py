"""Report linked sizes and reject instructions outside uncompressed RV32I."""
import json
import struct
import sys
from pathlib import Path


def audit(path):
    data = Path(path).read_bytes()
    if data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected little-endian ELF32')
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if h[2] != 243 or h[7] != 0:
        raise ValueError('Expected base RISC-V / soft-float ELF without RVC')
    rows = [struct.unpack_from('<IIIIIIIIII', data, h[6] + i * h[11]) for i in range(h[12])]
    names = rows[h[13]]
    strings = data[names[4]:names[4] + names[5]]
    sections = {strings[r[0]:strings.index(b'\0', r[0])].decode(): r for r in rows}
    text = sections['.text']
    if text[5] % 4:
        raise ValueError('Unaligned instruction stream')
    for at in range(text[4], text[4] + text[5], 4):
        w, = struct.unpack_from('<I', data, at)
        op, f3, f7 = w & 127, (w >> 12) & 7, w >> 25
        valid = w & 3 == 3
        if op == 0x03:
            valid &= f3 in (0, 1, 2, 4, 5)
        elif op == 0x23:
            valid &= f3 in (0, 1, 2)
        elif op == 0x13:
            valid &= (f3 not in (1, 5) or
                      (f3 == 1 and f7 == 0) or (f3 == 5 and f7 in (0, 32)))
        elif op == 0x33:
            valid &= f7 == 0 or (f7 == 32 and f3 in (0, 5))
        elif op == 0x63:
            valid &= f3 in (0, 1, 4, 5, 6, 7)
        elif op == 0x67:
            valid &= f3 == 0
        elif op in (0x17, 0x37, 0x6F):
            pass
        elif op == 0x73:
            valid &= w in (0x73, 0x100073)
        elif op == 0x0F:
            valid &= f3 == 0 and w >> 28 == 0 and ((w >> 7) & 31) == 0 and ((w >> 15) & 31) == 0
        else:
            valid = False
        if not valid:
            raise ValueError(f'Non-RV32I word 0x{w:08x} at text offset {at - text[4]}')
    sizes = {name: sections[name][5] if name in sections else 0
             for name in ('.text', '.rodata', '.data', '.bss')}
    static = sum(sizes[n] for n in ('.rodata', '.data', '.bss'))
    if static > 128 * 1024:
        raise ValueError('Static data exceeds 128 KiB')
    result = {'elf': str(path), 'sections': sizes, 'static_bytes': static,
              'static_instructions': text[5] // 4, 'isa': 'RV32I'}
    Path(path).with_suffix('.audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(audit(sys.argv[1]), indent=2))
    except (ValueError, KeyError) as error:
        raise SystemExit(str(error))
