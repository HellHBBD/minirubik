CC ?= cc
CFLAGS ?= -O3 -std=c99 -Wall -Wextra -Wpedantic
FRAMA_C ?= frama-c
RV_CC ?= clang
RV_LD ?= ld.lld
RV_OBJCOPY ?= llvm-objcopy
RV_ASFLAGS ?= --target=riscv32-unknown-elf -march=rv32i -mabi=ilp32
RV_BUILD ?= build-rv32i
RV_INPUT ?= riscv/input.S
RIPES ?= /usr/bin/ripes
RV_PROC ?= RV32_ISS
PYTHON ?= python3
RV_CAL_BYTES ?= 65536
RV_CAL_PASSES ?= 1
RV_GCC ?= riscv64-elf-gcc
RV_REFERENCE_FLAGS ?= -O2 -std=c99 -march=rv32i -mabi=ilp32 -ffreestanding \
	-fno-builtin -fno-pic -fno-pie -msmall-data-limit=0 -mno-relax \
	-ffunction-sections -fdata-sections
RV_RENDER ?= 0
RV_RENDER_TEST ?= 0
RV_RENDER_DELAY ?= 50000
RV_LED_SYMBOLS ?= $(abspath riscv/led_symbols.inc)
RV_GUI_INPUT ?= $(RV_INPUT)
RV_RENDER_FIXTURE ?= $(RV_BUILD)/render-fixtures.S
RV_RENDER_FLAGS = -DRENDER=$(RV_RENDER) -DRENDER_TEST=$(RV_RENDER_TEST) \
	-DRENDER_DELAY=$(RV_RENDER_DELAY) -DLED_SYMBOLS='"$(RV_LED_SYMBOLS)"' \
	-DRENDER_TABLES='"$(abspath $(RV_BUILD)/render-tables.inc)"'
RV_RENDER_TEST_OBJECTS = $(if $(filter 1,$(RV_RENDER_TEST)),$(RV_BUILD)/render-check.o $(RV_BUILD)/render-fixtures.o)
CLANG_FORMAT := $(shell command -v clang-format-20 2>/dev/null || \
	command -v clang-format 2>/dev/null)
C_SOURCES := $(wildcard *.c *.h)
SAMPLE_STATE := 21345671111111
SAMPLE_SOLUTION := B' R' D2 R' B R B' R D2 B R'
VECTORS := tests/solutions.txt
# One per rejection path: short, long, cubie digit low, cubie digit high,
# orientation digit low, orientation digit high, non-digit, duplicate, sum.
INVALID_STATES := 1234567111111 123456711111111 02345671111111 82345671111111 \
	12345671111110 12345671111114 1234567111111a 11345671111111 12345671111112

.PHONY: all check prove clean indent rv32i rv32i-smoke rv32i-input-check rv32i-rank-check clean-rv32i force-rv-input

all: solver mini

solver: solver.c
	$(CC) $(CFLAGS) $< -o $@

mini: mini.c
	$(CC) $(CFLAGS) $< -o $@

rv32i: $(RV_BUILD)/smoke.elf

$(RV_BUILD):
	mkdir -p "$@"

$(RV_BUILD)/tables.S: solver | $(RV_BUILD)
	./solver --emit-tables >"$@"

$(RV_BUILD)/tables.o: $(RV_BUILD)/tables.S
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

.PHONY: force-render-config
force-render-config:

$(RV_BUILD)/render-config: force-render-config | $(RV_BUILD)
	@$(PYTHON) -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); v="\n".join(sys.argv[2:])+"\n"; p.write_text(v) if not p.exists() or p.read_text()!=v else None' "$@" "$(RV_RENDER)" "$(RV_RENDER_TEST)" "$(RV_RENDER_DELAY)" "$(RV_LED_SYMBOLS)"

$(RV_BUILD)/render-tables.inc: riscv/cube_geometry.py riscv/check_smoke.py | $(RV_BUILD)
	$(PYTHON) riscv/cube_geometry.py >"$@"

$(RV_BUILD)/entry.o: riscv/entry.S $(RV_BUILD)/render-config | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) $(RV_RENDER_FLAGS) -c "$<" -o "$@"

$(RV_BUILD)/parse.o: riscv/parse.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/rank.o: riscv/rank.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/heuristic.o: riscv/heuristic.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/move.o: riscv/move.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/search.o: riscv/search.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/replay.o: riscv/replay.S $(RV_BUILD)/render-config | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) $(RV_RENDER_FLAGS) -c "$<" -o "$@"

$(RV_BUILD)/render.o: riscv/render.S $(RV_BUILD)/render-config $(RV_BUILD)/render-tables.inc $(if $(filter 1,$(RV_RENDER)),$(RV_LED_SYMBOLS)) | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) $(RV_RENDER_FLAGS) -c "$<" -o "$@"

$(RV_BUILD)/render-check.o: riscv/render_check.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/render-fixtures.o: $(RV_RENDER_FIXTURE) | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/output.o: riscv/output.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

force-rv-input:

$(RV_BUILD)/input.o: $(RV_INPUT) force-rv-input | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/smoke.debug.elf: $(RV_BUILD)/entry.o $(RV_BUILD)/parse.o $(RV_BUILD)/rank.o $(RV_BUILD)/heuristic.o $(RV_BUILD)/move.o $(RV_BUILD)/search.o $(RV_BUILD)/replay.o $(RV_BUILD)/render.o $(RV_RENDER_TEST_OBJECTS) $(RV_BUILD)/output.o $(RV_BUILD)/tables.o $(RV_BUILD)/input.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/entry.o $(RV_BUILD)/parse.o $(RV_BUILD)/rank.o $(RV_BUILD)/heuristic.o $(RV_BUILD)/move.o $(RV_BUILD)/search.o $(RV_BUILD)/replay.o $(RV_BUILD)/render.o $(RV_RENDER_TEST_OBJECTS) $(RV_BUILD)/output.o $(RV_BUILD)/tables.o $(RV_BUILD)/input.o

$(RV_BUILD)/smoke.elf: $(RV_BUILD)/smoke.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-smoke: $(RV_BUILD)/smoke.elf
	$(PYTHON) riscv/check_smoke.py "$(RIPES)" "$<" "$(RV_PROC)"

.PHONY: rv32i-reference rv32i-reference-check rv32i-reference-input-check rv32i-reference-rank-check rv32i-reference-heuristic-check rv32i-reference-info rv32i-compare
rv32i-reference-info:
	@$(PYTHON) -c 'import json,sys; print(json.dumps({"compiler":sys.argv[1],"flags":sys.argv[2]}))' "$(RV_GCC)" "$(RV_REFERENCE_FLAGS)"

rv32i-compare:
	$(PYTHON) riscv/compare_reference.py
$(RV_BUILD)/reference-tables.S: solver | $(RV_BUILD)
	./solver --emit-reference-tables >"$@"

$(RV_BUILD)/reference-tables.o: $(RV_BUILD)/reference-tables.S
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/reference.o: riscv/reference.c solver.c | $(RV_BUILD)
	$(RV_GCC) $(RV_REFERENCE_FLAGS) -c "$<" -o "$@"

$(RV_BUILD)/reference-bridge.o: riscv/reference_bridge.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/reference.debug.elf: $(RV_BUILD)/entry.o $(RV_BUILD)/replay.o $(RV_BUILD)/render.o $(RV_RENDER_TEST_OBJECTS) $(RV_BUILD)/output.o $(RV_BUILD)/reference.o $(RV_BUILD)/reference-bridge.o $(RV_BUILD)/reference-tables.o $(RV_BUILD)/input.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax --gc-sections -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/entry.o $(RV_BUILD)/replay.o $(RV_BUILD)/render.o $(RV_RENDER_TEST_OBJECTS) $(RV_BUILD)/output.o \
		$(RV_BUILD)/reference.o $(RV_BUILD)/reference-bridge.o \
		$(RV_BUILD)/reference-tables.o $(RV_BUILD)/input.o

