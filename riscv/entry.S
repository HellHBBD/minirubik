/* A4: table-transfer, parsing, ranking and heuristic checkpoint.
 * Ripes services: a7=4 prints the string at a0; a7=10 terminates.
 * s0 records status (0=valid, 1=checkpoint failure, 2=invalid input).
 * s1/s2 expose parsed bytes as fixed-width base-8/base-4 fingerprints;
 * these diagnostics are not the Lehmer P or base-3 Q coordinates.
 * s3/s4 expose the actual P/Q coordinates after a successful parse.
 * s5 exposes the admissible heuristic.
 */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    li s1, 0
    li s2, 0
    li s3, 0
    li s4, 0
    li s5, 0
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

    la a0, cube_input
    la a1, cube_state
    jal ra, cube_parse_state
    mv s0, a0
    bnez a0, .Linvalid_input

    /* Expose all fourteen parsed bytes for the host checker. */
    la t0, cube_state
    li t1, 7
.Lfingerprint:
    lbu t2, 0(t0)
    li t4, 7
    bgeu t2, t4, .Lfail
    slli s1, s1, 3
    or s1, s1, t2
    lbu t3, 7(t0)
    li t4, 3
    bgeu t3, t4, .Lfail
    slli s2, s2, 2
    or s2, s2, t3
    addi t0, t0, 1
    addi t1, t1, -1
    bnez t1, .Lfingerprint
    la a0, cube_state
    jal ra, cube_rank_state
    mv s3, a0
    mv s4, a1
    li t0, 5040
    bgeu s3, t0, .Lfail
    li t0, 729
    bgeu s4, t0, .Lfail
    mv a0, s3
    mv a1, s4
    jal ra, cube_heuristic
    mv s5, a0
    la a0, .Lpass_message
    j .Lreport
.Linvalid_input:
    la a0, .Linvalid_message
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
    .asciz "RV32I input valid\n"
.Linvalid_message:
    .asciz "RV32I input invalid\n"
.Lfail_message:
    .asciz "RV32I checkpoint failed\n"

.section .bss.cube_state, "aw", @nobits
.balign 4
.globl cube_state
.type cube_state, @object
cube_state:
    .space 14
.size cube_state, .-cube_state

.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
