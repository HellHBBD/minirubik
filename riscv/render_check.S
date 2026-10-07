/* Test-only RAM framebuffer validator. gp counts verified frames; tp=status.
 * Compare every RGB word with independent geometric fixtures and guard both
 * ends. The production GUI renderer never reads the expected-frame data.
 */
.option norvc
.option norelax
.section .text.render_check, "ax", @progbits
.globl cube_render_test_init
.type cube_render_test_init, @function
cube_render_test_init:
    li gp, 0
    li tp, 0
    li t0, 0xa5a5a5a5
    la t1, cube_render_test_before
    sw t0, 0(t1)
    la t1, cube_render_test_after
    sw t0, 0(t1)
    ret
.size cube_render_test_init, .-cube_render_test_init

.globl cube_render_check_frame
.type cube_render_check_frame, @function
cube_render_check_frame:
    la t0, cube_render_expected_count
    lw t0, 0(t0)
    bgeu gp, t0, .Lfailure
    la t0, cube_render_expected
    mv t1, gp
    li t2, 3500
    beqz t1, .Lcompare
.Loffset:
    add t0, t0, t2
    addi t1, t1, -1
    bnez t1, .Loffset
.Lcompare:
    la t1, cube_render_test_framebuffer
    li t2, 875
.Lword:
    lw t3, 0(t0)
    lw t4, 0(t1)
    bne t3, t4, .Lfailure
    addi t0, t0, 4
    addi t1, t1, 4
    addi t2, t2, -1
    bnez t2, .Lword
    li t0, 0xa5a5a5a5
    la t1, cube_render_test_before
    lw t1, 0(t1)
    bne t0, t1, .Lfailure
    la t1, cube_render_test_after
    lw t1, 0(t1)
    bne t0, t1, .Lfailure
    addi gp, gp, 1
    ret
.Lfailure:
    li tp, 1
    li a0, 1
    li a7, 93
    ecall
.Lhalt:
    j .Lhalt
.size cube_render_check_frame, .-cube_render_check_frame

.section .bss.render_test, "aw", @nobits
.balign 4
cube_render_test_before:
    .space 4
.globl cube_render_test_framebuffer
cube_render_test_framebuffer:
    .space 3500
cube_render_test_after:
    .space 4