$(RV_BUILD)/reference.elf: $(RV_BUILD)/reference.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-reference: $(RV_BUILD)/reference.elf

rv32i-reference-check: $(RV_BUILD)/reference.elf
	$(PYTHON) riscv/check_smoke.py "$(RIPES)" "$<" "$(RV_PROC)"

rv32i-reference-input-check: $(RV_BUILD)/reference.elf
	$(PYTHON) riscv/check_inputs.py --ripes "$(RIPES)" --build "$(RV_BUILD)" \
		--processor "$(RV_PROC)" --input "$(RV_INPUT)" --target rv32i-reference

$(RV_BUILD)/reference-rank.debug.elf: $(RV_BUILD)/rank-check.o $(RV_BUILD)/reference.o $(RV_BUILD)/reference-bridge.o $(RV_BUILD)/rank-cases.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax --gc-sections -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/rank-check.o $(RV_BUILD)/reference.o \
		$(RV_BUILD)/reference-bridge.o $(RV_BUILD)/rank-cases.o

$(RV_BUILD)/reference-rank.elf: $(RV_BUILD)/reference-rank.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-reference-rank-check: $(RV_BUILD)/reference-rank.elf
	$(PYTHON) riscv/check_ranks.py "$(RIPES)" "$<" "$(RV_PROC)"

$(RV_BUILD)/reference-heuristic.debug.elf: $(RV_BUILD)/heuristic-check.o $(RV_BUILD)/reference.o $(RV_BUILD)/reference-tables.o $(RV_BUILD)/heuristic-cases.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax --gc-sections -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/heuristic-check.o $(RV_BUILD)/reference.o \
		$(RV_BUILD)/reference-tables.o $(RV_BUILD)/heuristic-cases.o

$(RV_BUILD)/reference-heuristic.elf: $(RV_BUILD)/reference-heuristic.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-reference-heuristic-check: $(RV_BUILD)/reference-heuristic.elf
	$(PYTHON) riscv/check_heuristics.py "$(RIPES)" "$<" "$(RV_PROC)"

rv32i-input-check: $(RV_BUILD)/smoke.elf
	$(PYTHON) riscv/check_inputs.py --ripes "$(RIPES)" \
		--build "$(RV_BUILD)" --processor "$(RV_PROC)" --input "$(RV_INPUT)"

$(RV_BUILD)/rank-cases.S: solver | $(RV_BUILD)
	./solver --emit-rank-cases >"$@"

$(RV_BUILD)/rank-cases.o: $(RV_BUILD)/rank-cases.S
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/rank-check.o: riscv/rank_check.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/rank-check.debug.elf: $(RV_BUILD)/rank-check.o $(RV_BUILD)/rank.o $(RV_BUILD)/rank-cases.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/rank-check.o $(RV_BUILD)/rank.o $(RV_BUILD)/rank-cases.o

$(RV_BUILD)/rank-check.elf: $(RV_BUILD)/rank-check.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-rank-check: $(RV_BUILD)/rank-check.elf
	$(PYTHON) riscv/check_ranks.py "$(RIPES)" "$<" "$(RV_PROC)"

.PHONY: rv32i-heuristic-check
$(RV_BUILD)/heuristic-cases.S: solver | $(RV_BUILD)
	./solver --emit-heuristic-cases >"$@"

$(RV_BUILD)/heuristic-cases.o: $(RV_BUILD)/heuristic-cases.S
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/heuristic-check.o: riscv/heuristic_check.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/heuristic-check.debug.elf: $(RV_BUILD)/heuristic-check.o $(RV_BUILD)/heuristic.o $(RV_BUILD)/tables.o $(RV_BUILD)/heuristic-cases.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/heuristic-check.o $(RV_BUILD)/heuristic.o $(RV_BUILD)/tables.o $(RV_BUILD)/heuristic-cases.o

