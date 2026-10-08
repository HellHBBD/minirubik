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

以下命令都從 repository 根目錄執行。操作流程依序是：**host 編譯 → host
測試 → RV32I 編譯 → target 個別檢查 → 完整 gates → 選用的比較與視覺化**。

### 環境與工具

| 工作 | 所需工具 |
| --- | --- |
| Host C | Make、C99 compiler（預設 `cc`）、Python 3 |
| 手寫 RV32I | `clang`、`ld.lld`、`llvm-objcopy`、Ripes |
| GCC reference | 以上工具，加上 `riscv64-elf-gcc`（輸出 `-march=rv32i -mabi=ilp32`） |
| 量測與 binary identity | GNU `readelf`；`pacman` 若存在則用來記錄 package owner |
| 有限前景執行 | `guard-run`、GNU `timeout` |

既有量測使用 `/usr/bin/ripes`，package 為
`ripes-git 2.2.6.r108.g0b4c65b-1`，Build ID 為
`1b3e4f66c547c43ca72e2253150dbd67bdad1821`。CLI checks 使用
`RV32_ISS`；pipeline tests 另外使用 `RV32_5S`。Python drivers 會設定
`QT_QPA_PLATFORM=offscreen`，不需要先開啟 GUI。

下面使用 `guard-run` 搭配有限 timeout 執行編譯、模擬與全域驗證。
`--wall-seconds` 是 gate driver 停止啟動新 cases 的時間，不是單一 simulator
timeout；完成的 cases 會立即存檔。

### 快速開始

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s make
guard-run -- timeout --signal=TERM --kill-after=10s 120s ./solver 21345671111111
guard-run -- timeout --signal=TERM --kill-after=10s 120s make check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-smoke
```

`make` 預設建立 `solver` 與 `mini`。`solver` 是主要 C implementation，具有
contracts、self-test、表格匯出與 diagnostics；`mini` 是保留作為可讀性對照的
golfed BFS 版本，沒有 self-test，失敗時不印 diagnostics。兩者都應回傳
optimal solution，但合法最短路徑可以不同。

Host 的 14-digit argument 是輸入，stdout 是 move line；solved 印空行。
成功 status 為 0，非法輸入為 2，內部／輸出失敗為 1。

`make rv32i` 產生 `build-rv32i/smoke.debug.elf`（保留 symbols）與
`build-rv32i/smoke.elf`（載入 Ripes 的 stripped image）。雖然名稱是
`smoke.elf`，內容是完整 parse／rank／search／replay／output entry。
`rv32i-smoke` 執行目前編譯進 ELF 的輸入，並核對 guest status、coordinates、
heuristic、optimal length、replay 與輸出。名稱相同的 `.debug.elf` 供 checker
讀取 input 與 symbols，應與 `.elf` 一起保留。

### 編譯流程與輸入設定

```text
solver.c ── cc ──→ solver ── --emit-tables ──→ tables.S
                                                 ↓
                     手寫 .S + input.S + tables.S
                                  ↓ clang
                                 *.o
                                  ↓ ld.lld + riscv/link.ld
                          smoke.debug.elf
                                  ↓ llvm-objcopy
                             smoke.elf
                                  ↓
                        Ripes + Python checker
