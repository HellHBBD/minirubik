/* GCC reference: compile the final solver's actual C query functions.
 * The target mode excludes hosted builders/oracles and lowers bounded
 * arithmetic without compiler runtime helpers. Startup, output and replay
 * harness are shared with the hand-written image for comparable counts.
 */
#define CUBE_RV32I_REFERENCE 1
#include "../solver.c"

int cube_parse_state(const char *input, state_t *state)
{
    return parse_state(input, state) ? 0 : 2;
}

uint32_t cube_rank_packed(const state_t *state)
{
    return rank_state(state);
}

unsigned cube_heuristic(uint16_t p, uint16_t q)
{
    return query_heuristic(p, q);
}

uint32_t cube_move_packed(uint16_t p, uint16_t q, uint8_t move)
{
    uint8_t face = move >= 6 ? 2 : move >= 3 ? 1 : 0;
    uint8_t turns = (uint8_t) (move - 3U * face + 1U);
    for (uint8_t i = 0; i < turns; ++i) {
        p = query_tables.permutation[face][p];
        q = query_tables.orientation[face][q];
    }
    return p | ((uint32_t) q << 16);
}

int cube_solve(uint16_t p, uint16_t q, uint8_t path[MAX_DEPTH])
{
    return solve_coordinate(p, q, path, NULL);
}
