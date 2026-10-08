"""Retain short Ripes pipeline telemetry and measured modulo-three variants."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from calibrate import ripes_identity
from check_smoke import debug_image


def run():
    identity = ripes_identity('/usr/bin/ripes')
    root = Path('build-rv32i/pipeline')
    root.mkdir(exist_ok=True)
    records = []
    for name, source, flags in (('walkthrough', 'riscv/walkthrough.S', []),
                                ('mod-branching', 'riscv/modulo_check.S', ['-DMOD_BRANCHLESS=0']),
                                ('mod-branchless', 'riscv/modulo_check.S', ['-DMOD_BRANCHLESS=1'])):
        obj = root / f'{name}.o'
        elf = root / f'{name}.elf'
        commands = [
            ['clang', '--target=riscv32-unknown-elf', '-march=rv32i', '-mabi=ilp32',
             *flags, '-c', source, '-o', str(obj)],
            ['ld.lld', '-m', 'elf32lriscv', '--no-relax', '-T', 'riscv/link.ld',
             '-o', str(elf.with_suffix('.debug.elf')), str(obj)],
            ['llvm-objcopy', '--strip-all', '--remove-section=.riscv.attributes',
             str(elf.with_suffix('.debug.elf')), str(elf)]]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise ValueError('Pipeline build failed: ' + result.stdout + result.stderr)
        image = debug_image(elf)
        linked = audit(elf)
        for processor in ('RV32_ISS', 'RV32_5S'):
            command = [identity['ripes_path'], '--mode', 'cli', '--src', str(elf), '-t', 'elf',
                       '--proc', processor, '--timeout', '10000', '--json', '--iret', '--cycles',
                       '--cpi', '--regs', '--pipeline', '--runinfo']
            result = subprocess.run(command, capture_output=True, text=True, timeout=20,
                                    env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
            prefix = root / f'{name}-{processor}'
            prefix.with_suffix('.stdout.log').write_text(result.stdout)
            prefix.with_suffix('.stderr.log').write_text(result.stderr)
            if result.returncode or 'ERROR:' in result.stdout + result.stderr:
                raise ValueError('Pipeline run failed: ' + result.stdout + result.stderr)
            start = result.stdout.find('{')
            if start < 0 or result.stdout[:start] != '\nProgram exited with code: 0\n':
                raise ValueError('Pipeline example did not exit successfully')
            report, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
            trace = report['pipeline']
            prefix.with_suffix('.pipeline.tsv').write_text(trace)
            regs = report['registers']
            if regs['x10'] != 0 or regs['x2'] != image[2]['__stack_top'][0]:
                raise ValueError('Pipeline guest status or stack pointer failed')
            if name == 'walkthrough':
                if regs['x8'] != 0 or regs['x9'] != 14 or regs['x18'] != 28:
                    raise ValueError('Forward/store/load-use example produced the wrong result')
                if processor == 'RV32_5S':
                    row = next((line for line in trace.splitlines()
                                if line.startswith('add x18 x9 x7\t')), None)
                    if row is None or [c for c in row.split('\t')[1:] if c] != \
                            ['IF', 'ID', '-', 'EX', 'MEM', 'WB']:
                        raise ValueError('Walkthrough trace did not show the expected load-use stall')
            elif regs['x8'] != 9 or regs['x9'] != 9 or regs['x18'] != 0:
                raise ValueError('Modulo example did not verify all nine pairs')
            if report['runinfo']['processor'] != processor or report['runinfo']['ISA extensions'] != []:
                raise ValueError('Pipeline processor or base ISA mismatch')
            record = {'name': name, 'processor': processor, 'command': command,
                      'audit': linked, 'report': report,
                      'pipeline_tsv': str(prefix.with_suffix('.pipeline.tsv'))}
            records.append(record)
            prefix.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
            print(f'{name} {processor}: {report["# instructions retired"]} iret', flush=True)
    summary = {'identity': identity, 'records': records,
               'gui_signal_visualization': 'PENDING: scoped Desktop screenshot unavailable'}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for processor in ('RV32_ISS', 'RV32_5S'):
        pair = [r for r in records if r['processor'] == processor and r['name'].startswith('mod-')]
        if pair[1]['report']['# instructions retired'] - pair[0]['report']['# instructions retired'] != 15:
            raise ValueError('Modulo retired difference does not match the nine-pair operation count')


if __name__ == '__main__':
    try:
        run()
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
