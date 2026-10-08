"""Accept any valid shortest path, rather than one BFS tie-breaking string."""
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'riscv'))
from check_smoke import MOVE_NAMES, replay


def path(output):
    text = output.decode('ascii')
    names = text.split()
    if text != ' '.join(names) + '\n':
        raise ValueError('Noncanonical solution whitespace')
    return [MOVE_NAMES.index(name) for name in names]


def run():
    count = 0
    for line in Path('tests/solutions.txt').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        text, expected = line.split('|')
        state = bytes(ord(c) - 49 for c in text)
        golden = path((expected + '\n').encode())
        if not replay(state, golden):
            raise ValueError('Golden path does not solve its input: ' + text)
        for binary in ('./solver', './mini'):
            result = subprocess.run([binary, text], capture_output=True, timeout=15)
            if result.returncode:
                raise ValueError(f'{binary} {text}: status {result.returncode}')
            actual = path(result.stdout)
            if len(actual) != len(golden) or not replay(state, actual):
                raise ValueError(f'{binary} {text}: path is invalid or not optimal')
        count += 1
    print(f'{count} solution vectors passed by solver and mini: exact length and independent cubie replay')


if __name__ == '__main__':
    try:
        run()
    except (ValueError, UnicodeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
