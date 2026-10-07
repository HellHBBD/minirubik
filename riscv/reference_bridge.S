/* C returns the coordinate pair in one word; match the existing a0/a1 ABI.
 * These wrappers contain no solver logic and are included in reference size.
 */
.option norvc
.option norelax
.macro coordinate_bridge name, callee
.section .text.\name, "ax", @progbits
.globl \name
.type \name, @function
\name:
    addi sp, sp, -16
    sw ra, 12(sp)
    jal ra, \callee
    srli a1, a0, 16
    slli a0, a0, 16
    srli a0, a0, 16
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
.size \name, .-\name
.endm
coordinate_bridge cube_rank_state, cube_rank_packed
coordinate_bridge cube_apply_move, cube_move_packed
