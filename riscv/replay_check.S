/* Exercise replay rejection paths independently of cube_solve and entry.
 * Record: P/Q:u16, length/status/count/pad:u8, final P/Q:u16, path[12].
 * s0=completed, s1=cursor, s2=count; s3..s11 are ABI canaries.
 */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    li s0, 0
    la s1, cube_replay_cases
    li s2, 12
    li s3, 103
    li s4, 104
    li s5, 105
    li s6, 106
    li s7, 107
    li s8, 108
    li s9, 109
    li s10, 110
    li s11, 111
.Lcase:
    lhu a0, 0(s1)
    lhu a1, 2(s1)
    addi a2, s1, 12
    lbu a3, 4(s1)
    jal ra, cube_replay
    lbu t0, 5(s1)
    bne a0, t0, .Lfail
    lhu t0, 8(s1)
    bne a1, t0, .Lfail
    lhu t0, 10(s1)
    bne a2, t0, .Lfail
    lbu t0, 6(s1)
    bne a3, t0, .Lfail
    addi s0, s0, 1
    addi s1, s1, 24
    bltu s0, s2, .Lcase
    la a0, .Lpass
    li a7, 4
    ecall
    li a0, 0
    j .Lexit
.Lfail:
    la a0, .Lfailure
    li a7, 4
    ecall
    li a0, 1
.Lexit:
    li a7, 93
    ecall
.Lhalt:
    j .Lhalt
.size _start, .-_start

.section .rodata.replay_cases, "a", @progbits
.balign 2
.globl cube_replay_cases
.type cube_replay_cases, @object
cube_replay_cases:
    /* Solved, inverse R, and four R quarter turns. */
    .2byte 0,0
    .byte 0,0,0,0
    .2byte 0,0
    .zero 12
    .2byte 1104,426
    .byte 1,0,1,0
    .2byte 0,0
    .byte 2
    .zero 11
    .2byte 0,0
    .byte 4,0,4,0
    .2byte 0,0
    .zero 12
    /* Valid but unsolved paths must fail, including an empty path. */
    .2byte 0,0
    .byte 1,1,1,0
    .2byte 1104,426
    .zero 12
    .2byte 1104,426
    .byte 0,1,0,0
    .2byte 1104,426
    .zero 12
    /* Invalid moves: first move, high byte, and after one valid move. */
    .2byte 0,0
    .byte 1,1,0,0
    .2byte 0,0
    .byte 9
    .zero 11
    .2byte 0,0
    .byte 1,1,0,0
    .2byte 0,0
    .byte 255
    .zero 11
    .2byte 0,0
    .byte 2,1,1,0
    .2byte 1104,426
    .byte 0,9
    .zero 10
    /* Excessive lengths must fail before any path read. */
    .2byte 0,0
    .byte 12,1,0,0
    .2byte 0,0
    .zero 12
    .2byte 0,0
    .byte 255,1,0,0
    .2byte 0,0
    .zero 12
    /* Out-of-domain coordinates must fail before table access. */
    .2byte 5040,0
    .byte 1,1,0,0
    .2byte 5040,0
    .zero 12
    .2byte 0,729
    .byte 1,1,0,0
    .2byte 0,729
    .zero 12
.size cube_replay_cases, .-cube_replay_cases
.Lpass:
    .asciz "RV32I replay cases verified\n"
.Lfailure:
    .asciz "RV32I replay cases failed\n"

.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
