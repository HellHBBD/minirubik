/* cube_replay(a0=P, a1=Q, a2=path, a3=length) validates and applies a path.
 * Return a0=0 only if solved, otherwise 1; a1/a2=final P/Q and a3=number
 * of applied moves. Reject out-of-domain coordinates, length >11 and moves
 * >=9 before indexing. Preserve all callee-saved registers and sp.
 */
.option norvc
.option norelax
.section .text.replay, "ax", @progbits
.globl cube_replay
.type cube_replay, @function
cube_replay:
#if RENDER
    addi sp, sp, -32
#else
    addi sp, sp, -16
#endif
    sw s0, 0(sp)
    sw s1, 4(sp)
    sw s2, 8(sp)
    sw ra, 12(sp)
    mv s0, a2
    mv s1, a3
    li s2, 0
    li t0, 11
    bltu t0, s1, .Lfail
.Lnext:
    li t0, 5040
    bgeu a0, t0, .Lfail
    li t0, 729
    bgeu a1, t0, .Lfail
    beq s2, s1, .Ldone
    lbu a2, 0(s0)
    li t0, 9
    bgeu a2, t0, .Lfail
    jal ra, cube_apply_move
#if RENDER
    sw a0, 16(sp)
    sw a1, 20(sp)
    lbu a0, 0(s0)
    jal ra, cube_render_step
    lw a0, 16(sp)
    lw a1, 20(sp)
#endif
    addi s0, s0, 1
    addi s2, s2, 1
    j .Lnext
.Ldone:
    or t0, a0, a1
    snez t1, t0
#if RENDER
    /* Independently require the displayed logical cubies to be solved. */
    la t0, cube_state
    li t3, 0
.Lrender_solved:
    lbu t4, 0(t0)
    bne t4, t3, .Lfail
    lbu t4, 7(t0)
    bnez t4, .Lfail
    addi t0, t0, 1
    addi t3, t3, 1
    li t4, 7
    bltu t3, t4, .Lrender_solved
#endif
    j .Lreturn
.Lfail:
    li t1, 1
.Lreturn:
    mv a2, a1
    mv a1, a0
    mv a0, t1
    mv a3, s2
    lw s0, 0(sp)
    lw s1, 4(sp)
    lw s2, 8(sp)
    lw ra, 12(sp)
#if RENDER
    addi sp, sp, 32
#else
    addi sp, sp, 16
#endif
    ret
.size cube_replay, .-cube_replay
