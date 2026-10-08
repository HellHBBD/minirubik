"""Verify every permutation/orientation coordinate with one Ripes batch."""

import json
import os
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from check_smoke import debug_image, object_data


def check(ripes, elf, processor):
    image = debug_image(elf)
    count, = struct.unpack('<I', object_data(image, 'cube_rank_case_count'))
    cases = object_data(image, 'cube_rank_cases')
    if count != 5040 + 729 - 1 or len(cases) != count * 18:
        raise ValueError('Ranking fixtures do not cover the expected domains')
    for i in range(count):
        row = cases[i * 18:(i + 1) * 18]
        p, q = struct.unpack_from('<HH', row, 14)
        expected = (i, 0) if i < 5040 else (0, i - 5040 + 1)
        if (p, q) != expected:
            raise ValueError('Ranking fixture coordinate order is incorrect')
        if sorted(row[:7]) != list(range(7)) or \
                any(v >= 3 for v in row[7:14]) or sum(row[7:14]) % 3:
            raise ValueError('Ranking fixture contains an invalid cubie state')
    command = [ripes, '--mode', 'cli', '--src', elf, '-t', 'elf',
               '--proc', processor, '--timeout', '30000', '--json',
               '--iret', '--regs', '--runinfo', '--exectime']
    result = subprocess.run(command, capture_output=True, text=True,
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            timeout=45)
    if result.returncode != 0 or 'ERROR:' in result.stdout + result.stderr:
        raise ValueError('Ripes failed: ' + result.stdout + result.stderr)
    start = result.stdout.find('{')
    if start < 0:
        raise ValueError('Ripes did not produce a JSON report')
    report, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
    regs = report['registers']
    if regs['x8'] != count or regs['x18'] != count or regs['x19'] != 0 or regs['x10'] != 0:
        raise ValueError(f'RV32I ranking failed after {regs["x8"]} records')
    if regs['x9'] != image[2]['cube_rank_cases'][0] + count * 18:
        raise ValueError('Ranking kernel did not traverse the complete fixture')
    if regs['x2'] != image[2]['__stack_top'][0]:
        raise ValueError('Rank function did not preserve sp')
    if 'RV32I ranks verified\n' not in result.stdout:
        raise ValueError('Rank kernel did not print its success marker')
    if report['# instructions retired'] <= 0:
        raise ValueError('Ripes did not retire instructions')
    if report['runinfo']['processor'] != processor or report['runinfo']['ISA extensions'] != []:
        raise ValueError('Ranking processor/ISA configuration is incorrect')
    Path(elf).with_suffix('.report.json').write_text(
        json.dumps({'command': command, 'count': count, 'report': report}, indent=2) + '\n')
    print(f'RV32I rank domains passed: 5040 P, 729 Q, {count} records; '
          f'{report["# instructions retired"]} instructions retired')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_ranks.py RIPES ELF PROCESSOR')
    try:
        check(*sys.argv[1:])
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
