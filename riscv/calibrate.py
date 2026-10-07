"""Measure sparse-memory amplification and model execution rate on Linux.

Each observation launches a fresh Ripes process, serially. Linux wait4 gives
the peak RSS of the finite timeout wrapper and its Ripes child, excluding this
Python driver and compiler. Rate uses Ripes model time, not process startup.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from check_smoke import debug_image, object_data

BASELINE_BYTES = 18405414


def ripes_identity(executable):
    resolved = shutil.which(os.path.expanduser(executable))
    if resolved is None:
        raise ValueError(f'Ripes executable not found: {executable}')
    path = str(Path(resolved).resolve())
    notes = subprocess.check_output(['readelf', '-n', path], text=True, timeout=15)
    match = re.search(r'Build ID: ([0-9a-f]+)', notes)
    if match is None:
        raise ValueError(f'Ripes executable has no GNU Build ID: {path}')
    package = None
    origin = 'package manager unavailable'
    pacman = shutil.which('pacman')
    if pacman is not None:
        owner = subprocess.run([pacman, '-Qoq', '--', path], capture_output=True,
                               text=True, timeout=15)
        if owner.returncode == 0:
            names = owner.stdout.splitlines()
            if len(names) != 1:
                raise ValueError('Ripes executable has an ambiguous package owner')
            package = subprocess.check_output([pacman, '-Q', '--', names[0]],
                                              text=True, timeout=15).strip()
            origin = 'package-owned executable'
        elif owner.returncode == 1:
            origin = 'not owned by pacman'
        else:
            raise ValueError('Ripes package-owner query failed: ' + owner.stderr)
    return {'ripes_requested': executable, 'ripes_path': path,
            'ripes_package': package, 'ripes_origin': origin,
            'ripes_build_id': match.group(1)}


def archive_sources(root):
    directory = root / 'sources'
    directory.mkdir(exist_ok=True)
    hashes, archives = {}, {}
    for path in (Path('riscv/calibration.S'), Path(__file__)):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        destination = directory / f'{digest}-{path.name}'
        destination.write_bytes(data)
        hashes[str(path)] = digest
        archives[str(path)] = str(destination)
    return hashes, archives


def build_case(root, size, passes):
    directory = root / f'case-{size}-{passes}'
    command = ['make', '--no-print-directory', 'rv32i-calibration',
               f'RV_BUILD={directory}', f'RV_CAL_BYTES={size}',
               f'RV_CAL_PASSES={passes}']
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError('Calibration build failed: ' + result.stdout + result.stderr)
    elf = directory / 'calibration.elf'
    image = debug_image(elf)
    if struct.unpack('<II', object_data(image, 'cube_calibration_parameters')) != (size, passes):
        raise ValueError('Calibration ELF has stale parameters')
    return elf, image[2]['__stack_top'][0], audit(elf)


def measure(args, elf, stack, size, passes, processor, repeat, linked):
    name = f'{processor}-{repeat}'
    stdout = elf.parent / f'{name}.stdout.log'
    stderr = elf.parent / f'{name}.stderr.log'
    command = ['timeout', '--signal=TERM', '--kill-after=5s',
               f'{args.sim_timeout / 1000 + 15:g}s', args.ripes,
               '--mode', 'cli', '--src', str(elf), '-t', 'elf',
               '--proc', processor, '--timeout', str(args.sim_timeout),
               '--json', '--iret', '--regs', '--exectime', '--runinfo']
    started = time.perf_counter()
    with stdout.open('w') as out, stderr.open('w') as err:
        process = subprocess.Popen(command, stdout=out, stderr=err,
                                   env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
        _, status, usage = os.wait4(process.pid, 0)
        process.returncode = os.waitstatus_to_exitcode(status)
    elapsed = time.perf_counter() - started
    text, errors = stdout.read_text(), stderr.read_text()
    if process.returncode or 'ERROR:' in text + errors:
        raise ValueError(f'Calibration run failed ({process.returncode}): {text}{errors}')
    start = text.find('{')
    if start < 0 or text[:start] != '\nProgram exited with code: 0\n':
        raise ValueError('Calibration guest did not exit successfully')
    report, _ = json.JSONDecoder().raw_decode(text[start:])
    expected = {'x8': 0, 'x10': 0, 'x9': size, 'x18': passes,
                'x19': size // 4, 'x20': 0x100000, 'x21': 0,
                'x22': size // 4 * passes, 'x24': 0x12345678,
                'x25': 0x100000 + size, 'x26': 0x12345678,
                'x27': 0x12345678, 'x2': stack}
    if any(report['registers'][reg] != value for reg, value in expected.items()):
        raise ValueError('Calibration did not finish all stores or preserve its boundaries')
    if report['runinfo']['processor'] != processor or report['runinfo']['ISA extensions'] != []:
        raise ValueError('Calibration processor or base ISA mismatch')
    # Four instructions per store, five per pass, fixed setup/check/exit.
    # Pinned ISS retires the post-exit self-loop; 5S does not.
    instructions = size * passes + 5 * passes + (23 if processor == 'RV32_ISS' else 22)
    if report['# instructions retired'] != instructions:
        raise ValueError('Calibration retired count differs from the loop operation count')
    milliseconds = report['execution time (ms)']
    if milliseconds <= 0 or usage.ru_maxrss <= 0:
        raise ValueError('Calibration time or peak RSS is not measurable')
    evidence = {'command': command, 'guest_bytes': size, 'passes': passes,
                'processor': processor, 'repeat': repeat,
                'ripes_identity': args.identity,
                'elf_sha256': hashlib.sha256(elf.read_bytes()).hexdigest(),
                'peak_rss_bytes': usage.ru_maxrss * 1024,
                'process_wall_seconds': elapsed,
                'model_instructions_per_second': instructions * 1000 / milliseconds,
                'child_user_seconds': usage.ru_utime, 'child_system_seconds': usage.ru_stime,
                'report': report, 'audit': linked, 'stdout': str(stdout), 'stderr': str(stderr)}
    (elf.parent / f'{name}.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'{processor} bytes={size} passes={passes} repeat={repeat}: '
          f'RSS={evidence["peak_rss_bytes"]}, model={milliseconds}ms, '
          f'iret={instructions}', flush=True)
    return evidence


def run(args):
    if args.repeats < 1 or args.repeats > 10 or args.sim_timeout <= 0:
        raise ValueError('Require 1..10 repeats and a positive simulation timeout')
    identity = ripes_identity(args.ripes)
    args.identity = identity
    args.ripes = identity['ripes_path']
    root = Path(args.build) / 'calibration' / identity['ripes_build_id']
    root.mkdir(parents=True, exist_ok=True)
    hashes, archives = archive_sources(root)
    records = []
    output = root / f'{args.phase}-summary.json'
    sizes = (65536, 1048576, 2097152, 4194304) if args.phase == 'memory' else (65536,)
    processors = ('RV32_ISS',) if args.phase == 'memory' else ('RV32_ISS', 'RV32_5S')
    passes = 1 if args.phase == 'memory' else 128
    summary = {'phase': args.phase, **identity,
               'rss_method': 'Linux wait4 peak RSS; fresh timeout/Ripes process per observation',
               'rate_method': 'Ripes --iret / --exectime; excludes startup/build/teardown',
               'source_sha256': hashes, 'source_archives': archives,
               'records': records}
    for size in sizes:
        elf, stack, linked = build_case(root, size, passes)
        for processor in processors:
            for repeat in range(args.repeats):
                records.append(measure(args, elf, stack, size, passes, processor, repeat, linked))
                output.write_text(json.dumps(summary, indent=2) + '\n')
    if args.phase == 'memory':
        medians = {size: statistics.median(r['peak_rss_bytes'] for r in records
                                          if r['guest_bytes'] == size) for size in sizes}
        control = sizes[0]
        slopes = {size: (medians[size] - medians[control]) / (size - control) for size in sizes[1:]}
        slope = slopes[sizes[-1]]
        if slope <= 0:
            raise ValueError('Sparse memory amplification was not measurable')
        summary.update({'median_rss_bytes': medians, 'control_relative_slopes': slopes,
                        'host_bytes_per_guest_byte': slope,
                        'baseline_guest_bytes': BASELINE_BYTES,
                        'projected_incremental_host_bytes': slope * BASELINE_BYTES,
                        'projected_process_peak_bytes': medians[control] + slope * (BASELINE_BYTES - control)})
    else:
        rates = {p: statistics.median(r['model_instructions_per_second'] for r in records
                                     if r['processor'] == p) for p in processors}
        summary.update({'median_instructions_per_second': rates,
                        'projected_1e9_instruction_seconds': {p: 1e9 / rate for p, rate in rates.items()}})
    output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('memory', 'rate'), required=True)
    parser.add_argument('--ripes', default='/usr/bin/ripes')
    parser.add_argument('--build', default='build-rv32i')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--sim-timeout', type=int, default=60000)
    try:
        run(parser.parse_args())
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
