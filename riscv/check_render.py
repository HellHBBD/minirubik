"""Run the actual renderer in Ripes with RAM replacing the absent CLI device.

Every pixel of every actual solution frame is checked on target against an
independent integer 3-D facelet rotation model. PNGs are previews of these
verified words, not screenshots of a running GUI LED peripheral.
"""
import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
from audit_elf import audit
from calibrate import ripes_identity
from check_smoke import MOVE_NAMES, SOURCES, TWISTS, check
from cube_geometry import facelets_from_cubies, pixels, turn_facelets


def cubie_move(state, move):
    p, o = list(state[:7]), list(state[7:])
    face, turns = divmod(move, 3)
    for _ in range(turns + 1):
        p = [p[i] for i in SOURCES[face]]
        o = [(o[i] + t) % 3 for i, t in zip(SOURCES[face], TWISTS[face])]
    return p + o


def png(path, words, scale=10):
    width, height = 35 * scale, 25 * scale
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            value = words[(y // scale) * 35 + x // scale]
            # Grid denotes individual LEDs, not an additional cube-face gap.
            if x % scale == 0 or y % scale == 0:
                value = 0
            rows.extend(((value >> 16) & 255, (value >> 8) & 255, value & 255))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
    path.write_bytes(data)


def run():
    build = Path('build-rv32i')
    root = build / 'render-tests'
    root.mkdir(exist_ok=True)
    identity = ripes_identity('/usr/bin/ripes')
    solved = list(range(7)) + [0] * 7
    solved_colors = [f for f in range(6) for _ in range(4)]
    # Check model compatibility before relying on it as fixture evidence.
    for move in range(9):
        assert facelets_from_cubies(cubie_move(solved, move)) == turn_facelets(solved_colors, move)
    inputs = ('12345671111111', '25314672313211', '21345671111111')
    records = []
    for text in inputs:
        native = subprocess.run(['./solver', text], capture_output=True, text=True, timeout=15)
        if native.returncode:
            raise ValueError('Native solver failed while preparing renderer checks')
        path = [MOVE_NAMES.index(name) for name in native.stdout.split()]
        state = [ord(c) - 49 for c in text]
        # Construct the initial frame geometrically via the inverse solution;
        # then compare it with the corner/orientation decoding independently.
        colors = list(solved_colors)
        scramble = [3 * (m // 3) + (2, 1, 0)[m % 3] for m in reversed(path)]
        reconstructed = list(solved)
        for move in scramble:
            colors = turn_facelets(colors, move)
            reconstructed = cubie_move(reconstructed, move)
        if reconstructed != state or facelets_from_cubies(state) != colors:
            raise ValueError('Cubie orientation convention differs from geometric facelets')
        frames = [pixels(colors)]
        for move in path:
            colors = turn_facelets(colors, move)
            frames.append(pixels(colors))
        if colors != solved_colors:
            raise ValueError('The actual native path does not solve the geometric cube')
        directory = root / text
        directory.mkdir(exist_ok=True)
        source = directory / 'input.S'
        source.write_text('.section .rodata.cube_input, "a", @progbits\n'
                          '.globl cube_input\n.type cube_input, @object\n'
                          f'cube_input:\n.asciz "{text}"\n.size cube_input, .-cube_input\n')
        fixture = directory / 'render-fixtures.S'
        lines = ['.section .rodata.render_expected, "a", @progbits', '.balign 4',
                 '.globl cube_render_expected_count', '.type cube_render_expected_count, @object',
                 'cube_render_expected_count:', f'.4byte {len(frames)}',
                 '.size cube_render_expected_count, .-cube_render_expected_count',
                 '.globl cube_render_expected', '.type cube_render_expected, @object', 'cube_render_expected:']
        for frame in frames:
            for start in range(0, len(frame), 16):
                lines.append('.4byte ' + ','.join(hex(v) for v in frame[start:start + 16]))
        lines.append('.size cube_render_expected, .-cube_render_expected')
        fixture.write_text('\n'.join(lines) + '\n')
        command = ['make', '--no-print-directory', 'rv32i', f'RV_BUILD={directory}',
                   f'RV_INPUT={source}', 'RV_RENDER=1', 'RV_RENDER_TEST=1', 'RV_RENDER_DELAY=0',
                   f'RV_RENDER_FIXTURE={fixture}']
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError('Renderer build failed: ' + result.stdout + result.stderr)
        elf = directory / 'smoke.elf'
        evidence = check(identity['ripes_path'], str(elf), 'RV32_ISS')
        regs = evidence['report']['registers']
        if regs['x3'] != len(frames) or regs['x4'] != 0 or evidence['path'] != path:
            raise ValueError('Renderer did not verify every frame of the actual solution')
        png(directory / 'initial.png', frames[0])
        png(directory / 'solved.png', frames[-1])
        record = {'input': text, 'frames': len(frames), 'pixel_words_checked': len(frames) * 875,
                  'geometry_model': 'Independent integer rotations of positions and face normals',
                  'image_provenance': 'Preview of runtime-verified RAM framebuffer; not GUI screenshot',
                  'command': command, 'audit': audit(elf), 'evidence': evidence,
                  'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()}
        records.append(record)
        (root / 'summary.json').write_text(json.dumps({'identity': identity, 'records': records,
                                                     'gui_visual_check': 'PENDING'}, indent=2) + '\n')
        print(f'Renderer passed: {text}, {len(frames)} actual-path frames, '
              f'{len(frames) * 875} RGB words and both framebuffer guards', flush=True)


if __name__ == '__main__':
    try:
        run()
    except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