```

Makefile 先用 host `solver` 匯出 query tables，再把手寫 assembly 與表格組譯成
RV32I objects，依 `riscv/link.ld` 連結，最後移除 symbols 與 `.riscv.attributes`。
GCC reference 使用 `riscv/reference.c` include 同一份 `solver.c` 的 target mode，
搭配 reference tables 與 ABI bridges；entry、replay、output 共用。

**RV32I 輸入來自編譯進 ELF 的 `cube_input`，不是命令列 argument。**
預設 [`riscv/input.S`](riscv/input.S) 的 `.asciz` 是 solved code
`12345671111111`。要測另一個 cube，可修改這個字串後重建，或提供具有相同
section／symbol 定義的獨立 `.S` 檔，再用 `RV_INPUT=檔案路徑` 指定。
`input.o` 每次都重新組譯；checkers 從 ELF 讀取實際字串。

### Makefile targets

以下 targets 均以 `make TARGET` 使用；編譯與驗證命令沿用快速開始的有限執行形式。

| Target | 用途／預設產物 |
| --- | --- |
| `all`（預設） | 建立 host `solver`、`mini` |
| `check` | Host self-test、solution vectors／獨立 replay、非法輸入與輸出失敗 checks |
| `rv32i` | 建立 renderer-off `build-rv32i/smoke.elf` |
| `rv32i-smoke` | 驗證目前 target input；保存 `smoke.report.json`、`smoke.audit.json` |
| `rv32i-input-check` | 122-case valid／invalid input matrix |
| `rv32i-rank-check` | P/Q ranking domain 與 ABI checks |
| `rv32i-heuristic-check` | Heuristic domain 與 packed-nibble checks |
| `rv32i-replay-check` | Replay-only、非法 path／coordinates 與 saved-register checks |
| `rv32i-reference` | 建立 GCC `build-rv32i/reference.elf` |
| `rv32i-reference-check` | GCC reference 的目前 input check |
| `rv32i-reference-input-check`、`rv32i-reference-rank-check`、`rv32i-reference-heuristic-check` | GCC 的 input／ranking／heuristic checks |
| `rv32i-reference-info` | 印出 reference compiler 與 flags |
| `rv32i-compare` | Hand／GCC 的表格一致性、linked size 與三個 queries；`comparison/summary.json` |
| `rv32i-calibration` | 建立單一 memory／rate calibration kernel；批次量測使用下方 driver |
| `rv32i-gui` | 獨立 renderer-on build：`build-rv32i/gui/smoke.elf` |
| `rv32i-render-check` | RAM framebuffer 像素驗證；`render-tests/summary.json` 與 PNG previews |
| `rv32i-pipeline-check` | ISS／5-stage 短例；`pipeline/summary.json` 與 `.pipeline.tsv` |
| `rv32i-gui-evidence` | 準備三個 frozen GUI cases 與 `gui-evidence/manifest.json` |
| `clean` | 刪除 host `solver`、`mini` |
| `clean-rv32i` | 刪除所選 `RV_BUILD` 的列舉中間檔／ELFs；保留 gates 與其他子目錄 |

Makefile 另保留 `indent`（clang-format 20）與 `prove`（Frama-C／Alt-Ergo）
輔助 targets；一般編譯與上述驗證流程不依賴它們。

### 常用變數

以 `make TARGET NAME=value` 覆寫。一般 target 的預設值如下：

| 變數 | 預設值／作用 |
| --- | --- |
| `CC`、`CFLAGS` | `cc`、`-O3 -std=c99 -Wall -Wextra -Wpedantic`；host 編譯 |
| `PYTHON` | `python3` |
| `RV_CC`、`RV_LD`、`RV_OBJCOPY` | `clang`、`ld.lld`、`llvm-objcopy` |
| `RV_ASFLAGS` | `--target=riscv32-unknown-elf -march=rv32i -mabi=ilp32` |
| `RV_BUILD` | `build-rv32i`；一般 RV32I 產物目錄 |
| `RV_INPUT` | `riscv/input.S`；CLI target input object |
| `RIPES`、`RV_PROC` | `/usr/bin/ripes`、`RV32_ISS`；一般 target checks |
| `RV_GCC`、`RV_REFERENCE_FLAGS` | `riscv64-elf-gcc`、`-O2` 加上 RV32I／ILP32 與 freestanding flags；完整 flags 可用 `rv32i-reference-info` 查看 |
| `RV_RENDER`、`RV_RENDER_TEST` | 均為 0；renderer switch 與 RAM test switch |
| `RV_RENDER_DELAY` | 50000；GUI frame 間 busy-loop 次數 |
| `RV_GUI_INPUT` | 預設沿用 `RV_INPUT`；`rv32i-gui` 的輸入 |
| `RV_LED_SYMBOLS` | `riscv/led_symbols.inc` 的絕對路徑；GUI LED base／width／height symbols |
| `RV_CAL_BYTES`、`RV_CAL_PASSES` | 65536、1；單一 calibration kernel 大小／passes |

例如以另一個 processor 檢查目前 input：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-smoke RV_PROC=RV32_5S
```

