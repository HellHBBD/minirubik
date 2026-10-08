/* All nine pairs in [0,2]^2; same harness, selected reduction sequence.
 * s0=verified pairs, s1=sum of reduced results, s2=status.
 */
#ifndef MOD_BRANCHLESS
#define MOD_BRANCHLESS 0
#endif
.option norvc
.option norelax
.section .text.entry, "ax", @progbits
.globl _start
.type _start, @function
_start:
    la sp, __stack_top
    la t0, .Lpairs
    li t1, 9
    li s0, 0
    li s1, 0
    li s2, 0
.Lpair:
    lbu t2, 0(t0)
    lbu t3, 1(t0)
    add t2, t2, t3
#if MOD_BRANCHLESS
    addi t4, t2, -3
    srai t5, t4, 31
    andi t5, t5, 3
    add t2, t4, t5
#else
    addi t4, t2, -3
    bltz t4, .Lreduced
    mv t2, t4
.Lreduced:
#endif
    lbu t3, 2(t0)
    bne t2, t3, .Lfail
    add s1, s1, t2
    addi s0, s0, 1
    addi t0, t0, 3
    addi t1, t1, -1
    bnez t1, .Lpair
    j .Lexit
.Lfail:
    li s2, 1
.Lexit:
    mv a0, s2
    li a7, 93
    ecall
.Lhalt:
    j .Lhalt
.size _start, .-_start
.section .rodata.modulo, "a", @progbits
.Lpairs:
    .byte 0,0,0, 0,1,1, 0,2,2, 1,0,1, 1,1,2, 1,2,0, 2,0,2, 2,1,0, 2,2,1
.section .bss.stack, "aw", @nobits
.balign 16
    .space 1024
.globl __stack_top
__stack_top:
