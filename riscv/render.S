/* Assemble-time optional renderer. Each actual HTM path move updates the
 * logical cubies, then rebuilds 24 facelets and redraws the unfolded net.
 * U / L F R B / D; each facelet 4x3 pixels; row-major RGB word stores.
 */
#ifndef RENDER
#define RENDER 0
#endif
#ifndef RENDER_TEST
#define RENDER_TEST 0
#endif
#ifndef RENDER_DELAY
#define RENDER_DELAY 50000
#endif
#if RENDER
#include LED_SYMBOLS
.if LED_MATRIX_0_WIDTH != 35 || LED_MATRIX_0_HEIGHT != 25
.error "Cube net requires an LED Matrix of width 35 and height 25"
.endif
.option norvc
.option norelax
.section .text.render, "ax", @progbits
.globl cube_render
.type cube_render, @function
cube_render:
    addi sp, sp, -16
    sw s0, 0(sp)
    sw s1, 4(sp)
    sw s2, 8(sp)
    sw ra, 12(sp)
    la s0, LED_MATRIX_0_BASE
    mv t0, s0
    li t1, LED_MATRIX_0_WIDTH*LED_MATRIX_0_HEIGHT
.Lclear:
    sw zero, 0(t0)
    addi t0, t0, 4
    addi t1, t1, -1
    bnez t1, .Lclear
    jal ra, cube_build_facelets
    li s1, 0
.Lfacelet:
    la t0, cube_render_facelets
    add t0, t0, s1
    lbu t0, 0(t0)
    slli t0, t0, 2
    la t1, cube_palette
    add t1, t1, t0
    lw s2, 0(t1)
    slli t0, s1, 2
    la t1, cube_led_offsets
    add t1, t1, t0
    lw t0, 0(t1)
    add t0, s0, t0
    li t1, 3
.Lpixel_row:
    li t2, 4
.Lpixel:
    sw s2, 0(t0)
    addi t0, t0, 4
    addi t2, t2, -1
    bnez t2, .Lpixel
    addi t0, t0, 4*LED_MATRIX_0_WIDTH-16
    addi t1, t1, -1
    bnez t1, .Lpixel_row
    addi s1, s1, 1
    li t0, 24
    bltu s1, t0, .Lfacelet
#if RENDER_TEST
    jal ra, cube_render_check_frame
#endif
.globl cube_frame_ready
.type cube_frame_ready, @notype
cube_frame_ready:
    nop
#if RENDER_DELAY > 0
    li t0, RENDER_DELAY
.Ldelay:
    addi t0, t0, -1
    bnez t0, .Ldelay
#endif
    lw s0, 0(sp)
    lw s1, 4(sp)
    lw s2, 8(sp)
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
.size cube_render, .-cube_render

/* Each corner's three facelets take color[j+orientation mod 3]. */
.type cube_build_facelets, @function
cube_build_facelets:
    li t0, 0
    la t1, cube_state
    la t2, cube_corner_facelets
    la t3, cube_corner_colors
    la t4, cube_render_facelets
.Lcorner:
    li t5, 7
    beq t0, t5, .Lfixed
    add t5, t1, t0
    lbu a0, 0(t5)
    lbu a1, 7(t5)
    j .Lcorner_ready
.Lfixed:
    li a0, 7
    li a1, 0
.Lcorner_ready:
    slli t5, a0, 1
    add t5, t5, a0
    add a0, t3, t5
    li a2, 0
.Lsticker:
    add a3, a2, a1
    addi t5, a3, -3
    bltz t5, .Lindex_ready
    mv a3, t5
.Lindex_ready:
    add t5, a0, a3
    lbu t5, 0(t5)
    lbu t6, 0(t2)
    add t6, t4, t6
    sb t5, 0(t6)
    addi t2, t2, 1
    addi a2, a2, 1
    li t5, 3
    bltu a2, t5, .Lsticker
    addi t0, t0, 1
    li t5, 8
    bltu t0, t5, .Lcorner
    ret
.size cube_build_facelets, .-cube_build_facelets

.globl cube_render_step
.type cube_render_step, @function
cube_render_step:
    addi sp, sp, -16
    sw s0, 0(sp)
    sw s1, 4(sp)
    sw ra, 12(sp)
    li s0, 0
    mv s1, a0
    li t0, 3
.Ldecode:
    bltu s1, t0, .Ldecoded
    addi s1, s1, -3
    addi s0, s0, 1
    j .Ldecode
.Ldecoded:
    addi s1, s1, 1
.Lquarter:
    mv a0, s0
    jal ra, cube_render_turn
    addi s1, s1, -1
    bnez s1, .Lquarter
    jal ra, cube_render
    lw s0, 0(sp)
    lw s1, 4(sp)
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
.size cube_render_step, .-cube_render_step

.type cube_render_turn, @function
cube_render_turn:
    slli t0, a0, 3
    sub t0, t0, a0
    la t1, cube_render_source
    add t1, t1, t0
    la t2, cube_render_twist
    add t2, t2, t0
    la t3, cube_state
    la t4, cube_render_scratch
    li t0, 7
.Ltransform:
    lbu t5, 0(t1)
    add t5, t3, t5
    lbu t6, 0(t5)
    sb t6, 0(t4)
    lbu t6, 7(t5)
    lbu a1, 0(t2)
    add t6, t6, a1
    addi a1, t6, -3
    bltz a1, .Lorientation_ready
    mv t6, a1
.Lorientation_ready:
    sb t6, 7(t4)
    addi t1, t1, 1
    addi t2, t2, 1
    addi t4, t4, 1
    addi t0, t0, -1
    bnez t0, .Ltransform
    la t0, cube_render_scratch
    li t1, 14
.Lcopy:
    lbu t2, 0(t0)
    sb t2, 0(t3)
    addi t0, t0, 1
    addi t3, t3, 1
    addi t1, t1, -1
    bnez t1, .Lcopy
    ret
.size cube_render_turn, .-cube_render_turn

#include RENDER_TABLES
.section .bss.renderer, "aw", @nobits
.globl cube_render_facelets
cube_render_facelets:
    .space 24
cube_render_scratch:
    .space 14
#endif