`RV_BUILD` 是產物路徑，不是所有 compiler flags 的 cache key；切換 toolchain
或編譯 flags 時使用新的 build 目錄。Renderer configuration 有獨立變更追蹤。

**變數的作用範圍：** `rv32i-compare`、`rv32i-render-check`、
`rv32i-pipeline-check` 的 Python drivers 固定使用 `build-rv32i` 與
`/usr/bin/ripes`；pipeline driver 也直接使用 Clang／LLD／objcopy。
`rv32i-gui-evidence` 的 Ripes identity 固定為 `/usr/bin/ripes`，輸出 session
可透過直接呼叫 driver 的 `--output` 指定。完整 gate／calibration drivers
則支援自己的 `--build`、`--ripes` arguments。

### 分層測試與完整 gates

先完成快速開始，再依序執行 target 的個別 checks：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-input-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-rank-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-heuristic-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-replay-check
```

`make check` 驗證 host，並不執行完整 H3 或全部 hardest-state target gate。
完整流程由 [`riscv/check_gates.py`](riscv/check_gates.py) 收集可接續的證據：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 240s python3 riscv/check_gates.py host --wall-seconds 80
guard-run -- timeout --signal=TERM --kill-after=10s 120s python3 riscv/check_gates.py prepare
guard-run -- timeout --signal=TERM --kill-after=10s 120s python3 riscv/check_gates.py target --wall-seconds 80
```

1. `host`：H1／H2／H4 加上分段 H3，每段預設 65,536 ranks。重複同一命令
   可接續，直到 `summary.json` 顯示 `H1_H2_H4=PASS`、`H3=PASS`，且 covered
   interval 是 `[0,3674160)`。證據位於 `build-rv32i/gates/host/<identity>/`。
2. `prepare`：建立 renderer-off immutable ELF、exact BFS 的全部 2,644
   distance-11 inputs、pinned host oracle 與 source／binary hashes；以
   `build-rv32i/gates/active.json` 選定 run。每次 target query 只替換 15-byte
   input object。
3. `target`：重複同一命令接續未完成 cases，直到 run 的 `summary.json` 顯示
   `complete=true`、`measured=2644`、`gate=PASS`、`over_budget_count=0`。
   每個 query 核對 optimal length、獨立 replay、guest diagnostics，以及
   完整 entry 的 retired instructions 不超過 50,000,000。

**Driver 正常返回但摘要是 `PARTIAL`，表示尚未完成，不是全域 PASS。**
Run 目錄保存 `manifest.json`、`hardest.txt`、templates、archived sources、
`host-solver` 與 `records/*.json`。`--run` 可選定既有 target run；同一 run
不可同時啟動多個 target drivers，因為共用 `query.elf`。既有完整 target
量測累計約 43 分 15 秒，包含 oracle／checker／simulator 啟動。

