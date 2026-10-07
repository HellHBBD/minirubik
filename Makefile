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
RV_PROC ?= RV32_SS
PYTHON ?= python3
CLANG_FORMAT := $(shell command -v clang-format-20 2>/dev/null || \
	command -v clang-format 2>/dev/null)
C_SOURCES := $(wildcard *.c *.h)
SAMPLE_STATE := 21345671111111
SAMPLE_SOLUTION := B' R' D2 R' B R B' R D2 B R'
VECTORS := tests/solutions.txt
# One per rejection path: short, long, cubie digit low, cubie digit high,
# orientation digit low, orientation digit high, non-digit, duplicate, parity.
INVALID_STATES := 1234567111111 123456711111111 02345671111111 82345671111111 \
	12345671111110 12345671111114 1234567111111a 11345671111111 12345671111112

.PHONY: all check prove clean indent rv32i rv32i-smoke rv32i-input-check clean-rv32i force-rv-input

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

$(RV_BUILD)/entry.o: riscv/entry.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/parse.o: riscv/parse.S | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

force-rv-input:

$(RV_BUILD)/input.o: $(RV_INPUT) force-rv-input | $(RV_BUILD)
	$(RV_CC) $(RV_ASFLAGS) -c "$<" -o "$@"

$(RV_BUILD)/smoke.debug.elf: $(RV_BUILD)/entry.o $(RV_BUILD)/parse.o $(RV_BUILD)/tables.o $(RV_BUILD)/input.o riscv/link.ld
	$(RV_LD) -m elf32lriscv --no-relax -T riscv/link.ld -o "$@" \
		$(RV_BUILD)/entry.o $(RV_BUILD)/parse.o $(RV_BUILD)/tables.o $(RV_BUILD)/input.o

$(RV_BUILD)/smoke.elf: $(RV_BUILD)/smoke.debug.elf
	$(RV_OBJCOPY) --strip-all --remove-section=.riscv.attributes "$<" "$@"

rv32i-smoke: $(RV_BUILD)/smoke.elf
	$(PYTHON) riscv/check_smoke.py "$(RIPES)" "$<" "$(RV_PROC)"

rv32i-input-check: $(RV_BUILD)/smoke.elf
	$(PYTHON) riscv/check_inputs.py --ripes "$(RIPES)" \
		--build "$(RV_BUILD)" --processor "$(RV_PROC)" --input "$(RV_INPUT)"

clean-rv32i:
	$(RM) "$(RV_BUILD)/tables.S" "$(RV_BUILD)/tables.o" \
		"$(RV_BUILD)/entry.o" "$(RV_BUILD)/parse.o" "$(RV_BUILD)/input.o" \
		"$(RV_BUILD)/smoke.debug.elf" "$(RV_BUILD)/smoke.elf" \
		"$(RV_BUILD)/smoke.report.json"

check: solver mini $(VECTORS)
	./solver --self-test
	@expected=$$(mktemp); actual=$$(mktemp); \
		trap 'rm -f "$$expected" "$$actual"' 0 1 2 15; \
		count=0; \
		while IFS='|' read -r state solution; do \
			case "$$state" in ""|\#*) continue ;; esac; \
			printf '%s\n' "$$solution" >"$$expected"; \
			for binary in ./solver ./mini; do \
				$$binary "$$state" >"$$actual"; \
				status=$$?; \
				test $$status -eq 0 || { \
					echo "$$binary $$state: exit status $$status"; exit 1; }; \
				cmp -s "$$actual" "$$expected" || { \
					echo "$$binary $$state: output mismatch"; \
					echo "  expected: $$solution"; \
					printf '  got:      '; cat "$$actual"; \
					echo "  ($$(wc -c <"$$expected") bytes expected, \
$$(wc -c <"$$actual") produced)"; exit 1; }; \
			done; \
			count=$$((count + 1)); \
		done <$(VECTORS); \
		echo "$$count solution vectors matched by solver and mini"
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
