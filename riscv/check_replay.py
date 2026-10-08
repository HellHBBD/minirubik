"""Check replay rejection cases, completion and callee-saved ABI in Ripes."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from check_smoke import debug_image, object_data
from audit_elf import audit


def check(ripes, elf, processor):
    image = debug_image(elf)
    fixtures = object_data(image, 'cube_replay_cases')
    if len(fixtures) != 12 * 24:
        raise ValueError('Replay fixture count differs from the kernel')
    command = [ripes, '--mode', 'cli', '--src', elf, '-t', 'elf',
               '--proc', processor, '--timeout', '30000', '--json',
               '--iret', '--regs', '--runinfo']
    result = subprocess.run(command, capture_output=True, text=True, timeout=45,
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    if result.returncode or 'ERROR:' in result.stdout + result.stderr:
        raise ValueError('Ripes replay check failed: ' + result.stdout + result.stderr)
    start = result.stdout.find('{')
    if start < 0:
        raise ValueError('No replay JSON report')
    report, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
    regs = report['registers']
    if regs['x10'] != 0 or regs['x8'] != 12 or regs['x18'] != 12:
        raise ValueError('Replay kernel failed or did not complete all cases')
    if regs['x9'] != image[2]['cube_replay_cases'][0] + len(fixtures):
        raise ValueError('Replay fixture cursor did not reach the end')
    if regs['x2'] != image[2]['__stack_top'][0]:
        raise ValueError('Replay did not restore sp')
    if any(regs[f'x{r}'] != 103 + i for i, r in enumerate(range(19, 28))):
        raise ValueError('Replay clobbered a callee-saved canary')
    if report['runinfo']['processor'] != processor or report['runinfo']['ISA extensions'] != []:
        raise ValueError('Replay processor or ISA differs from the requested base RV32I')
    output = result.stdout[:start].replace('\0', '')
    if output != 'RV32I replay cases verified\n\nProgram exited with code: 0\n':
        raise ValueError('Replay success output differs from the expected output')
    if report['# instructions retired'] <= 0:
        raise ValueError('Replay did not retire instructions')
    evidence = {'command': command, 'cases': 12, 'report': report, 'audit': audit(elf)}
    Path(elf).with_suffix(f'.{processor}.report.json').write_text(
        json.dumps(evidence, indent=2) + '\n')
    print(f'RV32I replay check passed: {processor}, 12 cases, '
          f'{report["# instructions retired"]} instructions retired')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_replay.py RIPES ELF PROCESSOR')
    try:
        check(*sys.argv[1:])
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
