/* Replace this object to supply a different external input. */
.section .rodata.cube_input, "a", @progbits
.globl cube_input
.type cube_input, @object
cube_input:
    .asciz "12345671111111"
.size cube_input, .-cube_input
