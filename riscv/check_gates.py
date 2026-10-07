"""Resumable host H1-H4 evidence and the complete RV32_ISS hardest gate.

Run under guard-run and a finite outer timeout. Each invocation stops starting
new cases after its wall budget; PARTIAL is never reported as a passed gate.
Only the 15-byte input object is patched between target queries. Search, replay,
output and tables remain the same linked image for every measured state.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from calibrate import ripes_identity
from check_smoke import check, debug_image, object_data

DOMAIN = 3674160
HARDEST = 2644
LIMIT = 50000000
HISTOGRAM = [1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644]
ASSEMBLY = ('entry.S', 'parse.S', 'rank.S', 'heuristic.S', 'move.S',
            'search.S', 'replay.S', 'output.S', 'link.ld')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def native(command, directory, name, timeout=120):
    started = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    (directory / f'{name}.stdout.log').write_text(result.stdout)
    (directory / f'{name}.stderr.log').write_text(result.stderr)
    evidence = {'command': command, 'status': result.returncode,
                'elapsed_seconds': time.perf_counter() - started,
                'stdout': result.stdout, 'stderr': result.stderr}
    if result.returncode:
        save(directory / f'{name}.failure.json', evidence)
        raise ValueError(f'Native command failed: {command}: {result.stderr}')
    return evidence


def snapshot(paths, directory):
    directory.mkdir(exist_ok=True)
    hashes = {}
    for path in paths:
        data = path.read_bytes()
        value = digest(data)
        hashes[str(path)] = value
        (directory / f'{value}-{path.name}').write_bytes(data)
    return hashes


def histogram(text, prefix):
    rows = re.findall(re.escape(prefix) + r' (\d+): (\d+) states', text)
    if [int(d) for d, _ in rows] != list(range(12)):
        raise ValueError('Missing or duplicated distance histogram bins')
    return [int(n) for _, n in rows]


def host(args):
    started = time.perf_counter()
    identity = digest(Path('solver.c').read_bytes()) + '-' + digest(Path('solver').read_bytes())[:16]
    root = Path(args.build) / 'gates' / 'host' / identity
    root.mkdir(parents=True, exist_ok=True)
    snapshot((Path('solver.c'), Path(__file__)), root / 'sources')
    if not (root / 'H1-H2-H4.json').exists():
        result = native(['./solver', '--self-test'], root, 'H1-H2-H4')
        if result['stdout'] != '3674160 states; diameter 11\n' or \
                'P/Q + mixed heuristic: 3674160 states checked' not in result['stderr'] or \
                'byte/packed equality and abstract distances checked' not in result['stderr']:
            raise ValueError('Host self-test did not report complete H1/H4 coverage')
        tables = re.findall(r'^H2 (.+)$', result['stderr'], re.M)
        if len(tables) != 7:
            raise ValueError('H2 did not report every dependent table')
        result['tables'] = tables
        save(root / 'H1-H2-H4.json', result)
    first = 0
    records = []
    while first < DOMAIN:
        count = min(args.chunk, DOMAIN - first)
        path = root / f'H3-{first}-{first + count}.json'
        if path.exists():
            result = json.loads(path.read_text())
        else:
            if time.perf_counter() - started >= args.wall_seconds:
                break
            result = native(['./solver', '--verify-range', str(first), str(count)], root,
                            f'H3-{first}-{first + count}')
            marker = f'IDA* rank range [{first},{first + count}): {count} states checked'
            if result['stdout'] != 'rank range passed\n' or marker not in result['stderr']:
                raise ValueError('H3 did not verify the requested complete rank range')
            rows = re.findall(r'^distance (\d+): (\d+) states$', result['stderr'], re.M)
            if [int(d) for d, _ in rows] != list(range(12)) or sum(int(n) for _, n in rows) != count:
                raise ValueError('H3 range histogram does not cover the full range')
            result.update({'first': first, 'count': count, 'histogram': [int(n) for _, n in rows]})
            save(path, result)
            print(f'H3 [{first},{first + count}) passed in {result["elapsed_seconds"]:.3f}s', flush=True)
        if result['first'] != first or result['count'] != count or result['status'] != 0:
            raise ValueError('H3 resume record differs from the requested range')
        records.append(result)
        first += count
    totals = [sum(r['histogram'][i] for r in records) for i in range(12)]
    complete = first == DOMAIN
    if complete and totals != HISTOGRAM:
        raise ValueError('H3 complete histogram differs from the exact HTM distribution')
    summary = {'source_sha256': digest(Path('solver.c').read_bytes()),
               'solver_sha256': digest(Path('solver').read_bytes()),
               'H1_H2_H4': 'PASS', 'H3': 'PASS' if complete else 'PARTIAL',
               'covered_rank_interval': [0, first], 'domain': DOMAIN,
               'histogram': totals, 'ranges': len(records),
               'H3_wall_seconds': sum(r['elapsed_seconds'] for r in records)}
    save(root / 'summary.json', summary)
    print(json.dumps({'root': str(root), **summary}, indent=2))


def corpus(data):
    cases = []
    previous = -1
    for line in data.decode('ascii').splitlines():
        index, rank, state, distance = line.split()
        index, rank, distance = int(index), int(rank), int(distance)
        if index != len(cases) or rank <= previous or not 0 <= rank < DOMAIN or distance != 11:
            raise ValueError('Hardest corpus is not a unique ascending exact-distance list')
        if len(state) != 14:
            raise ValueError('Hardest input is not fourteen characters')
        p = [ord(c) - 49 for c in state[:7]]
        o = [ord(c) - 49 for c in state[7:]]
        if sorted(p) != list(range(7)) or any(v not in range(3) for v in o) or sum(o) % 3:
            raise ValueError('Hardest corpus contains an invalid cube')
        pr = qr = 0
        for i, value in enumerate(p):
            pr = pr * (7 - i) + sum(v < value for v in p[i + 1:])
        for value in o[:6]:
            qr = 3 * qr + value
        if pr * 729 + qr != rank:
            raise ValueError('Hardest corpus input differs from its rank')
        previous = rank
        cases.append({'index': index, 'rank': rank, 'input': state, 'distance': distance})
    if len(cases) != HARDEST or not any(c['input'] == '21345671111111' for c in cases):
        raise ValueError('Hardest corpus is incomplete or omits the comparison vector')
    return cases


def input_offset(data, address):
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    for i in range(h[12]):
        row = struct.unpack_from('<IIIIIIIIII', data, h[6] + i * h[11])
        if row[1] == 1 and row[2] & 2 and row[3] <= address and address + 15 <= row[3] + row[5]:
            return row[4] + address - row[3]
    raise ValueError('cube_input is not wholly inside an allocated PROGBITS section')


def prepare(args):
    identity = ripes_identity(args.ripes)
    parent = Path(args.build) / 'gates'
    template = parent / 'template'
    template.mkdir(parents=True, exist_ok=True)
    source = template / 'input.S'
    source.write_text('.section .rodata.cube_input, "a", @progbits\n'
                      '.globl cube_input\n.type cube_input, @object\n'
                      'cube_input:\n.asciz "12345671111111"\n.size cube_input, .-cube_input\n')
    build = subprocess.run(['make', '--no-print-directory', 'rv32i', f'RV_BUILD={template}',
                            f'RV_INPUT={source}'], capture_output=True, text=True, timeout=60)
    if build.returncode:
        raise ValueError('Gate template build failed: ' + build.stdout + build.stderr)
    exported = native(['./solver', '--emit-hardest-cases'], template, 'hardest-corpus')
    if histogram(exported['stderr'], 'exact BFS distance') != HISTOGRAM:
        raise ValueError('Exact corpus enumeration has an incorrect domain histogram')
    data = exported['stdout'].encode('ascii')
    corpus(data)
    elf = template / 'smoke.elf'
    image = debug_image(elf)
    if object_data(image, 'cube_input') != b'12345671111111\0':
        raise ValueError('Gate template cube_input is not a fixed fifteen-byte object')
    paths = [Path('solver.c'), Path('Makefile'), Path(__file__), Path('riscv/check_smoke.py'),
             Path('riscv/audit_elf.py'), Path('riscv/calibrate.py')]
    paths += [Path('riscv') / name for name in ASSEMBLY]
    hashes = {str(p): digest(p.read_bytes()) for p in paths}
    manifest = {'identity': identity, 'processor': 'RV32_ISS', 'budget': LIMIT,
                'cases': HARDEST, 'corpus_sha256': digest(data), 'sources': hashes,
                'host_solver_sha256': digest(Path('solver').read_bytes()),
                'template_sha256': digest(elf.read_bytes()),
                'debug_sha256': digest(elf.with_suffix('.debug.elf').read_bytes()),
                'audit': audit(elf), 'input_address': image[2]['cube_input'][0]}
    run_id = digest(json.dumps(manifest, sort_keys=True).encode())[:20]
    root = parent / (identity['ripes_build_id'] + '-' + run_id)
    root.mkdir(exist_ok=True)
    for suffix in ('.elf', '.debug.elf'):
        (root / ('template' + suffix)).write_bytes(elf.with_suffix(suffix).read_bytes())
    (root / 'hardest.txt').write_bytes(data)
    snapshot(paths, root / 'sources')
    (root / 'host-solver').write_bytes(Path('solver').read_bytes())
    (root / 'host-solver').chmod(0o755)
    save(root / 'corpus-evidence.json', exported)
    save(root / 'manifest.json', manifest)
    save(parent / 'active.json', {'root': str(root)})
    print(f'Prepared all {HARDEST} exact distance-11 inputs: {root}')


def target(args):
    started = time.perf_counter()
    root = Path(args.run) if args.run else Path(json.loads(
        (Path(args.build) / 'gates/active.json').read_text())['root'])
    manifest = json.loads((root / 'manifest.json').read_text())
    if ripes_identity(args.ripes) != manifest['identity']:
        raise ValueError('Selected Ripes executable differs from the pinned run')
    for name, value in manifest['sources'].items():
        archived = root / 'sources' / (value + '-' + Path(name).name)
        if digest(archived.read_bytes()) != value:
            raise ValueError('An archived source changed after preparation')
    native_solver = root / 'host-solver'
    if not native_solver.exists():
        data = Path('solver').read_bytes()
        if digest(data) != manifest['host_solver_sha256']:
            raise ValueError('Original native solver is unavailable; do not mix new oracle code into this run')
        native_solver.write_bytes(data)
        native_solver.chmod(0o755)
    if digest(native_solver.read_bytes()) != manifest['host_solver_sha256']:
        raise ValueError('Pinned native solver changed after preparation')
    raw = (root / 'hardest.txt').read_bytes()
    if digest(raw) != manifest['corpus_sha256']:
        raise ValueError('Hardest corpus changed after preparation')
    cases = corpus(raw)
    templates = {}
    offsets = {}
    for suffix, key in (('.elf', 'template_sha256'), ('.debug.elf', 'debug_sha256')):
        data = (root / ('template' + suffix)).read_bytes()
        if digest(data) != manifest[key]:
            raise ValueError('Immutable target template changed')
        templates[suffix] = data
        offsets[suffix] = input_offset(data, manifest['input_address'])
    directory = root / 'records'
    directory.mkdir(exist_ok=True)
    first, end = args.first, min(HARDEST, args.first + args.count)
    if not 0 <= first < end:
        raise ValueError('Hardest case interval is outside [0,2644)')
    for case in cases[first:end]:
        path = directory / f'{case["index"]:04d}.json'
        if path.exists():
            continue
        if time.perf_counter() - started >= args.wall_seconds:
            break
        before = time.perf_counter()
        for suffix, template in templates.items():
            data = bytearray(template)
            at = offsets[suffix]
            data[at:at + 15] = case['input'].encode('ascii') + b'\0'
            (root / ('query' + suffix)).write_bytes(data)
        evidence = check(manifest['identity']['ripes_path'], str(root / 'query.elf'),
                         'RV32_ISS', args.sim_timeout, quiet=True, solver=native_solver)
        if evidence['expected']['length'] != 11 or \
                evidence['expected']['p'] * 729 + evidence['expected']['q'] != case['rank']:
            raise ValueError('Target/native length or coordinates differ from the exact BFS corpus')
        instructions = evidence['report']['# instructions retired']
        record = {**case, 'elapsed_seconds': time.perf_counter() - before,
                  'iret': instructions, 'budget_passed': instructions <= LIMIT,
                  'validator_sha256': {str(p): digest(p.read_bytes()) for p in
                                       (Path(__file__), Path('riscv/check_smoke.py'))},
                  'elf_sha256': digest((root / 'query.elf').read_bytes()), **evidence}
        save(path, record)
        if case['index'] % 32 == 0 or instructions > LIMIT:
            print(f'hardest {case["index"]}/{HARDEST}: rank {case["rank"]}, '
                  f'iret {instructions}, {"PASS" if instructions <= LIMIT else "OVER BUDGET"}', flush=True)
    records = []
    for case in cases:
        path = directory / f'{case["index"]:04d}.json'
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        if any(record[key] != case[key] for key in case) or record['expected']['length'] != 11 or \
                record['iret'] != record['report']['# instructions retired'] or \
                record['budget_passed'] != (record['iret'] <= LIMIT):
            raise ValueError('Resume record is inconsistent with the pinned corpus or telemetry')
        records.append(record)
    complete = len(records) == HARDEST
    failures = [r['index'] for r in records if not r['budget_passed']]
    worst = max(records, key=lambda r: r['iret']) if records else None
    comparison = next((r for r in records if r['input'] == '21345671111111'), None)
    summary = {'root': str(root), 'identity': manifest['identity'], 'processor': 'RV32_ISS',
               'total': HARDEST, 'measured': len(records), 'complete': complete,
               'gate': ('FAIL' if failures else 'PASS') if complete else 'PARTIAL',
               'over_budget': failures, 'over_budget_count': len(failures), 'audit': manifest['audit'],
               'worst': {k: worst[k] for k in ('index', 'rank', 'input', 'iret')} if worst else None,
               'comparison_vector': {k: comparison[k] for k in ('index', 'rank', 'input', 'iret')}
                                    if comparison else None,
               'measurement_wall_seconds': sum(r['elapsed_seconds'] for r in records)}
    save(root / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'over_budget'}, indent=2))
    if complete and failures:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('host', 'prepare', 'target'))
    parser.add_argument('--build', default='build-rv32i')
    parser.add_argument('--ripes', default='/usr/bin/ripes')
    parser.add_argument('--run')
    parser.add_argument('--wall-seconds', type=float, default=80)
    parser.add_argument('--sim-timeout', type=int, default=30000)
    parser.add_argument('--chunk', type=int, default=65536)
    parser.add_argument('--first', type=int, default=0)
    parser.add_argument('--count', type=int, default=HARDEST)
    try:
        args = parser.parse_args()
        if args.wall_seconds <= 0 or args.sim_timeout <= 0 or not 0 < args.chunk <= DOMAIN or args.count <= 0:
            raise ValueError('All budgets and counts must be positive and bounded')
        {'host': host, 'prepare': prepare, 'target': target}[args.phase](args)
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
