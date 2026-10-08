"""Compare the identical full-entry harness with hand or GCC query functions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from calibrate import ripes_identity
from check_gates import input_offset
from check_smoke import check, debug_image, object_data


def run():
    build = Path('build-rv32i')
    result = subprocess.run(['make', '--no-print-directory', 'rv32i', 'rv32i-reference'],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('Comparison build failed: ' + result.stdout + result.stderr)
    info = subprocess.check_output(['make', '-s', '--no-print-directory',
                                    'rv32i-reference-info'], text=True, timeout=15)
    compiler = json.loads(info)
    compiler['version'] = subprocess.check_output([compiler['compiler'], '--version'],
                                                  text=True, timeout=15).splitlines()[0]
    identity = ripes_identity('/usr/bin/ripes')
    root = build / 'comparison'
    root.mkdir(exist_ok=True)
    symbols = ('cube_permutation_turn', 'cube_orientation_turn', 'cube_permutation_distance',
               'cube_orientation_distance', 'cube_permutation_subset', 'cube_mixed_distance')
    images = {name: debug_image(build / f'{name}.elf') for name in ('smoke', 'reference')}
    for symbol in symbols:
        if object_data(images['smoke'], symbol) != object_data(images['reference'], symbol):
            raise ValueError('GCC and hand images have different table payloads: ' + symbol)
    cases = ('12345671111111', '25314672313211', '21345671111111')
    evidence = {'identity': identity, 'compiler': compiler,
                'convention': 'Full parse/rank/search/replay/output entry; renderer absent; linked .text bytes',
                'table_payloads_equal': True, 'images': {}, 'cases': []}
    for name in images:
        elf = build / f'{name}.elf'
        evidence['images'][name] = {'audit': audit(elf),
                                  'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest()}
    for state in cases:
        row = {'input': state}
        for name, image in images.items():
            destination = root / f'{name}-{state}.elf'
            for suffix in ('.elf', '.debug.elf'):
                data = bytearray((build / (name + suffix)).read_bytes())
                at = input_offset(data, image[2]['cube_input'][0])
                data[at:at + 15] = state.encode() + b'\0'
                destination.with_suffix(suffix).write_bytes(data)
            measured = check(identity['ripes_path'], str(destination), 'RV32_ISS')
            row[name] = {'iret': measured['report']['# instructions retired'],
                         'evidence': measured}
        evidence['cases'].append(row)
    (root / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'compiler': compiler, 'sizes': {n: v['audit']['sections']['.text']
                     for n, v in evidence['images'].items()}, 'cases': [
                         {'input': r['input'], 'hand_iret': r['smoke']['iret'],
                          'gcc_iret': r['reference']['iret']} for r in evidence['cases']]}, indent=2))


if __name__ == '__main__':
    try:
        run()
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
