"""Verify every retained hardest record and export compact durable evidence."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from calibrate import ripes_identity
from check_gates import HARDEST, LIMIT, corpus, input_offset
from check_smoke import MOVE_NAMES, debug_image, fingerprint, replay


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args):
    root = Path(json.loads(Path('build-rv32i/gates/active.json').read_text())['root'])
    manifest = json.loads((root / 'manifest.json').read_text())
    summary = json.loads((root / 'summary.json').read_text())
    if ripes_identity('/usr/bin/ripes') != manifest['identity']:
        raise ValueError('Simulator identity changed')
    raw = (root / 'hardest.txt').read_bytes()
    if sha(raw) != manifest['corpus_sha256']:
        raise ValueError('Corpus changed')
    cases = corpus(raw)
    template = (root / 'template.elf').read_bytes()
    if sha(template) != manifest['template_sha256'] or Path('build-rv32i/smoke.elf').read_bytes() != template:
        raise ValueError('The final CLI image differs from the measured subject')
    if sha((root / 'host-solver').read_bytes()) != manifest['host_solver_sha256']:
        raise ValueError('Pinned native oracle changed')
    offset = input_offset(template, manifest['input_address'])
    stack_top = debug_image(root / 'template.elf')[2]['__stack_top'][0]
    rows = []
    for case in cases:
        data = (root / 'records' / f'{case["index"]:04d}.json').read_bytes()
        record = json.loads(data)
        if any(record[k] != case[k] for k in case):
            raise ValueError('Record differs from the exact corpus')
        report, expected = record['report'], record['expected']
        regs = report['registers']
        path = record['path']
        encoded = [(regs['x23'] >> (4 * i)) & 15 for i in range(8)]
        encoded += [(regs['x24'] >> (4 * i)) & 15 for i in range(3)]
        state = bytes(ord(c) - 49 for c in case['input'])
        if path != encoded or not replay(state, path) or expected['length'] != 11 or regs['x22'] != 11:
            raise ValueError('Record path/length/replay failed')
        if regs['x8'] != 0 or regs['x10'] != 0 or regs['x25'] != 0 or regs['x26'] != 0 or regs['x27'] != 11:
            raise ValueError('Guest validation or target replay failed')
        if regs['x2'] != stack_top or regs['x9'] != fingerprint(state[:7], 3) or \
                regs['x18'] != fingerprint(state[7:], 2) or regs['x21'] != expected['h']:
            raise ValueError('Parser fingerprints, heuristic or stack pointer failed')
        if regs['x19'] * 729 + regs['x20'] != case['rank'] or \
                expected['p'] != regs['x19'] or expected['q'] != regs['x20']:
            raise ValueError('Coordinates differ from the exact rank')
        if report['runinfo']['processor'] != 'RV32_ISS' or report['runinfo']['ISA extensions'] != []:
            raise ValueError('Record processor/ISA differs from the pinned gate')
        output = ' '.join(MOVE_NAMES[m] for m in path) + '\n'
        if record['guest_output'] != output:
            raise ValueError('Move output differs from the returned path')
        image = bytearray(template)
        image[offset:offset + 15] = case['input'].encode() + b'\0'
        if sha(image) != record['elf_sha256']:
            raise ValueError('Record is not an input-only variation of the measured image')
        count = report['# instructions retired']
        if count != record['iret'] or not 0 < count <= LIMIT or not record['budget_passed']:
            raise ValueError('Instruction budget failed')
        rows.append({**case, 'iret': count, 'path': path,
                     'elf_sha256': record['elf_sha256'], 'raw_record_sha256': sha(data),
                     'elapsed_seconds': record['elapsed_seconds']})
    if len(rows) != HARDEST or summary['gate'] != 'PASS' or not summary['complete']:
        raise ValueError('Full-domain completion is not established')
    maximum = max(rows, key=lambda r: r['iret'])
    minimum = min(rows, key=lambda r: r['iret'])
    comparison = next(r for r in rows if r['input'] == '21345671111111')
    if maximum['iret'] != summary['worst']['iret'] or comparison['iret'] != summary['comparison_vector']['iret']:
        raise ValueError('Summary differs from verified raw records')
    result = {'gate': 'PASS', 'domain': 'all 2644 exact HTM distance-11 states',
              'count': HARDEST, 'limit': LIMIT, 'over_budget': 0,
              'identity': manifest['identity'], 'renderer': 'compiled out',
              'convention': 'full parse/rank/search/replay/output --iret; linked .text bytes',
              'target_template_sha256': manifest['template_sha256'],
              'current_cli_byte_identical': True, 'corpus_sha256': manifest['corpus_sha256'],
              'pinned_native_sha256': manifest['host_solver_sha256'],
              'measured_source_sha256': manifest['sources'], 'audit': manifest['audit'],
              'maximum': maximum, 'minimum': minimum, 'comparison': comparison,
              'budget_margin_percent': 100 * (LIMIT - maximum['iret']) / LIMIT,
              'measurement_wall_seconds': sum(r['elapsed_seconds'] for r in rows),
              'raw_evidence_root': str(root), 'records': rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'measured_source_sha256')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='measurements/rv32i-final.json')
    try:
        run(parser.parse_args())
    except (ValueError, KeyError) as error:
        raise SystemExit(str(error))
