/* cube_apply_move(a0=P, a1=Q, a2=move 0..8) -> a0=P', a1=Q'.
 * Leaf: clobber a0, a1 and temporaries. Each call is one HTM move even
 * when one, two or three quarter-turn lookups are needed.
 */
.option norvc
.option norelax
.section .text.move, "ax", @progbits
.globl cube_apply_move
.type cube_apply_move, @function
cube_apply_move:
    mv t0, a2
    li t1, 0
    li t2, 3
.Lface:
    bltu t0, t2, .Ldecoded
    addi t0, t0, -3
    addi t1, t1, 1
    j .Lface
.Ldecoded:
    addi t0, t0, 1
    la t3, cube_permutation_turn
    la t4, cube_orientation_turn
    li t5, 10080
    li t6, 1458
    beqz t1, .Lturn
.Lrow:
    add t3, t3, t5
    add t4, t4, t6
    addi t1, t1, -1
    bnez t1, .Lrow
.Lturn:
    slli t1, a0, 1
    add t1, t3, t1
    lhu a0, 0(t1)
    slli t1, a1, 1
    add t1, t4, t1
    lhu a1, 0(t1)
    addi t0, t0, -1
    bnez t0, .Lturn
    ret
.size cube_apply_move, .-cube_apply_move
