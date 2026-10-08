/* Independent Stage 1 benchmark, not linked into the cube solver.
 * Write every word of a fresh sparse guest region; repeated passes reuse it.
 * s0=status, s1=bytes, s2=passes, s3=words/pass, s4=base,
 * s5=passes remaining, s6=completed word stores, s8=stored value.
 */
#ifndef CAL_BYTES
#define CAL_BYTES 65536
#endif
#ifndef CAL_PASSES
#define CAL_PASSES 1
#endif
.if CAL_BYTES < 4 || CAL_BYTES % 4 != 0 || CAL_BYTES > 8388608
.error "Calibration requires a word-aligned region of 4 bytes to 8 MiB"
.endif
.if CAL_PASSES < 1 || CAL_PASSES > 512
.error "Calibration passes must be 1..512"
.endif
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    la t0, cube_calibration_parameters
    lw s1, 0(t0)
    lw s2, 4(t0)
    srli s3, s1, 2
    li s4, 0x100000
    mv s5, s2
    li s6, 0
    li s8, 0x12345678
.Lpass:
    mv t0, s4
    mv t1, s3
.Lword:
    sw s8, 0(t0)
    addi t0, t0, 4
    addi t1, t1, -1
    bnez t1, .Lword
    add s6, s6, s3
    addi s5, s5, -1
    bnez s5, .Lpass
    mv s9, t0
    lw s10, 0(s4)
    lw s11, -4(t0)
    li s0, 1
    bne s10, s8, .Lexit
    bne s11, s8, .Lexit
    li s0, 0
.Lexit:
    mv a0, s0
    li a7, 93
    ecall
.Lhalt:
    j .Lhalt
.size _start, .-_start

.section .rodata.calibration, "a", @progbits
.balign 4
.globl cube_calibration_parameters
.type cube_calibration_parameters, @object
cube_calibration_parameters:
    .4byte CAL_BYTES, CAL_PASSES
.size cube_calibration_parameters, .-cube_calibration_parameters

.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