全部完成後，以 solved input、renderer-off、預設 build 重建最終 CLI image，
再獨立核對與匯出：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i RV_INPUT=build-rv32i/gates/template/input.S RV_RENDER=0 RV_RENDER_TEST=0
guard-run -- timeout --signal=TERM --kill-after=10s 120s python3 riscv/export_gate_evidence.py --output build-rv32i/gates/verified-final.json
```

Exporter 固定讀取預設 build、active run 與 `/usr/bin/ripes`，並要求當前
`smoke.elf` 與 measured template 逐 byte 相同。它重新核對全部 records、
paths、input-only ELF hashes、processor／ISA 與 instruction budget。
範例輸出另存於 build 目錄；已保存的正式結果為
[`measurements/rv32i-final.json`](measurements/rv32i-final.json)。

### GCC、量測與 LED／pipeline

Host `solver` 已建立後，可依需求執行：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-reference-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-reference-input-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-reference-rank-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-reference-heuristic-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-compare RV_RENDER=0 RV_RENDER_TEST=0
guard-run -- timeout --signal=TERM --kill-after=10s 120s python3 riscv/calibrate.py --phase memory
guard-run -- timeout --signal=TERM --kill-after=10s 180s python3 riscv/calibrate.py --phase rate
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-render-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-pipeline-check
guard-run -- timeout --signal=TERM --kill-after=10s 120s make rv32i-gui
```

Calibration 的 RSS／rate、binary identity 與 raw logs 存在
`build-rv32i/calibration/` 下的 Build-ID 子目錄。Renderer check 以 RAM 代替
MMIO，逐像素核對 actual solution frames；PNG 是已驗證 framebuffer 的
preview。Pipeline check 保存 ISS／5-stage JSON 與 TSV trace。

GUI 操作：開啟 Ripes，加入 **35×25 LED Matrix**，確認匯出的
`LED_MATRIX_0_BASE`、`LED_MATRIX_0_WIDTH`、`LED_MATRIX_0_HEIGHT` 與
`RV_LED_SYMBOLS` 檔案相符，再載入 `build-rv32i/gui/smoke.elf` 執行。
預設 base 為 `0xf0000000`；配置不同時，提供對應 symbols 檔重建。
以 `RV_GUI_INPUT` 選擇 cube，`RV_RENDER_DELAY` 調整顯示節奏。

`make rv32i-gui-evidence` 可準備 solved／one-move／distance-11 的 ELFs 與
frame-ready addresses；若已有 session，以新目錄建立另一份，例如：

```sh
guard-run -- timeout --signal=TERM --kill-after=10s 120s python3 riscv/prepare_gui_cases.py --output build-rv32i/gui-evidence-new
```

每次選用尚未存在或為空的 session 目錄。準備 ELFs、RAM previews、pipeline
telemetry 與實際 GUI screenshots 是不同的證據類型。

實作、驗證結果與量測解讀見 [`report.md`](report.md) 第 4–8 節；
本節提供操作入口。輸入與 move notation 的圖解如下。

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

| Position | Corner of the cube |
| :---: | :--- |
| 1 | front, upper, right |
| 2 | front, down, right |
| 3 | front, down, left |
| 4 | back, upper, right |
| 5 | back, down, right |
| 6 | back, down, left |
| 7 | back, upper, left |

The second group, `O = 1111111`, describes the twist of the cubie in each of
those same seven positions:

| Digit | Meaning |
| :---: | :--- |
| 1 | not twisted |
| 2 | twisted by +120° |
| 3 | twisted by −120° |

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

| Token | Meaning |
| :---: | :--- |
| `R` | turn the `RIGHT` face 90° clockwise |
| `B` | turn the `BACK` face 90° clockwise |
| `D` | turn the `DOWN` face 90° clockwise |

Clockwise means clockwise as seen by someone looking directly at that face from
outside the cube, so you have to walk around to the back to read `B` and look up
from underneath to read `D`. Two suffixes modify a turn:

| Suffix | Meaning |
| :---: | :--- |
| none | 90° clockwise |
| `'` | 90° counterclockwise, the inverse |
| `2` | 180°, direction does not matter |

`R`, `B`, and `D` are the only faces that appear, because turning `UP`, `FRONT`,
or `LEFT` would move the anchor at position `0`. A turn counts as one move
whichever suffix it carries, which is the half-turn metric; under that metric no
position needs more than 11 moves. Solving an already-solved cube prints an
empty line.

See [`report.md`](report.md) for the current implementation and validation
report, and [`baseline-report.md`](baseline-report.md) for the original
model and diagrams.
