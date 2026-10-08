/* cube_print_path(a0=validated path, a1=length): space-separated HTM tokens
 * and one newline, including an empty line for solved. Ripes print-string
 * service is a7=4. Preserve sp and all callee-saved registers.
 */
.option norvc
.option norelax
.section .text.output, "ax", @progbits
.globl cube_print_path
.type cube_print_path, @function
cube_print_path:
    addi sp, sp, -16
    sw s0, 0(sp)
    sw s1, 4(sp)
    sw s2, 8(sp)
    mv s0, a0
    mv s1, a1
    li s2, 0
.Ltoken:
    beq s2, s1, .Lnewline
    beqz s2, .Lmove
    la a0, .Lspace
    li a7, 4
    ecall
.Lmove:
    lbu t0, 0(s0)
    slli t0, t0, 2
    la a0, cube_move_tokens
    add a0, a0, t0
    li a7, 4
    ecall
    addi s0, s0, 1
    addi s2, s2, 1
    j .Ltoken
.Lnewline:
    la a0, .Lnewline_string
    li a7, 4
    ecall
    lw s0, 0(sp)
    lw s1, 4(sp)
    lw s2, 8(sp)
    addi sp, sp, 16
    ret
.size cube_print_path, .-cube_print_path

.section .rodata.output, "a", @progbits
.globl cube_move_tokens
.type cube_move_tokens, @object
cube_move_tokens:
    .ascii "R\0\0\0R2\0\0R'\0\0B\0\0\0B2\0\0B'\0\0D\0\0\0D2\0\0D'\0\0"
.size cube_move_tokens, .-cube_move_tokens
.Lspace:
    .asciz " "
.Lnewline_string:
    .asciz "\n"
