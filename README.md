# minirubik

An optimal C99 and handwritten RV32I solver for the 2×2×2 Rubik’s Cube.
Factored coordinates, packed pattern databases, and non-recursive IDA* solve
every valid position in at most 11 half-turn-metric moves. Exhaustive BFS over
all 3,674,160 states provides an independent exact-distance validation oracle.

## Why a cube is a graph

Ernő Rubik created the original cube in 1974 to demonstrate how parts can move
independently without breaking the whole. A 3×3 cube has 20 moving pieces and
about 4.3 × 10¹⁹ reachable arrangements. The smaller 2×2 cube keeps the eight
corners and removes the edges and fixed centers. [Philo Li’s formula-free
introduction](https://philoli.com/zh/blog/solve-rubiks-cube-without-formulas/)
offers the key intuition: every turn is reversible, turns can be composed, and
their order matters—`R U` is generally not `U R`.

Human solvers use those facts to move a few pieces while restoring the rest;
the commutator `A B A⁻¹ B⁻¹` is the standard example. This program uses the
same group structure differently: it treats every valid arrangement as a node,
every face turn as an edge, and validates against an exhaustive graph search.
It does not use the article’s 3×3 Roux stages or a library of memorized algorithms.

The solver gives the eight corner positions the numbers `0–7`. The 2.5D
walkthrough below shows where those numbers are on the physical cube.

## How it works

1. Fix one corner to remove whole-cube rotations.
2. Rank the remaining corner permutation and six independent orientations into
   a dense integer.
3. Precompute coordinate transition tables and packed pattern databases for
   `R`, `B`, and `D`, including inverse and half turns.
4. Use non-recursive IDA* with an admissible heuristic to find an optimal
   solution, then replay it before printing the move tokens.

The host self-test also builds a full-state BFS oracle. The RV32I query image
contains only the compact query tables, not that full-state oracle.

## Build and run

Run all commands below from the repository root. Follow this workflow:
**host build → host tests → RV32I build → individual target checks → complete
validation gates → optional comparisons and visualization**.

### Environment and tools

| Task                              | Required tools                                                               |
| --------------------------------- | ---------------------------------------------------------------------------- |
| Host C                            | Make, a C99 compiler (`cc` by default), Python 3                             |
| Handwritten RV32I                 | `clang`, `ld.lld`, `llvm-objcopy`, Ripes                                     |
| GCC reference                     | The tools above, plus `riscv64-elf-gcc` targeting `-march=rv32i -mabi=ilp32` |
| Measurements and binary identity  | GNU `readelf`                                                                |
| Calibration driver dependency     | GNU `timeout` (used internally by the calibration driver)                    |

The recorded measurements use Ripes at commit `0b4c65b`. CLI checks use
`RV32_ISS`; pipeline tests also use `RV32_5S`. The Python drivers set
`QT_QPA_PLATFORM=offscreen`, so you do not need to open the GUI first.

`--wall-seconds` determines when the gate driver stops starting new cases;
it is not the timeout for an individual simulator run. Completed cases are
saved immediately.

### Quick start

```sh
make
./solver 21345671111111
make check
make rv32i
make rv32i-smoke
```

By default, `make` builds `solver` and `mini`. `solver` is the main C
implementation, with contracts, a self-test, table export, and diagnostics.
`mini` is a golfed BFS variant retained as a readability contrast; it has no
self-test and prints no diagnostics on failure. Both should return optimal
solutions, but their valid shortest paths may differ.

The host program takes a 14-digit argument and writes a line of move tokens to
stdout; a solved input produces an empty line. Exit status is 0 on success,
2 for invalid input, and 1 for internal or output failures.

`make rv32i` produces `build-rv32i/smoke.debug.elf`, retaining symbols, and
`build-rv32i/smoke.elf`, the stripped image loaded into Ripes. Despite its name,
`smoke.elf` contains the complete parse/rank/search/replay/output entry point.
`rv32i-smoke` runs the input currently compiled into the ELF and checks guest
status, coordinates, heuristic, optimal length, replay, and output. Keep the
matching `.debug.elf` alongside the `.elf`: the checker reads its input and
symbols.

### Build workflow and input configuration

```text
solver.c ── cc ──→ solver ── --emit-tables ──→ tables.S
                                                 ↓
                handwritten .S + input.S + tables.S
                                  ↓ clang
                                 *.o
                                  ↓ ld.lld + riscv/link.ld
                          smoke.debug.elf
                                  ↓ llvm-objcopy
                             smoke.elf
                                  ↓
                        Ripes + Python checker
```

The Makefile first exports query tables using the host `solver`, then assembles
the handwritten code and tables into RV32I objects, links them with
`riscv/link.ld`, and finally removes symbols and `.riscv.attributes`.
The GCC reference uses `riscv/reference.c` to include the target mode of the same
`solver.c`, together with reference tables and ABI bridges. The entry, replay,
and output code is shared.

**The RV32I input is `cube_input` compiled into the ELF, not a command-line
argument.** By default, the `.asciz` in [`riscv/input.S`](riscv/input.S) contains
the solved code `12345671111111`. To test another cube, edit this string and
rebuild, or provide a separate `.S` file with the same section and symbol
definitions and select it with `RV_INPUT=path/to/file`.
`input.o` is reassembled on every build; the checkers read the actual string
from the ELF.

### Makefile targets

Use the targets below with `make TARGET`.

| Target                                                                                         | Purpose / default artifacts                                                                                       |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `all` (default)                                                                                | Build the host `solver` and `mini`                                                                                |
| `check`                                                                                        | Host self-test, solution vectors with independent replay, invalid-input and output-failure checks                 |
| `rv32i`                                                                                        | Build renderer-off `build-rv32i/smoke.elf`                                                                        |
| `rv32i-smoke`                                                                                  | Validate the current target input; save `smoke.report.json` and `smoke.audit.json`                                |
| `rv32i-input-check`                                                                            | 122-case valid/invalid input matrix                                                                               |
| `rv32i-rank-check`                                                                             | P/Q ranking-domain and ABI checks                                                                                 |
| `rv32i-heuristic-check`                                                                        | Heuristic-domain and packed-nibble checks                                                                         |
| `rv32i-replay-check`                                                                           | Replay-only, invalid-path/coordinate, and saved-register checks                                                   |
| `rv32i-reference`                                                                              | Build GCC `build-rv32i/reference.elf`                                                                             |
| `rv32i-reference-check`                                                                        | Check the current input with the GCC reference                                                                    |
| `rv32i-reference-input-check`, `rv32i-reference-rank-check`, `rv32i-reference-heuristic-check` | GCC input/ranking/heuristic checks                                                                                |
| `rv32i-reference-info`                                                                         | Print the reference compiler and flags                                                                            |
| `rv32i-compare`                                                                                | Handwritten/GCC table consistency, linked sizes, and three queries; `comparison/summary.json`                     |
| `rv32i-calibration`                                                                            | Build a single memory/rate calibration kernel; use the driver below for batch measurements                        |
| `rv32i-gui`                                                                                    | Separate renderer-on build: `build-rv32i/gui/smoke.elf`                                                           |
| `rv32i-render-check`                                                                           | RAM framebuffer pixel validation; `render-tests/summary.json` and PNG previews                                    |
| `rv32i-pipeline-check`                                                                         | Short ISS/5-stage cases; `pipeline/summary.json` and `.pipeline.tsv`                                              |
| `rv32i-gui-evidence`                                                                           | Prepare three frozen GUI cases and `gui-evidence/manifest.json`                                                   |
| `clean`                                                                                        | Remove the host `solver` and `mini`                                                                               |
| `clean-rv32i`                                                                                  | Remove the listed intermediate files and ELFs from the selected `RV_BUILD`; retain gates and other subdirectories |

The Makefile also retains the auxiliary targets `indent` (clang-format 20) and
`prove` (Frama-C/Alt-Ergo). Regular builds and the validation workflow above do
not depend on them.

### Common variables

Override variables with `make TARGET NAME=value`. Defaults for regular targets
are listed below:

| Variable                        | Default / purpose                                                                                                      |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `CC`, `CFLAGS`                  | `cc`, `-O3 -std=c99 -Wall -Wextra -Wpedantic`; host compilation                                                        |
| `PYTHON`                        | `python3`                                                                                                              |
| `RV_CC`, `RV_LD`, `RV_OBJCOPY`  | `clang`, `ld.lld`, `llvm-objcopy`                                                                                      |
| `RV_ASFLAGS`                    | `--target=riscv32-unknown-elf -march=rv32i -mabi=ilp32`                                                                |
| `RV_BUILD`                      | `build-rv32i`; regular RV32I artifact directory                                                                        |
| `RV_INPUT`                      | `riscv/input.S`; CLI target input object                                                                               |
| `RIPES`, `RV_PROC`              | `/usr/bin/ripes`, `RV32_ISS`; regular target checks                                                                    |
| `RV_GCC`, `RV_REFERENCE_FLAGS`  | `riscv64-elf-gcc`, `-O2` plus RV32I/ILP32 and freestanding flags; use `rv32i-reference-info` to see the complete flags |
| `RV_RENDER`, `RV_RENDER_TEST`   | Both 0; renderer and RAM-test switches                                                                                 |
| `RV_RENDER_DELAY`               | 50000; busy-loop iterations between GUI frames                                                                         |
| `RV_GUI_INPUT`                  | Defaults to `RV_INPUT`; input for `rv32i-gui`                                                                          |
| `RV_LED_SYMBOLS`                | Absolute path to `riscv/led_symbols.inc`; GUI LED base/width/height symbols                                            |
| `RV_CAL_BYTES`, `RV_CAL_PASSES` | 65536, 1; size/passes for a single calibration kernel                                                                  |

For example, check the current input on another processor:

```sh
make rv32i-smoke RV_PROC=RV32_5S
```

`RV_BUILD` is an artifact path, not a cache key for all compiler flags. Use a
new build directory when switching toolchains or compiler flags. Renderer
configuration changes are tracked separately.

**Variable scope:** The Python drivers for `rv32i-compare`,
`rv32i-render-check`, and `rv32i-pipeline-check` use fixed paths
`build-rv32i` and `/usr/bin/ripes`. The pipeline driver also uses
Clang/LLD/objcopy directly. `rv32i-gui-evidence` identifies Ripes at the fixed
path `/usr/bin/ripes`; select an output session by calling the driver directly
with `--output`. The full gate and calibration drivers support their own
`--build` and `--ripes` arguments.

### Layered tests and complete validation gates

Complete the quick start first, then run the individual target checks in order:

```sh
make rv32i-input-check
make rv32i-rank-check
make rv32i-heuristic-check
make rv32i-replay-check
```

`make check` validates the host; it does not run the complete H3 check or the
target gate over all hardest states. The full workflow uses
[`riscv/check_gates.py`](riscv/check_gates.py) to collect resumable evidence:

```sh
python3 riscv/check_gates.py host --wall-seconds 80
python3 riscv/check_gates.py prepare
python3 riscv/check_gates.py target --wall-seconds 80
```

1. `host`: Run H1/H2/H4 and H3 in chunks of 65,536 ranks by default. Repeat
   the same command to resume until `summary.json` reports `H1_H2_H4=PASS`,
   `H3=PASS`, and a covered interval of `[0,3674160)`. Evidence is stored in
   `build-rv32i/gates/host/<identity>/`.
2. `prepare`: Build an immutable renderer-off ELF, all 2,644 exact-BFS
   distance-11 inputs, a pinned host oracle, and source/binary hashes. Select
   the run through `build-rv32i/gates/active.json`. Each target query replaces
   only the 15-byte input object.
3. `target`: Repeat the same command to resume unfinished cases until the run's
   `summary.json` reports `complete=true`, `measured=2644`, `gate=PASS`, and
   `over_budget_count=0`. Each query checks optimal length, independent replay,
   guest diagnostics, and a retired-instruction count of at most 50,000,000
   for the complete entry point.

**A successful driver exit with a `PARTIAL` summary means the work is
unfinished, not a whole-domain PASS.** The run directory retains
`manifest.json`, `hardest.txt`, templates, archived sources, `host-solver`, and
`records/*.json`. Use `--run` to select an existing target run. Do not start
multiple target drivers concurrently for the same run: they share `query.elf`.
The recorded complete target measurements took approximately 43 minutes
15 seconds in total, including oracle/checker/simulator startup.

Once all checks are complete, rebuild the final CLI image in the default build
directory with solved input and the renderer disabled, then independently
validate and export the evidence:

```sh
make rv32i RV_INPUT=build-rv32i/gates/template/input.S RV_RENDER=0 RV_RENDER_TEST=0
python3 riscv/export_gate_evidence.py --output build-rv32i/gates/verified-final.json
```

The exporter reads the default build, active run, and `/usr/bin/ripes` at fixed
paths, and requires the current `smoke.elf` to be byte-identical to the measured
template. It revalidates all records, paths, input-only ELF hashes, processor/ISA
settings, and the instruction budget. The example output is saved separately
in the build directory; the retained final result is
[`measurements/rv32i-final.json`](measurements/rv32i-final.json).

### GCC, measurements, and LED/pipeline checks

After building the host `solver`, run the following as needed:

```sh
make rv32i-reference-check
make rv32i-reference-input-check
make rv32i-reference-rank-check
make rv32i-reference-heuristic-check
make rv32i-compare RV_RENDER=0 RV_RENDER_TEST=0
python3 riscv/calibrate.py --phase memory
python3 riscv/calibrate.py --phase rate
make rv32i-render-check
make rv32i-pipeline-check
make rv32i-gui
```

Calibration RSS/rate measurements, binary identity, and raw logs are stored in
a Build-ID subdirectory under `build-rv32i/calibration/`. The renderer check
uses RAM instead of MMIO and validates actual solution frames pixel by pixel;
the PNGs are previews of the validated framebuffer. The pipeline check saves
ISS/5-stage JSON records and TSV traces.

For GUI use, open Ripes, add a **35×25 LED Matrix**, and check that the exported
`LED_MATRIX_0_BASE`, `LED_MATRIX_0_WIDTH`, and `LED_MATRIX_0_HEIGHT` match the
`RV_LED_SYMBOLS` file. Then load and run `build-rv32i/gui/smoke.elf`.
The default base is `0xf0000000`; for a different configuration, provide a
matching symbols file and rebuild. Select the cube with `RV_GUI_INPUT` and
adjust the display pace with `RV_RENDER_DELAY`.

`make rv32i-gui-evidence` prepares ELFs and frame-ready addresses for solved,
one-move, and distance-11 cases. If a session already exists, create another
in a new directory, for example:

```sh
python3 riscv/prepare_gui_cases.py --output build-rv32i/gui-evidence-new
```

Always choose a session directory that does not exist or is empty. Prepared
ELFs, RAM previews, pipeline telemetry, and actual GUI screenshots are distinct
types of evidence.

See sections 4–9 of [`report.md`](report.md) for the implementation, validation
results, and measurement interpretation. This section provides the operational
entry points. Illustrated explanations of input and move notation follow.

### Reading the 14-digit input

The program receives one 14-digit code with no spaces. For explanation, split
it into two groups:

```diagram
2134567 1111111
└── P ─┘ └── O ─┘
  cubies   twists
```

Imagine seven numbered seats and seven students. A position is a seat fixed in
space; a cubie is the physical corner that can move to another seat. In the
solved cube, cubie 1 sits in position 1, cubie 2 in position 2, and so on.
The real cube has no printed numbers; `0–7` are labels used only by this solver.

#### Step 1: Hold the cube in one direction

Keep `FRONT` facing you and `UP` pointing upward. Position `0` is the corner
nearest the upper-left of the front face. It is an anchor for describing the
other corners; the physical cubie is not glued in place.

```diagram
                              BACK
                    ·───────────────·
                   ╱               ╱│
                  ╱        UP     ╱ │
                 ╱               ╱  │
              [0]───────────────·   │
               │                │   │
               │     FRONT      │ R │
               │                │   ·
               │                │  ╱
               │                │ ╱
               │                │╱
               ·────────────────·
```

`R` marks the narrow `RIGHT` face.

#### Step 2: Separate the front and back layers

A 2×2×2 cube has only corner cubies. Looking from the fixed direction, four
corner positions touch the front face and four touch the back face. Each
bracketed number below names one whole corner, not one colored sticker:

```diagram
 FRONT LAYER                          BACK LAYER

 upper-left   upper-right             upper-left   upper-right
     [0]────────[1]                       [7]────────[4]
      │          │                         │          │
      │          │       front ↔ back      │          │
     [3]────────[2]                       [6]────────[5]
 down-left    down-right               down-left    down-right
```

The front layer runs clockwise from its upper-left corner as `0, 1, 2, 3`.
The back layer is drawn as if seen through the cube from the front: `7` is
upper-left, followed clockwise by `4, 5, 6`.

#### Step 3: Join the two layers into positions 0–7

Slide the back square up and to the right, the same direction the cube recedes
in Step 1, to get the complete 2.5D position map. The back edges are drawn
through the front face rather than hidden behind it:

```diagram
                           BACK
                      [7]────────[4]
                     ╱ │        ╱ │
                  [0]──│─────[1]  │
                   │   │      │   │
                   │  [6]─────│──[5]
                   │ ╱        │ ╱
                  [3]────────[2]
                      FRONT
```

The seven characters of `P` describe positions `1, 2, 3, 4, 5, 6, 7` in that
order; the anchor at position `0` is left out.

#### Step 4: Put the cubies into those positions

Compare the position map on the left with the filled cube on the right. Read
`P = 2134567` from left to right to fill the positions. The arrows below the
figure identify the two positions that change.

```diagram
 POSITION MAP                             AFTER P = 2134567
 (fixed seats)                            (cubies now in seats)

     [7]────────[4]                           [7]────────[4]
    ╱ │        ╱ │                           ╱ │        ╱ │
 [0]──│─────[1]  │                        [0]──│─────[2]  │
  │   │      │   │                         │   │      │   │
  │  [6]─────│──[5]                        │  [6]─────│──[5]
  │ ╱        │ ╱                           │ ╱        │ ╱
 [3]────────[2]                           [3]────────[1]
     FRONT                                    FRONT

 position:     1 2 3 4 5 6 7
 P says:       2 1 3 4 5 6 7
               │ │ └───────── cubies 3–7 stay in their matching seats
               │ └─────────── put cubie 1 in position 2: [2] becomes [1]
               └───────────── put cubie 2 in position 1: [1] becomes [2]
```

So the first two digits, `21`, exchange the two corners on the front-right
edge. The remaining digits, `34567`, leave the other five movable corners
where they were. `P` must contain every digit from `1` through `7` exactly
once; otherwise a cubie would be missing or duplicated.

The seven seats named by `P` are:

| Position | Corner of the cube  |
| :------: | :------------------ |
|    1     | front, upper, right |
|    2     | front, down, right  |
|    3     | front, down, left   |
|    4     | back, upper, right  |
|    5     | back, down, right   |
|    6     | back, down, left    |
|    7     | back, upper, left   |

The second group, `O = 1111111`, describes the twist of the cubie in each of
those same seven positions:

| Digit | Meaning          |
| :---: | :--------------- |
|   1   | not twisted      |
|   2   | twisted by +120° |
|   3   | twisted by −120° |

Here every orientation digit is `1`, so the two corners change places without
being twisted. For a valid cube, convert orientation digits to `0`, `1`, and
`2`; their sum must be divisible by three. The solved code is
`12345671111111`. `make check` uses the exchanged-corner example above.

## Reading the solution

```text
$ ./solver 21345671111111
B' R' D2 R' B R B' R D2 B R'
```

Each token is one face turn. Apply them left to right; after the last one the
cube is solved. This is one optimal path; the solver may print another path of
the same shortest length.

| Token | Meaning                             |
| :---: | :---------------------------------- |
|  `R`  | turn the `RIGHT` face 90° clockwise |
|  `B`  | turn the `BACK` face 90° clockwise  |
|  `D`  | turn the `DOWN` face 90° clockwise  |

Clockwise means clockwise as seen by someone looking directly at that face from
outside the cube, so you have to walk around to the back to read `B` and look up
from underneath to read `D`. Two suffixes modify a turn:

| Suffix | Meaning                           |
| :----: | :-------------------------------- |
|  none  | 90° clockwise                     |
|  `'`   | 90° counterclockwise, the inverse |
|  `2`   | 180°, direction does not matter   |

`R`, `B`, and `D` are the only faces that appear, because turning `UP`, `FRONT`,
or `LEFT` would move the anchor at position `0`. A turn counts as one move
whichever suffix it carries, which is the half-turn metric; under that metric no
position needs more than 11 moves. Solving an already-solved cube prints an
empty line.

See [`report.md`](report.md) for the current implementation and validation
report, and [`baseline-report.md`](baseline-report.md) for the original
model and diagrams.