$(RV_BUILD)/heuristic-check.elf: $(RV_BUILD)/heuristic-check.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-heuristic-check: $(RV_BUILD)/heuristic-check.elf
	$(PYTHON) riscv/check_heuristics.py "$(RIPES)" "$<" "$(RV_PROC)"

.PHONY: rv32i-replay-check
$(RV_BUILD)/replay-check.o: riscv/replay_check.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/replay-check.debug.elf: $(RV_BUILD)/replay-check.o $(RV_BUILD)/replay.o $(RV_BUILD)/move.o $(RV_BUILD)/tables.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/replay-check.o $(RV_BUILD)/replay.o $(RV_BUILD)/move.o $(RV_BUILD)/tables.o

$(RV_BUILD)/replay-check.elf: $(RV_BUILD)/replay-check.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-replay-check: $(RV_BUILD)/replay-check.elf
	$(PYTHON) riscv/check_replay.py "$(RIPES)" "$<" "$(RV_PROC)"

.PHONY: rv32i-calibration force-rv-calibration
force-rv-calibration:

$(RV_BUILD)/calibration.o: riscv/calibration.S force-rv-calibration | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -DCAL_BYTES=$(RV_CAL_BYTES) \
		-DCAL_PASSES=$(RV_CAL_PASSES) -c "$<" -o "$@"

$(RV_BUILD)/calibration.debug.elf: $(RV_BUILD)/calibration.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" $(RV_BUILD)/calibration.o

$(RV_BUILD)/calibration.elf: $(RV_BUILD)/calibration.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-calibration: $(RV_BUILD)/calibration.elf

.PHONY: rv32i-gui rv32i-render-check rv32i-pipeline-check rv32i-gui-evidence
rv32i-gui:
	$(MAKE) rv32i RV_BUILD=$(RV_BUILD)/gui RV_INPUT=$(RV_GUI_INPUT) RV_RENDER=1 RV_RENDER_TEST=0

rv32i-render-check:
	$(PYTHON) riscv/check_render.py

rv32i-pipeline-check:
	$(PYTHON) riscv/check_pipeline.py

rv32i-gui-evidence:
	$(PYTHON) riscv/prepare_gui_cases.py

clean-rv32i:
	$(RM) "$(RV_BUILD)/render.o" "$(RV_BUILD)/render-check.o" \
		"$(RV_BUILD)/render-fixtures.o" "$(RV_BUILD)/render-config" "$(RV_BUILD)/render-tables.inc"
	$(RM) "$(RV_BUILD)/reference-rank.debug.elf" "$(RV_BUILD)/reference-rank.elf" \
		"$(RV_BUILD)/reference-rank.report.json" "$(RV_BUILD)/reference-heuristic.debug.elf" \
		"$(RV_BUILD)/reference-heuristic.elf" "$(RV_BUILD)/reference-heuristic.report.json"
	$(RM) "$(RV_BUILD)/reference.o" "$(RV_BUILD)/reference-bridge.o" \
		"$(RV_BUILD)/reference-tables.S" "$(RV_BUILD)/reference-tables.o" \
		"$(RV_BUILD)/reference.debug.elf" "$(RV_BUILD)/reference.elf" \
		"$(RV_BUILD)/reference.report.json"
	$(RM) "$(RV_BUILD)/calibration.o" "$(RV_BUILD)/calibration.debug.elf" \
		"$(RV_BUILD)/calibration.elf" "$(RV_BUILD)/calibration.audit.json"
	$(RM) "$(RV_BUILD)/replay-check.o" "$(RV_BUILD)/replay-check.debug.elf" \
		"$(RV_BUILD)/replay-check.elf" $(wildcard $(RV_BUILD)/replay-check.*.report.json)
	$(RM) "$(RV_BUILD)/move.o" "$(RV_BUILD)/search.o" \
		"$(RV_BUILD)/replay.o" "$(RV_BUILD)/output.o"
	$(RM) "$(RV_BUILD)/heuristic.o" "$(RV_BUILD)/heuristic-cases.S" \
		"$(RV_BUILD)/heuristic-cases.o" "$(RV_BUILD)/heuristic-check.o" \
		"$(RV_BUILD)/heuristic-check.debug.elf" "$(RV_BUILD)/heuristic-check.elf" \
		"$(RV_BUILD)/heuristic-check.report.json"
	$(RM) "$(RV_BUILD)/tables.S" "$(RV_BUILD)/tables.o" \
		"$(RV_BUILD)/entry.o" "$(RV_BUILD)/parse.o" "$(RV_BUILD)/rank.o" "$(RV_BUILD)/input.o" \
		"$(RV_BUILD)/smoke.debug.elf" "$(RV_BUILD)/smoke.elf" \
		"$(RV_BUILD)/smoke.report.json"
	$(RM) "$(RV_BUILD)/rank-cases.S" "$(RV_BUILD)/rank-cases.o" \
		"$(RV_BUILD)/rank-check.o" "$(RV_BUILD)/rank-check.debug.elf" \
		"$(RV_BUILD)/rank-check.elf" "$(RV_BUILD)/rank-check.report.json"

