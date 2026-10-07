/* cube_parse_state(a0=input, a1=14-byte output state)
 * Output: seven cubie bytes followed by seven orientation bytes, all 0-based.
 * Return a0=0 for valid input, a0=2 for invalid input. Partial output on failure
 * is not used. Leaf function: only a0 and t0..t6 are clobbered; sp, ra and all
 * callee-saved registers are preserved. input must be NUL-terminated.
 */
.option norvc
.option norelax
.section .text.parser, "ax", @progbits
.globl cube_parse_state
.type cube_parse_state, @function
cube_parse_state:
    mv t0, a0
    mv t1, a1
    li t2, 7
    li t3, 0
.Lpermutation:
    lbu t4, 0(t0)
    addi t4, t4, -49
    li t5, 7
    /* Unsigned comparison rejects values below '1' as well as above '7'. */
    bgeu t4, t5, .Linvalid
    li t5, 1
    sll t5, t5, t4
    and t6, t3, t5
    bnez t6, .Linvalid
    or t3, t3, t5
    sb t4, 0(t1)
    addi t0, t0, 1
    addi t1, t1, 1
    addi t2, t2, -1
    bnez t2, .Lpermutation

    /* Seven unique values in 0..6 already form a complete permutation. */
    li t2, 7
    li t3, 0
.Lorientation:
    lbu t4, 0(t0)
    addi t4, t4, -49
    li t5, 3
    bgeu t4, t5, .Linvalid
    sb t4, 0(t1)
    add t3, t3, t4
    addi t0, t0, 1
    addi t1, t1, 1
    addi t2, t2, -1
    bnez t2, .Lorientation

    /* t0 now points at input[14]. Short inputs failed a range check earlier. */
    lbu t4, 0(t0)
    bnez t4, .Linvalid
    li t5, 3
.Lmodulo:
    bltu t3, t5, .Lremainder
    addi t3, t3, -3
    j .Lmodulo
.Lremainder:
    bnez t3, .Linvalid
    li a0, 0
    ret
.Linvalid:
    li a0, 2
    ret
.size cube_parse_state, .-cube_parse_state
