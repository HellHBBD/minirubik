"""Compare the RV32I input checkpoint with the native C parser."""

import json
import os
import struct
import subprocess
import sys
from pathlib import Path


def external_input(elf):
    """Read cube_input and stack symbols from the matching debug ELF."""
    data = Path(elf).with_suffix('.debug.elf').read_bytes()
    if data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Input checkpoint requires a little-endian ELF32')
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    sections = [struct.unpack_from('<IIIIIIIIII', data,
                                  header[6] + i * header[11])
                for i in range(header[12])]
    symbols = {}
    for section in sections:
        if section[1] != 2:  # SHT_SYMTAB
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for at in range(section[4], section[4] + section[5], section[9]):
            name, address, size, _, _, index = struct.unpack_from('<IIIBBH', data, at)
            end = names.index(b'\0', name)
            symbols[names[name:end].decode()] = (address, size, index)
    address, size, index = symbols['cube_input']
    section = sections[index]
    at = section[4] + address - section[3]
    raw = data[at:at + size]
    if b'\0' not in raw:
        raise ValueError('cube_input must contain a NUL-terminated string')
    return raw.split(b'\0', 1)[0], symbols['__stack_top'][0]


def fingerprint(values, bits):
    result = 0
    for value in values:
        result = (result << bits) | value
    return result


def check(ripes, elf, processor):
    input_bytes, stack_top = external_input(elf)
    native = subprocess.run([b'./solver', b'--parse-state', input_bytes],
                            capture_output=True, timeout=15)
    if native.returncode not in (0, 2):
        raise ValueError(f'Native parse oracle failed: {native.stderr!r}')
    expected = {'status': native.returncode, 'input_hex': input_bytes.hex()}
    if native.returncode == 0:
        if len(native.stdout) != 14:
            raise ValueError('Native parse oracle did not produce fourteen bytes')
        expected['permutation_fingerprint'] = fingerprint(native.stdout[:7], 3)
        expected['orientation_fingerprint'] = fingerprint(native.stdout[7:], 2)
    else:
        if native.stdout:
            raise ValueError('Native parse oracle emitted an invalid state')
        expected['permutation_fingerprint'] = 0
        expected['orientation_fingerprint'] = 0
    command = [ripes, '--mode', 'cli', '--src', elf, '-t', 'elf',
               '--proc', processor, '--timeout', '5000', '--json',
               '--iret', '--regs', '--runinfo']
    result = subprocess.run(command, capture_output=True, text=True,
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            timeout=15)
    if result.returncode != 0 or 'ERROR:' in result.stdout + result.stderr:
        raise ValueError('Ripes failed: ' + result.stdout + result.stderr)
    start = result.stdout.find('{')
    if start < 0:
        raise ValueError('Ripes did not produce a JSON report')
    report, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
    registers = report['registers']
    if registers['x8'] != native.returncode or registers['x10'] != native.returncode:
        raise ValueError('RV32I guest status differs from the native C parser')
    if registers['x9'] != expected['permutation_fingerprint'] or \
            registers['x18'] != expected['orientation_fingerprint']:
        raise ValueError('RV32I parsed bytes differ from the native C parser')
    if registers['x2'] != stack_top:
        raise ValueError('RV32I parser did not preserve the stack pointer')
    marker = 'RV32I input valid\n' if native.returncode == 0 else 'RV32I input invalid\n'
    if marker not in result.stdout:
        raise ValueError('RV32I guest did not print the expected input marker')
    if report['# instructions retired'] <= 0:
        raise ValueError('Ripes did not retire instructions')
    if report['runinfo']['processor'] != processor:
        raise ValueError('Ripes processor differs from the requested model')
    if report['runinfo']['ISA extensions'] != []:
        raise ValueError('Smoke test requires base RV32I without extensions')
    evidence = {'command': command, 'expected': expected, 'report': report}
    Path(elf).with_suffix('.report.json').write_text(
        json.dumps(evidence, indent=2) + '\n')
    print(f'RV32I smoke passed: {processor}, '
          f'{report["# instructions retired"]} instructions retired, '
          f'input status={native.returncode}, parsed fingerprints match')
    return evidence


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_smoke.py RIPES ELF PROCESSOR')
    try:
        check(*sys.argv[1:])
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
