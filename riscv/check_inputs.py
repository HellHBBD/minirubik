"""Exercise the handwritten input parser against the native C parse oracle."""

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
from check_smoke import check


def cases():
    unique = {}

    def add(label, data):
        if isinstance(data, str):
            data = data.encode('ascii')
        unique.setdefault(data, []).append(label)

    solved = b'12345671111111'
    vectors = ('12345671111111', '62345713133111', '24316572122213',
               '25713642221111', '24513763133333', '43752611332133',
               '25416373331111', '21345671111111')
    for i, vector in enumerate(vectors):
        add(f'vector-{i}', vector)
    add('one-R-turn', '25314672313211')
    add('reverse-permutation', '76543211111111')
    rng = random.Random(602)
    for i in range(12):
        p = list(range(7))
        rng.shuffle(p)
        o = [rng.randrange(3) for _ in range(6)]
        o.append((-sum(o)) % 3)
        add(f'random-valid-{i}', bytes(v + 49 for v in p + o))
    for total in range(15):
        remaining = total
        o = []
        for _ in range(7):
            digit = min(2, remaining)
            o.append(digit)
            remaining -= digit
        add(f'orientation-sum-{total}', b'1234567' + bytes(v + 49 for v in o))
    for length in range(14):
        add(f'short-{length}', solved[:length])
    for tail in (b'1', b'123456', b'x'):
        add(f'long-{tail.decode()}', solved + tail)
    for i in range(7):
        bad = bytearray(solved)
        bad[i] = solved[(i + 1) % 7]
        add(f'duplicate-position-{i}', bytes(bad))
        for value in (48, 56):
            bad = bytearray(solved)
            bad[i] = value
            add(f'permutation-range-{i}-{value}', bytes(bad))
        for value in (48, 52):
            bad = bytearray(solved)
            bad[i + 7] = value
            add(f'orientation-range-{i}-{value}', bytes(bad))
    for i in range(14):
        for value in (128, 255):
            bad = bytearray(solved)
            bad[i] = value
            add(f'high-byte-{i}-{value}', bytes(bad))
    add('nondigit-permutation', b'1a345671111111')
    add('nondigit-orientation', b'1234567111111a')
    add('reserved-cli-name-self-test', b'--self-test')
    add('reserved-cli-name-emit-tables', b'--emit-tables')
    add('early-NUL-with-tail', solved[:4] + b'\0' + solved[5:])
    add('NUL-terminator-with-unused-tail', solved + b'\0unused')
    return [(labels, data) for data, labels in unique.items()]


def build_input(build, source):
    command = ['make', '--no-print-directory', 'rv32i',
               f'RV_BUILD={build}', f'RV_INPUT={source}']
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError('Input build failed: ' + result.stdout + result.stderr)


def run(args):
    suite = cases()
    if args.list:
        print(f'{len(suite)} unique input cases')
        return
    first = args.first
    count = len(suite) - first if args.count is None else args.count
    if first < 0 or count <= 0 or first + count > len(suite):
        raise ValueError('Input-case range is outside the suite')
    build = Path(args.build)
    directory = build / 'input-cases'
    directory.mkdir(exist_ok=True)
    records = []
    output = build / f'input-check-{first}-{first + count}.json'
    try:
        for index in range(first, first + count):
            labels, data = suite[index]
            source = directory / f'case-{index}.S'
            values = ','.join(str(v) for v in data + b'\0')
            source.write_text('.section .rodata.cube_input, "a", @progbits\n'
                              '.globl cube_input\n.type cube_input, @object\n'
                              'cube_input:\n    .byte ' + values + '\n'
                              '.size cube_input, .-cube_input\n')
            before = time.perf_counter()
            build_input(build, source)
            evidence = check(args.ripes, str(build / 'smoke.elf'), args.processor)
            records.append({'index': index, 'labels': labels,
                            'object_input_hex': data.hex(),
                            'elapsed_seconds': time.perf_counter() - before,
                            **evidence})
            output.write_text(json.dumps({'suite_size': len(suite),
                                         'first': first, 'count': count,
                                         'records': records}, indent=2) + '\n')
            print(f'input case {index}: {labels[0]} passed', flush=True)
    finally:
        # Each case uses a generated object; never edit the user's input.S.
        build_input(build, Path(args.input))
        check(args.ripes, str(build / 'smoke.elf'), args.processor)
    valid = sum(r['expected']['status'] == 0 for r in records)
    print(f'INPUT RANGE [{first},{first + count}) PASSED: '
          f'{valid} valid, {count - valid} invalid; '
          f'{sum(r["elapsed_seconds"] for r in records):.3f}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ripes', default='/usr/bin/ripes')
    parser.add_argument('--build', default='build-rv32i')
    parser.add_argument('--processor', default='RV32_SS')
    parser.add_argument('--input', default='riscv/input.S')
    parser.add_argument('--first', type=int, default=0)
    parser.add_argument('--count', type=int)
    parser.add_argument('--list', action='store_true')
    try:
        run(parser.parse_args())
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
