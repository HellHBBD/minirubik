/* All P at Q=0, then every mixed subset row at all Q. */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    li s0, 0
    li s1, 0
    li s2, 0
    li s3, 0
    li s5, 0
    li s7, 0
    la s4, cube_heuristic_expected
.Lcase:
    mv a0, s1
    mv a1, s2
    jal ra, cube_heuristic
    lbu t0, 0(s4)
    bne a0, t0, .Lfail
    addi s0, s0, 1
    addi s4, s4, 1
    bnez s3, .Lmixed
    addi s1, s1, 1
    li t0, 5040
    bltu s1, t0, .Lcase
    li s3, 1
    la s6, cube_heuristic_representatives
    lhu s1, 0(s6)
    j .Lcase
.Lmixed:
    addi s2, s2, 1
    li t0, 729
    bltu s2, t0, .Lcase
    li s2, 0
    addi s6, s6, 2
    addi s7, s7, 1
    li t0, 35
    bgeu s7, t0, .Ldone
    lhu s1, 0(s6)
    j .Lcase
.Ldone:
    la a0, .Lpass_message
    j .Lreport
.Lfail:
    li s5, 1
    la a0, .Lfail_message
.Lreport:
    li a7, 4
    ecall
    mv a0, s5
    li a7, 10
    ecall
.size _start, .-_start
.section .rodata.heuristic_messages, "a", @progbits
.Lpass_message:
    .asciz "RV32I heuristics verified\n"
.Lfail_message:
    .asciz "RV32I heuristic check failed\n"
.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
