"""Freeze three renderer-on ELF cases and their frame-ready addresses.

Following the completed reference capture workflow, preparation is recorded
separately from runtime screenshots. Refuse to overwrite a capture session.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from calibrate import ripes_identity
from check_smoke import debug_image


def run(args):
    root = Path(args.output)
    if root.exists() and any(root.iterdir()):
        raise ValueError('GUI capture directory is not empty; choose a new --output session')
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for name, text in (('solved', '12345671111111'), ('one-move', '25314672313211'),
                       ('distance-11', '21345671111111')):
        directory = root / name
        directory.mkdir()
        source = directory / 'input.S'
        source.write_text('.section .rodata.cube_input, "a", @progbits\n'
                          '.globl cube_input\n.type cube_input, @object\n'
                          f'cube_input:\n.asciz "{text}"\n.size cube_input, .-cube_input\n')
        command = ['make', '--no-print-directory', 'rv32i', f'RV_BUILD={directory}',
                   f'RV_INPUT={source}', 'RV_RENDER=1', 'RV_RENDER_TEST=0']
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError('GUI case build failed: ' + result.stdout + result.stderr)
        elf = directory / 'smoke.elf'
        native = subprocess.run(['./solver', text], capture_output=True, text=True, timeout=15)
        if native.returncode:
            raise ValueError('Native path oracle failed')
        image = debug_image(elf)
        records.append({'name': name, 'input': text, 'elf': str(elf),
                        'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(),
                        'frame_ready_address': image[2]['cube_frame_ready'][0],
                        'frame_ready_hex': hex(image[2]['cube_frame_ready'][0]),
                        'expected_frames': len(native.stdout.split()) + 1,
                        'expected_path': native.stdout.strip(), 'audit': audit(elf),
                        'command': command})
    manifest = {'identity': ripes_identity('/usr/bin/ripes'), 'cases': records,
                'gui_status': 'PREPARED; reference screenshots reviewed separately',
                'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  (Path('riscv/render.S'), Path('riscv/cube_geometry.py'),
                                   Path('riscv/led_symbols.inc'), Path('riscv/entry.S'), Path('riscv/replay.S'))},
                'console_timing': 'Current entry prints the complete path after successful replay; '
                                  'reference move-prefix screenshots use another output timing'}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(root), 'cases': records}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='build-rv32i/gui-evidence')
    try:
        run(parser.parse_args())
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
