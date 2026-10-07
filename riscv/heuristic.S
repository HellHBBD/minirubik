/* cube_heuristic(a0=P, a1=Q) -> a0=max(dP,dQ,mixed).
 * Preconditions: P<5040, Q<729. Clobber a0 and t0..t6; preserve a1, sp,
 * ra and all callee-saved registers. Repeated addition is the baseline
 * implementation of subset*729; table bases are loaded on each call.
 */
.option norvc
.option norelax
.section .text.heuristic, "ax", @progbits
.globl cube_heuristic
.type cube_heuristic, @function
cube_heuristic:
    la t0, cube_permutation_distance
    add t0, t0, a0
    lbu t1, 0(t0)
    la t0, cube_orientation_distance
    add t0, t0, a1
    lbu t2, 0(t0)
    bgeu t1, t2, .Lbasic
    mv t1, t2
.Lbasic:
    la t0, cube_permutation_subset
    add t0, t0, a0
    lbu t3, 0(t0)
    mv t4, a1
    li t5, 729
    beqz t3, .Lindexed
.Lmultiply:
    add t4, t4, t5
    addi t3, t3, -1
    bnez t3, .Lmultiply
.Lindexed:
    andi t5, t4, 1
    slli t5, t5, 2
    srli t4, t4, 1
    la t6, cube_mixed_distance
    add t6, t6, t4
    lbu t3, 0(t6)
    srl t3, t3, t5
    andi t3, t3, 15
    bgeu t1, t3, .Lresult
    mv t1, t3
.Lresult:
    mv a0, t1
    ret
.size cube_heuristic, .-cube_heuristic
