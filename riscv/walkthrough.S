/* Small instruction-level example: forwarded ALU result, store, load-use,
 * conditional branch, and architectural checks. Open in RV32_5S to clock
 * each instruction through IF/ID/EX/MEM/WB and inspect the named muxes.
 */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    la t0, walk_word
    li t1, 10
    addi t2, t1, 4
.globl walk_store
walk_store:
    sw t2, 0(t0)
.globl walk_load
walk_load:
    lw s1, 0(t0)
.globl walk_load_use
walk_load_use:
    add s2, s1, t2
    li t3, 28
    li s0, 1
    bne s2, t3, .Lexit
    li s0, 0
.Lexit:
    mv a0, s0
    li a7, 93
    ecall
.Lhalt:
    j .Lhalt
.size _start, .-_start
.section .bss.walk, "aw", @nobits
.balign 4
.globl walk_word
walk_word:
    .space 4
.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
