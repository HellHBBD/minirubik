/* A1: data-transfer smoke test. This entry is not the cube search yet.
 * Ripes services: a7=4 prints the string at a0; a7=10 terminates.
 * s0 records status (0=pass, 1=fail), copied to a0 before termination.
 */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    la t0, cube_permutation_turn
    la t1, cube_orientation_turn

    /* R(solved): independently ranked P=1104 and Q=426. */
    lhu t2, 0(t0)
    li t4, 1104
    bne t2, t4, .Lfail
    lhu t3, 0(t1)
    li t4, 426
    bne t3, t4, .Lfail

    /* Start from solved and apply four R quarter turns by table lookup. */
    li t2, 0
    li t3, 0
    li t6, 4
.Lturn:
    slli t4, t2, 1
    add t5, t0, t4
    lhu t2, 0(t5)
    slli t4, t3, 1
    add t5, t1, t4
    lhu t3, 0(t5)
    addi t6, t6, -1
    bnez t6, .Lturn
    bnez t2, .Lfail
    bnez t3, .Lfail

    la t0, cube_permutation_distance
    lbu t1, 0(t0)
    bnez t1, .Lfail
    la t0, cube_orientation_distance
    lbu t1, 0(t0)
    bnez t1, .Lfail
    la t0, cube_permutation_subset
    lbu t1, 0(t0)
    bnez t1, .Lfail
    la t0, cube_mixed_distance
    lbu t1, 0(t0)
    andi t1, t1, 15
    bnez t1, .Lfail

    li s0, 0
    la a0, .Lpass_message
    j .Lreport
.Lfail:
    li s0, 1
    la a0, .Lfail_message
.Lreport:
    li a7, 4
    ecall
    mv a0, s0
    li a7, 10
    ecall
.size _start, .-_start

.section .rodata.smoke, "a", @progbits
.Lpass_message:
    .asciz "RV32I tables ready\n"
.Lfail_message:
    .asciz "RV32I table check failed\n"

.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