check: solver mini $(VECTORS)
	./solver --self-test
	$(PYTHON) tests/check_solutions.py
	@for binary in ./solver ./mini; do \
		for bad in $(INVALID_STATES); do \
			$$binary "$$bad" >/dev/null 2>&1; \
			status=$$?; \
			test $$status -eq 2 || { \
				echo "$$binary $$bad: expected status 2, got $$status"; exit 1; }; \
		done; \
		$$binary >/dev/null 2>&1; \
		status=$$?; \
		test $$status -eq 2 || { \
			echo "$$binary with no argument: expected status 2, got $$status"; \
			exit 1; }; \
		$$binary $(SAMPLE_STATE) $(SAMPLE_STATE) >/dev/null 2>&1; \
		status=$$?; \
		test $$status -eq 2 || { \
			echo "$$binary with two arguments: expected status 2, got $$status"; \
			exit 1; }; \
		$$binary $(SAMPLE_STATE) >&- 2>/dev/null; \
		status=$$?; \
		test $$status -eq 1 || { \
			echo "$$binary with stdout closed: expected status 1, got $$status"; \
			exit 1; }; \
	done
	@./solver --self-test >&- 2>/dev/null; \
		status=$$?; \
		test $$status -eq 1 || { \
			echo "solver --self-test with stdout closed: expected 1, got $$status"; \
			exit 1; }
	@echo "invalid input rejected with status 2, unwritable stdout with status 1"

prove: solver.c
	@log=$$(mktemp); trap 'rm -f "$$log"' 0 1 2 15; \
		$(FRAMA_C) -wp -wp-fct quarter_turn,rank_state,valid,parse_state \
		-wp-rte -rte-verbose 0 -wp-prover alt-ergo -wp-timeout 20 \
		-wp-cache none solver.c >"$$log" 2>&1; rc=$$?; \
		grep -Fvx -e '[wp] Warning: Skipped RTE guards: unaligned pointers (\aligned not supported)' \
		-e '[wp] Warning: Skipped RTE guards: invalid function pointer calls (\valid_function not supported)' "$$log"; \
		test $$rc -eq 0 && awk '$$1 == "[wp]" && $$2 == "Proved" && $$3 == "goals:" && $$4 > 0 && $$4 == $$6 { ok = 1 } END { exit !ok }' "$$log" && \
		! grep -Eq '(^|[[:space:]])(Timeout|Unknown|Failed):' "$$log"

indent:
ifeq ($(CLANG_FORMAT),)
	$(error clang-format 20 not found)
endif
	@$(CLANG_FORMAT) --version | grep -q 'version 20' || \
		{ echo "error: clang-format version 20 required"; exit 1; }
	$(CLANG_FORMAT) -i $(C_SOURCES)

clean:
	$(RM) solver mini
