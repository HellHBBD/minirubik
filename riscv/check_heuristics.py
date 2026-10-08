"""Check every lookup table entry and mixed nibble row against native C."""
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
    representatives = struct.unpack('<35H', object_data(image, 'cube_heuristic_representatives'))
    projection = object_data(image, 'cube_permutation_subset')
    for s, p in enumerate(representatives):
        if p >= 5040 or projection[p] != s:
            raise ValueError('Incorrect mixed subset representative')
    expected = object_data(image, 'cube_heuristic_expected')
    count = 5040 + 35 * 729
    if len(expected) != count or max(expected) > 11:
        raise ValueError('Incorrect heuristic fixture domain')
    command = [ripes, '--mode', 'cli', '--src', elf, '-t', 'elf', '--proc', processor,
               '--timeout', '30000', '--json', '--iret', '--regs', '--runinfo']
    result = subprocess.run(command, capture_output=True, text=True, timeout=45,
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    if result.returncode or 'ERROR:' in result.stdout + result.stderr:
        raise ValueError('Ripes failed: ' + result.stdout + result.stderr)
    at = result.stdout.find('{')
    if at < 0:
        raise ValueError('Missing Ripes report')
    report, _ = json.JSONDecoder().raw_decode(result.stdout[at:])
    regs = report['registers']
    if regs['x8'] != count or regs['x21'] or regs['x10']:
        raise ValueError(f'Heuristic mismatch after {regs["x8"]} cases')
    if regs['x23'] != 35 or regs['x18'] != 0:
        raise ValueError('Mixed rows were not fully traversed')
    if regs['x20'] != image[2]['cube_heuristic_expected'][0] + count:
        raise ValueError('Incomplete expected-distance traversal')
    if regs['x2'] != image[2]['__stack_top'][0]:
        raise ValueError('Heuristic did not preserve sp')
    if 'RV32I heuristics verified\n' not in result.stdout or \
            report['runinfo']['processor'] != processor or report['runinfo']['ISA extensions']:
        raise ValueError('Incorrect marker or processor configuration')
    Path(elf).with_suffix('.report.json').write_text(
        json.dumps({'command': command, 'count': count, 'report': report}, indent=2) + '\n')
    print(f'RV32I heuristic tables passed: {count} calls, all 25515 mixed entries; '
          f'{report["# instructions retired"]} instructions retired')


if __name__ == '__main__':
    try:
        check(*sys.argv[1:])
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
