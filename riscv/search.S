/* cube_solve(a0=P, a1=Q, a2=11-byte path) -> a0=length, or -1.
 * Explicit frames: p:u16 at 0, q:u16 at 2, previous_face:u8 at 4,
 * next_move:u8 at 5. Twelve frames, root sentinel face 3.
 * s0=bound, s1=depth, s2=frames, s3=path, s4/s5=root,
 * s6/s7=child, s8=move, s9=face, s10=current frame.
 * One 64-byte ABI frame protects nonrecursive calls to move/heuristic.
 */
.option norvc
.option norelax
.section .text.search, "ax", @progbits
.globl cube_solve
.type cube_solve, @function
cube_solve:
    addi sp, sp, -64
    sw ra, 60(sp)
    sw s0, 56(sp)
    sw s1, 52(sp)
    sw s2, 48(sp)
    sw s3, 44(sp)
    sw s4, 40(sp)
    sw s5, 36(sp)
    sw s6, 32(sp)
    sw s7, 28(sp)
    sw s8, 24(sp)
    sw s9, 20(sp)
    sw s10, 16(sp)
    mv s4, a0
    mv s5, a1
    mv s3, a2
    la s2, cube_frames
    jal ra, cube_heuristic
    mv s0, a0
.Lbound:
    li t0, 11
    bltu t0, s0, .Lfailed
    li s1, 0
    sh s4, 0(s2)
    sh s5, 2(s2)
    li t0, 3
    sb t0, 4(s2)
    sb zero, 5(s2)
.Lframe:
    mv s10, s2
    mv t0, s1
    beqz t0, .Llocated
.Loffset:
    addi s10, s10, 6
    addi t0, t0, -1
    bnez t0, .Loffset
.Llocated:
    lhu t0, 0(s10)
    lhu t1, 2(s10)
    or t2, t0, t1
    beqz t2, .Lsolved
    beq s1, s0, .Lbacktrack
    lbu s8, 5(s10)
    li t0, 9
    bgeu s8, t0, .Lbacktrack
    addi t0, s8, 1
    sb t0, 5(s10)
    mv t1, s8
    li s9, 0
    li t0, 3
.Lface:
    bltu t1, t0, .Lface_ready
    addi t1, t1, -3
    addi s9, s9, 1
    j .Lface
.Lface_ready:
    lbu t0, 4(s10)
    beq t0, s9, .Lframe
    lhu a0, 0(s10)
    lhu a1, 2(s10)
    mv a2, s8
    jal ra, cube_apply_move
    mv s6, a0
    mv s7, a1
    jal ra, cube_heuristic
    addi t0, s1, 1
    add t0, t0, a0
    bltu s0, t0, .Lframe
    add t0, s3, s1
    sb s8, 0(t0)
    addi t0, s10, 6
    sh s6, 0(t0)
    sh s7, 2(t0)
    sb s9, 4(t0)
    sb zero, 5(t0)
    addi s1, s1, 1
    j .Lframe
.Lbacktrack:
    beqz s1, .Lexhausted
    addi s1, s1, -1
    j .Lframe
.Lexhausted:
    addi s0, s0, 1
    j .Lbound
.Lsolved:
    mv a0, s1
    j .Lreturn
.Lfailed:
    li a0, -1
.Lreturn:
    lw ra, 60(sp)
    lw s0, 56(sp)
    lw s1, 52(sp)
    lw s2, 48(sp)
    lw s3, 44(sp)
    lw s4, 40(sp)
    lw s5, 36(sp)
    lw s6, 32(sp)
    lw s7, 28(sp)
    lw s8, 24(sp)
    lw s9, 20(sp)
    lw s10, 16(sp)
    addi sp, sp, 64
    ret
.size cube_solve, .-cube_solve
.section .bss.frames, "aw", @nobits
.balign 2
.globl cube_frames
.type cube_frames, @object
cube_frames:
    .space 72
.size cube_frames, .-cube_frames
