/* cube_rank_state(a0=validated 14-byte state)
 * Return a0=P (0..5039), a1=Q (0..728). Clobber a0, a1, a2 and t0..t6;
 * preserve sp, ra and all callee-saved registers. Leaf, base RV32I only.
 * The first version multiplies the permutation prefix by repeated addition.
 */
.option norvc
.option norelax
.section .text.ranking, "ax", @progbits
.globl cube_rank_state
.type cube_rank_state, @function
cube_rank_state:
    mv t0, a0
    li t1, 0
    li t2, 0
.Lposition:
    add a2, t0, t2
    lbu t5, 0(a2)
    addi t3, t2, 1
    li t4, 0
.Lright:
    li t6, 7
    bgeu t3, t6, .Lcounted
    add a2, t0, t3
    lbu t6, 0(a2)
    bgeu t6, t5, .Lnext_right
    addi t4, t4, 1
.Lnext_right:
    addi t3, t3, 1
    j .Lright
.Lcounted:
    /* P = old_P * (7 - i) + number of smaller cubies to the right. */
    li t3, 7
    sub t3, t3, t2
    mv a2, t1
    li t1, 0
.Lmultiply:
    add t1, t1, a2
    addi t3, t3, -1
    bnez t3, .Lmultiply
    add t1, t1, t4
    addi t2, t2, 1
    li t3, 7
    bltu t2, t3, .Lposition

    /* Q uses six independent position orientations; o[6] was validated. */
    addi t0, t0, 7
    li a1, 0
    li t2, 6
.Ltwist:
    lbu t3, 0(t0)
    slli t4, a1, 1
    add a1, t4, a1
    add a1, a1, t3
    addi t0, t0, 1
    addi t2, t2, -1
    bnez t2, .Ltwist
    mv a0, t1
    ret
.size cube_rank_state, .-cube_rank_state
