/* Rank-only batch kernel. Each readonly fixture is state[14], P:u16, Q:u16.
 * s0 counts completed records; s1 is the cursor; s2 is the total; s3 is status.
 * The shared rank function must preserve these callee-saved registers.
 */
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    li s0, 0
    li s3, 0
    la s1, cube_rank_cases
    la t0, cube_rank_case_count
    lw s2, 0(t0)
.Lcase:
    mv a0, s1
    jal ra, cube_rank_state
    lhu t0, 14(s1)
    bne a0, t0, .Lfail
    lhu t0, 16(s1)
    bne a1, t0, .Lfail
    addi s0, s0, 1
    addi s1, s1, 18
    bltu s0, s2, .Lcase
    la a0, .Lpass_message
    j .Lreport
.Lfail:
    li s3, 1
    la a0, .Lfail_message
.Lreport:
    li a7, 4
    ecall
    mv a0, s3
    li a7, 10
    ecall
.Lhalt:
    j .Lhalt
.size _start, .-_start

.section .rodata.rank_messages, "a", @progbits
.Lpass_message:
    .asciz "RV32I ranks verified\n"
.Lfail_message:
    .asciz "RV32I rank check failed\n"

.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
