/* Short GUI demonstration: R(solved), with the actual solution R'.
 * Select another arbitrary 14-character cube with RV_GUI_INPUT=/path/input.S.
 */
.section .rodata.cube_input, "a", @progbits
.globl cube_input
.type cube_input, @object
cube_input:
    .asciz "25314672313211"
.size cube_input, .-cube_input
