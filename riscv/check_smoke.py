"""Check guest status as well as the Ripes process result."""

import json
import os
import subprocess
import sys
from pathlib import Path


def check(ripes, elf, processor):
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
    if registers['x8'] != 0 or registers['x10'] != 0:
        raise ValueError('RV32I guest reported a table-check failure')
    if 'RV32I tables ready\n' not in result.stdout:
        raise ValueError('RV32I guest did not print its success marker')
    if report['# instructions retired'] <= 0:
        raise ValueError('Ripes did not retire instructions')
    if report['runinfo']['processor'] != processor:
        raise ValueError('Ripes processor differs from the requested model')
    if report['runinfo']['ISA extensions'] != []:
        raise ValueError('Smoke test requires base RV32I without extensions')
    Path(elf).with_suffix('.report.json').write_text(
        json.dumps({'command': command, 'report': report}, indent=2) + '\n')
    print(f'RV32I smoke passed: {processor}, '
          f'{report["# instructions retired"]} instructions retired, s0=a0=0')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_smoke.py RIPES ELF PROCESSOR')
    try:
        check(*sys.argv[1:])
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
