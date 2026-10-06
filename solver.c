#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    CUBIES = 7,
    PERMUTATIONS = 5040,
    ORIENTATIONS = 729,
    STATES = PERMUTATIONS * ORIENTATIONS,
    MOVES = 9,
    MAX_DEPTH = 11,
    HARDEST_STATES = 2644
};

typedef struct {
    uint8_t p[CUBIES], o[CUBIES];
} state_t;

/*@ predicate valid_state(state_t *state) =
      (\forall integer i; 0 <= i < CUBIES ==>
         state->p[i] < CUBIES && state->o[i] < 3) &&
      (\forall integer i, j; 0 <= i < j < CUBIES ==>
         state->p[i] != state->p[j]) &&
      (state->o[0] + state->o[1] + state->o[2] + state->o[3] +
       state->o[4] + state->o[5] + state->o[6]) % 3 == 0;
 */

static const char *const move_names[MOVES] = {"R",  "R2", "R'", "B", "B2",
                                              "B'", "D",  "D2", "D'"};
static const uint8_t inverse_move[MOVES] = {2, 1, 0, 5, 4, 3, 8, 7, 6};
/* Each destination takes a cubie from source[face][destination]. */
static const uint8_t source[3][CUBIES] = {
    {1, 4, 2, 0, 3, 5, 6},
    {0, 1, 2, 4, 5, 6, 3},
    {0, 2, 5, 3, 1, 4, 6},
};
static const uint8_t twist[3][CUBIES] = {
    {1, 2, 0, 2, 1, 0, 0},
    {0, 0, 0, 1, 2, 1, 2},
    {0, 0, 0, 0, 0, 0, 0},
};

/* The three quarter-turns preserve the fixed front-upper-left corner. */
/*@ requires face < 3;
    assigns \nothing;
    ensures \forall integer i; 0 <= i < CUBIES ==>
              \result.p[i] == state.p[source[face][i]];
    ensures \forall integer i; 0 <= i < CUBIES ==>
              \result.o[i] == (state.o[source[face][i]] + twist[face][i]) % 3;
 */
static state_t quarter_turn(state_t state, uint8_t face)
{
    state_t result;
    /*@ loop invariant 0 <= i <= CUBIES;
        loop invariant \forall integer j; 0 <= j < i ==>
          result.p[j] == state.p[source[face][j]];
        loop invariant \forall integer j; 0 <= j < i ==>
          result.o[j] == (state.o[source[face][j]] + twist[face][j]) % 3;
        loop assigns i, result.p[0..6], result.o[0..6];
        loop variant CUBIES - i;
    */
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t from = source[face][i];
        result.p[i] = state.p[from];
        result.o[i] = (uint8_t) ((state.o[from] + twist[face][i]) % 3U);
    }
    return result;
}

static state_t apply_move(state_t state, uint8_t move)
{
    uint8_t turns = (uint8_t) (move % 3U + 1U);
    for (uint8_t i = 0; i < turns; ++i)
        state = quarter_turn(state, (uint8_t) (move / 3U));
    return state;
}

/*@ requires \valid_read(state);
    requires \forall integer i; 0 <= i < CUBIES ==>
      0 <= state->p[i] < CUBIES;
    requires \forall integer i, j; 0 <= i < j < CUBIES ==>
      state->p[i] != state->p[j];
    requires \forall integer i; 0 <= i < CUBIES ==>
      0 <= state->o[i] < 3;
    assigns \nothing;
    ensures \result < STATES;
 */
static uint32_t rank_state(const state_t *state)
{
    uint32_t p = 0, o = 0;
    /*@ loop invariant 0 <= i <= CUBIES;
        loop invariant (i == 0 ==> p == 0) && (i == 1 ==> p <= 6) &&
          (i == 2 ==> p <= 41) && (i == 3 ==> p <= 209) &&
          (i == 4 ==> p <= 839) && (i == 5 ==> p <= 2519) &&
          (i >= 6 ==> p <= 5039);
        loop assigns i, p;
        loop variant CUBIES - i;
     */
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t smaller = 0;
        /*@ loop invariant i + 1 <= j <= CUBIES;
            loop invariant smaller <= j - i - 1;
            loop assigns j, smaller;
            loop variant CUBIES - j;
         */
        for (uint8_t j = (uint8_t) (i + 1U); j < CUBIES; ++j)
            if (state->p[j] < state->p[i])
                ++smaller;
        p = p * (CUBIES - i) + smaller;
    }
    /*@ loop invariant 0 <= i <= 6;
        loop invariant (i == 0 ==> o == 0) && (i == 1 ==> o < 3) &&
          (i == 2 ==> o < 9) && (i == 3 ==> o < 27) &&
          (i == 4 ==> o < 81) && (i == 5 ==> o < 243) &&
          (i == 6 ==> o < 729);
        loop assigns i, o;
        loop variant 6 - i;
     */
    for (uint8_t i = 0; i < 6; ++i)
        o = o * 3U + state->o[i];
    return p * ORIENTATIONS + o;
}

/*@ requires \valid(state); requires rank < STATES; assigns *state; */
static void unrank_state(uint32_t rank, state_t *state)
{
    uint8_t available[CUBIES] = {0, 1, 2, 3, 4, 5, 6};
    uint32_t p = rank / ORIENTATIONS, o = rank % ORIENTATIONS, f = 720;
    uint8_t sum = 0;
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t q = (uint8_t) (p / f);
        p %= f;
        state->p[i] = available[q];
        for (uint8_t j = q; j + 1U < CUBIES - i; ++j)
            available[j] = available[j + 1U];
        if (i < 5)
            f /= 6U - i;
    }
    for (uint8_t i = 6; i-- > 0;) {
        state->o[i] = (uint8_t) (o % 3U);
        sum = (uint8_t) (sum + state->o[i]);
        o /= 3U;
    }
    state->o[6] = (uint8_t) ((3U - sum % 3U) % 3U);
}

/*@ requires \valid_read(state);
    requires \initialized(&state->p[0..6]) && \initialized(&state->o[0..6]);
    assigns \nothing;
    ensures \result != 0 ==> \forall integer i; 0 <= i < CUBIES ==>
      state->p[i] < CUBIES && state->o[i] < 3;
    ensures \result != 0 ==> \forall integer i, j; 0 <= i < j < CUBIES ==>
      state->p[i] != state->p[j];
    ensures \result != 0 ==>
      (state->o[0] + state->o[1] + state->o[2] + state->o[3] +
       state->o[4] + state->o[5] + state->o[6]) % 3 == 0;
    ensures complete: valid_state(state) ==> \result != 0;
 */
static int valid(const state_t *state)
{
    uint8_t sum = 0;
    /*@ loop invariant 0 <= i <= CUBIES;
        loop invariant sum <= 2 * i;
        loop invariant sum == (i > 0 ? state->o[0] : 0) +
          (i > 1 ? state->o[1] : 0) + (i > 2 ? state->o[2] : 0) +
          (i > 3 ? state->o[3] : 0) + (i > 4 ? state->o[4] : 0) +
          (i > 5 ? state->o[5] : 0) + (i > 6 ? state->o[6] : 0);
        loop invariant \forall integer j; 0 <= j < i ==>
          state->p[j] < CUBIES && state->o[j] < 3;
        loop invariant \forall integer j, k; 0 <= j < k < i ==>
          state->p[j] != state->p[k];
        loop assigns i, sum;
        loop variant CUBIES - i;
    */
    for (uint8_t i = 0; i < CUBIES; ++i) {
        if (state->p[i] >= CUBIES || state->o[i] >= 3)
            return 0;
        /*@ loop invariant 0 <= j <= i;
            loop invariant \forall integer k; 0 <= k < j ==>
              state->p[k] != state->p[i];
            loop assigns j;
            loop variant i - j;
        */
        for (uint8_t j = 0; j < i; ++j)
            if (state->p[j] == state->p[i])
                return 0;
        sum = (uint8_t) (sum + state->o[i]);
    }
    return sum % 3U == 0;
}

/* P and Q advance independently. Store only quarter turns; repeated lookups
 * produce half and inverse turns, each of which still costs one HTM move.
 * The caller owns the 34,614 bytes of transition storage.
 */
static void build_transitions(uint16_t permutation[3][PERMUTATIONS],
                              uint16_t orientation[3][ORIENTATIONS])
{
    state_t state;
    for (uint16_t rank = 0; rank < PERMUTATIONS; ++rank) {
        unrank_state((uint32_t) rank * ORIENTATIONS, &state);
        for (uint8_t face = 0; face < 3; ++face) {
            state_t next = quarter_turn(state, face);
            permutation[face][rank] =
                (uint16_t) (rank_state(&next) / ORIENTATIONS);
        }
    }
    for (uint16_t rank = 0; rank < ORIENTATIONS; ++rank) {
        unrank_state(rank, &state);
        for (uint8_t face = 0; face < 3; ++face) {
            state_t next = quarter_turn(state, face);
            orientation[face][rank] =
                (uint16_t) (rank_state(&next) % ORIENTATIONS);
        }
    }
}

/* The caller supplies count distances and count queue entries. The VLA
 * parameter describes the row stride of the existing table; it does not
 * allocate storage. count is PERMUTATIONS or ORIENTATIONS.
 */
static int build_coordinate_distances(uint16_t count,
                                      uint16_t turns[3][count],
                                      uint8_t distance[count],
                                      uint16_t queue[count])
{
    uint16_t head = 0, tail = 1;
    memset(distance, UINT8_MAX, count);
    distance[0] = 0;
    queue[0] = 0;
    while (head < tail) {
        uint16_t here = queue[head++];
        for (uint8_t face = 0; face < 3; ++face) {
            uint16_t next = here;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                next = turns[face][next];
                /* One, two and three quarter turns are all neighbors of
                 * here with HTM cost 1, not successive BFS depths.
                 */
                if (distance[next] == UINT8_MAX) {
                    distance[next] = (uint8_t) (distance[here] + 1U);
                    queue[tail++] = next;
                }
            }
        }
    }
    return tail == count;
}

/* Each projection drops constraints, so both distances are lower bounds.
 * Use max, not sum: the same move may improve both coordinates.
 */
static uint8_t coordinate_heuristic(uint16_t p,
                                    uint16_t q,
                                    const uint8_t permutation_distance[],
                                    const uint8_t orientation_distance[])
{
    uint8_t dp = permutation_distance[p], dq = orientation_distance[q];
    return dp > dq ? dp : dq;
}

typedef struct {
    uint16_t permutation[3][PERMUTATIONS];
    uint16_t orientation[3][ORIENTATIONS];
    uint8_t permutation_distance[PERMUTATIONS];
    uint8_t orientation_distance[ORIENTATIONS];
} coordinate_tables_t;

static coordinate_tables_t query_tables;

static int build_query_tables(void)
{
    uint16_t queue[PERMUTATIONS];
    build_transitions(query_tables.permutation, query_tables.orientation);
    return build_coordinate_distances(PERMUTATIONS, query_tables.permutation,
                                      query_tables.permutation_distance, queue) &&
           build_coordinate_distances(ORIENTATIONS, query_tables.orientation,
                                      query_tables.orientation_distance, queue);
}

typedef struct {
    uint16_t p, q;
    uint8_t previous_face, next_move;
} frame_t;

/* Host diagnostics only. Counters are collected separately for each bound;
 * a normal query passes NULL and produces only its solution line.
 */
typedef struct {
    uint64_t expanded[MAX_DEPTH + 1];
    uint64_t generated[MAX_DEPTH + 1];
    uint64_t cutoffs[MAX_DEPTH + 1];
    uint64_t same_face[MAX_DEPTH + 1];
} search_stats_t;

static int solve_coordinate(uint16_t p,
                            uint16_t q,
                            uint8_t path[MAX_DEPTH],
                            search_stats_t *stats)
{
    frame_t frames[MAX_DEPTH + 1];
    uint8_t initial = coordinate_heuristic(p, q,
                                         query_tables.permutation_distance,
                                         query_tables.orientation_distance);
    for (uint8_t bound = initial; bound <= MAX_DEPTH; ++bound) {
        uint8_t depth = 0;
        /* Face 3 is the root sentinel: none of R/B/D is excluded. */
        frames[0] = (frame_t) {p, q, 3, 0};
        for (;;) {
            frame_t *frame = &frames[depth];
            if (frame->p == 0 && frame->q == 0)
                return depth;
            if (depth == bound || frame->next_move == MOVES) {
                if (depth == 0)
                    break;
                --depth;
                continue;
            }
            /* Expanded means a non-goal frame whose outgoing moves are
             * examined. Count it only on its first visit, not on backtrack.
             */
            if (stats && frame->next_move == 0)
                ++stats->expanded[bound];
            uint8_t move = frame->next_move++;
            uint8_t face = (uint8_t) (move / 3U);
            if (face == frame->previous_face) {
                if (stats)
                    ++stats->same_face[bound];
                continue;
            }
            uint16_t next_p = frame->p, next_q = frame->q;
            for (uint8_t turn = 0; turn <= move % 3U; ++turn) {
                next_p = query_tables.permutation[face][next_p];
                next_q = query_tables.orientation[face][next_q];
            }
            if (stats)
                ++stats->generated[bound];
            uint8_t h = coordinate_heuristic(next_p, next_q,
                                           query_tables.permutation_distance,
                                           query_tables.orientation_distance);
            if (depth + 1U + h > bound) {
                if (stats)
                    ++stats->cutoffs[bound];
                continue;
            }
            /* The parent cursor was advanced before descent, so backtrack
             * resumes at the next move. depth < bound <= MAX_DEPTH here.
             */
            path[depth] = move;
            ++depth;
            frames[depth] = (frame_t) {next_p, next_q, face, 0};
        }
    }
    return -1;
}

static int replay_solution(state_t state,
                           const uint8_t path[MAX_DEPTH],
                           int length)
{
    if (length < 0 || length > MAX_DEPTH)
        return 0;
    for (int i = 0; i < length; ++i) {
        if (path[i] >= MOVES)
            return 0;
        state = apply_move(state, path[i]);
    }
    return valid(&state) && rank_state(&state) == 0;
}

static uint8_t *build_table(uint8_t *diameter)
{
    uint8_t *toward_solved = malloc(STATES);
    uint32_t *queue = malloc((size_t) STATES * sizeof *queue);
    uint16_t permutation[3][PERMUTATIONS], orientation[3][ORIENTATIONS];
    uint32_t head = 0, tail = 1, level_end = 1;
    if (!toward_solved || !queue) {
        free(toward_solved);
        free(queue);
        return NULL;
    }
    build_transitions(permutation, orientation);
    memset(toward_solved, UINT8_MAX, STATES);
    queue[0] = 0;
    toward_solved[0] = 0;
    *diameter = 0;
    while (head < tail) {
        if (head == level_end) {
            level_end = tail;
            ++*diameter;
        }
        uint32_t here = queue[head++];
        uint16_t p = (uint16_t) (here / ORIENTATIONS);
        uint16_t o = (uint16_t) (here % ORIENTATIONS);
        for (uint8_t face = 0; face < 3; ++face) {
            uint16_t next_p = p, next_o = o;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                next_p = permutation[face][next_p];
                next_o = orientation[face][next_o];
                uint32_t there = (uint32_t) next_p * ORIENTATIONS + next_o;
                if (toward_solved[there] == UINT8_MAX) {
                    uint8_t move = (uint8_t) (face * 3U + turn);
                    toward_solved[there] = inverse_move[move];
                    queue[tail++] = there;
                }
            }
        }
    }
    free(queue);
    if (tail != STATES) {
        free(toward_solved);
        return NULL;
    }
    return toward_solved;
}

/*@ requires valid_read_string(input);
    requires \valid(state);
    assigns state->p[0..6], state->o[0..6];
    ensures \result != 0 ==> input[14] == '\0';
    ensures \result != 0 ==> \forall integer i; 0 <= i < CUBIES ==>
      state->p[i] < CUBIES && state->o[i] < 3;
    ensures \result != 0 ==> \forall integer i, j; 0 <= i < j < CUBIES ==>
      state->p[i] != state->p[j];
    ensures \result != 0 ==>
      (state->o[0] + state->o[1] + state->o[2] + state->o[3] +
       state->o[4] + state->o[5] + state->o[6]) % 3 == 0;
    ensures \result != 0 ==> \forall integer i; 0 <= i < CUBIES ==>
      state->p[i] == input[i] - '1';
    ensures \result != 0 ==> \forall integer i; 0 <= i < CUBIES ==>
      state->o[i] == input[i + CUBIES] - '1';
 */
static int parse_state(const char *input, state_t *state)
{
    /*@ loop invariant 0 <= i <= 14;
        loop invariant i <= strlen(input);
        loop invariant i <= 7 ==> \initialized(&state->p[0..i-1]);
        loop invariant i >= 7 ==> \initialized(&state->p[0..6]);
        loop invariant i >= 7 ==> \initialized(&state->o[0..i-8]);
        loop invariant \forall integer j; 0 <= j < i && j < CUBIES ==>
          state->p[j] == input[j] - '1';
        loop invariant \forall integer j; 0 <= j < i - CUBIES ==>
          state->o[j] == input[j + CUBIES] - '1';
        loop assigns i, state->p[0..6], state->o[0..6];
        loop variant 14 - i;
     */
    for (int i = 0; i < 14; ++i) {
        int limit = i < 7 ? 7 : 3;
        if (input[i] < '1' || input[i] > '0' + limit)
            return 0;
        (i < 7 ? state->p : state->o)[i % 7] = (uint8_t) (input[i] - '1');
    }
    return input[14] == '\0' && valid(state);
}

/* stdout is fully buffered off a terminal, so a write error surfaces at the
 * flush, not at the printf that queued the bytes. Every exit path that has
 * produced output goes through here.
 */
static int output_failed(void)
{
    return fflush(stdout) != 0 || ferror(stdout);
}

static int self_test(void)
{
    const state_t solved = {{0, 1, 2, 3, 4, 5, 6}, {0}};
    uint16_t permutation[3][PERMUTATIONS], orientation[3][ORIENTATIONS];
    state_t state;
    for (uint8_t move = 0; move < MOVES; ++move) {
        state = solved;
        state = apply_move(state, move);
        state = apply_move(state, inverse_move[move]);
        if (memcmp(&solved, &state, sizeof solved))
            return 0;
    }
    build_transitions(permutation, orientation);
    for (uint32_t rank = 0; rank < STATES; ++rank) {
        unrank_state(rank, &state);
        if (!valid(&state) || rank_state(&state) != rank)
            return 0;
        /* Check factoring on every full state, not just the representative
         * states used to construct the tables. Each turn is an HTM neighbor
         * of the original state, even though lookups are chained here.
         */
        for (uint8_t face = 0; face < 3; ++face) {
            uint16_t p = (uint16_t) (rank / ORIENTATIONS);
            uint16_t q = (uint16_t) (rank % ORIENTATIONS);
            state_t next = state;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                next = quarter_turn(next, face);
                p = permutation[face][p];
                q = orientation[face][q];
                if (rank_state(&next) != (uint32_t) p * ORIENTATIONS + q)
                    return 0;
            }
        }
    }
    return 1;
}

/* Only the host self-test uses the exhaustive oracle. Walk its stored moves
 * with the cubie model to obtain an exact distance independently of the new
 * abstract BFS. This also checks that each oracle path actually solves.
 */
static int self_test_heuristic(const uint8_t *toward_solved)
{
    uint32_t gaps[12] = {0};
    uint8_t maximum = 0;
    if (query_tables.permutation_distance[0] != 0 ||
        query_tables.orientation_distance[0] != 0)
        return 0;
    for (uint32_t rank = 0; rank < STATES; ++rank) {
        uint16_t p = (uint16_t) (rank / ORIENTATIONS);
        uint16_t q = (uint16_t) (rank % ORIENTATIONS);
        uint8_t h = coordinate_heuristic(p, q,
                                        query_tables.permutation_distance,
                                        query_tables.orientation_distance);
        uint8_t distance = 0;
        uint32_t here = rank;
        state_t state;
        unrank_state(rank, &state);
        while (here) {
            uint8_t move = toward_solved[here];
            if (move >= MOVES || distance == 11)
                return 0;
            state = apply_move(state, move);
            here = rank_state(&state);
            ++distance;
        }
        if (h > distance)
            return 0;
        ++gaps[distance - h];
        if (h > maximum)
            maximum = h;
    }
    /* Keep the existing stdout contract; these diagnostics are self-test
     * statistics, not extra query output. All counts cover the full domain.
     */
    fprintf(stderr, "P/Q heuristic: 3674160 states checked; maximum %u\n",
            (unsigned) maximum);
    for (uint8_t gap = 0; gap < 12; ++gap)
        fprintf(stderr, "distance - heuristic = %u: %lu states\n",
                (unsigned) gap, (unsigned long) gaps[gap]);
    return 1;
}

/* Obtain exact length by following the original oracle with the cubie model.
 * Invalid moves and paths longer than the known diameter fail explicitly.
 */
static int oracle_distance(state_t state, const uint8_t *toward_solved)
{
    uint32_t rank = rank_state(&state);
    int distance = 0;
    while (rank) {
        uint8_t move = toward_solved[rank];
        if (move >= MOVES || distance == MAX_DEPTH)
            return -1;
        state = apply_move(state, move);
        rank = rank_state(&state);
        ++distance;
    }
    return distance;
}

static int check_search(state_t state,
                        int expected,
                        search_stats_t *stats)
{
    uint8_t path[MAX_DEPTH];
    uint32_t rank = rank_state(&state);
    int length = solve_coordinate((uint16_t) (rank / ORIENTATIONS),
                                  (uint16_t) (rank % ORIENTATIONS), path, stats);
    if (length != expected || !replay_solution(state, path, length)) {
        fprintf(stderr, "search failed at rank %lu: expected %d, got %d\n",
                (unsigned long) rank, expected, length);
        return 0;
    }
    return 1;
}

static void print_search_stats(const search_stats_t *stats)
{
    for (uint8_t bound = 0; bound <= MAX_DEPTH; ++bound) {
        if (stats->expanded[bound] || stats->generated[bound])
            fprintf(stderr,
                    "bound %u: expanded %llu; generated %llu; "
                    "cutoffs %llu; same-face skips %llu\n",
                    (unsigned) bound,
                    (unsigned long long) stats->expanded[bound],
                    (unsigned long long) stats->generated[bound],
                    (unsigned long long) stats->cutoffs[bound],
                    (unsigned long long) stats->same_face[bound]);
    }
}

/* Basic mode covers all distance-0..2 states, the eight existing vectors,
 * and deterministic ranks divisible by 65536. Hardest mode selects a range
 * of the 2644 distance-11 states in ascending rank order for bounded batches.
 */
static int self_test_search(const uint8_t *toward_solved,
                            int hardest,
                            uint16_t first,
                            uint16_t count)
{
    static const char *const vectors[] = {
        "12345671111111", "62345713133111", "24316572122213",
        "25713642221111", "24513763133333", "43752611332133",
        "25416373331111", "21345671111111"
    };
    uint32_t vector_ranks[sizeof vectors / sizeof vectors[0]];
    uint32_t checked = 0, hardest_seen = 0;
    search_stats_t stats = {0};
    state_t state;
    for (size_t i = 0; i < sizeof vectors / sizeof vectors[0]; ++i) {
        if (!parse_state(vectors[i], &state))
            return 0;
        vector_ranks[i] = rank_state(&state);
    }
    for (uint32_t rank = 0; rank < STATES; ++rank) {
        unrank_state(rank, &state);
        int distance = oracle_distance(state, toward_solved);
        if (distance < 0)
            return 0;
        int selected = 0;
        if (hardest) {
            if (distance == MAX_DEPTH) {
                selected = hardest_seen >= first &&
                           hardest_seen < (uint32_t) first + count;
                ++hardest_seen;
            }
        } else {
            selected = distance <= 2 || rank % 65536U == 0;
            for (size_t i = 0; i < sizeof vectors / sizeof vectors[0]; ++i)
                if (rank == vector_ranks[i])
                    selected = 1;
        }
        if (selected) {
            if (!check_search(state, distance, &stats))
                return 0;
            ++checked;
        }
    }
    if (hardest && (hardest_seen != HARDEST_STATES || checked != count))
        return 0;
    fprintf(stderr, "IDA* replay and exact length: %lu states checked",
            (unsigned long) checked);
    if (hardest)
        fprintf(stderr, "; hardest indices [%u,%u)",
                (unsigned) first, (unsigned) (first + count));
    fputc('\n', stderr);
    print_search_stats(&stats);
    fprintf(stderr,
            "query tables %lu bytes; frames %lu bytes; path %u bytes; "
            "build queue %lu bytes\n",
            (unsigned long) sizeof query_tables,
            (unsigned long) ((MAX_DEPTH + 1) * sizeof(frame_t)),
            (unsigned) MAX_DEPTH,
            (unsigned long) (PERMUTATIONS * sizeof(uint16_t)));
    return 1;
}

static int parse_test_number(const char *input, uint16_t *number)
{
    uint32_t value = 0;
    if (!*input)
        return 0;
    for (; *input; ++input) {
        if (*input < '0' || *input > '9')
            return 0;
        value = value * 10U + (unsigned) (*input - '0');
        if (value > HARDEST_STATES)
            return 0;
    }
    *number = (uint16_t) value;
    return 1;
}

int main(int argc, char **argv)
{
    state_t state;
    uint8_t diameter;
    if (argc == 2 && !strcmp(argv[1], "--self-test")) {
        if (!self_test()) {
            fputs("self-test failed\n", stderr);
            return 1;
        }
        uint8_t *table = build_table(&diameter);
        if (!table) {
            fputs("could not build complete state table\n", stderr);
            return 1;
        }
        if (diameter != 11) {
            free(table);
            fputs("BFS check failed\n", stderr);
            return 1;
        }
        if (!build_query_tables() || !self_test_heuristic(table) ||
            !self_test_search(table, 0, 0, 0)) {
            free(table);
            fputs("coordinate solver check failed\n", stderr);
            return 1;
        }
        free(table);
        puts("3674160 states; diameter 11");
        return output_failed();
    }
    if (argc == 4 && !strcmp(argv[1], "--search-test")) {
        uint16_t first, count;
        if (!parse_test_number(argv[2], &first) ||
            !parse_test_number(argv[3], &count) || count == 0 ||
            first + count > HARDEST_STATES) {
            fputs("usage: solver --search-test FIRST COUNT\n", stderr);
            return 2;
        }
        uint8_t *table = build_table(&diameter);
        if (!table)
            return 1;
        int ok = diameter == MAX_DEPTH && build_query_tables() &&
                 self_test_search(table, 1, first, count);
        free(table);
        if (!ok)
            return 1;
        puts("distance-11 batch passed");
        return output_failed();
    }
    if (argc != 2 || !parse_state(argv[1], &state)) {
        /* C99 5.1.2.2.1 lets argv[0] be null when argc is 0. */
        fprintf(stderr, "usage: %s PPPPPPPOOOOOOO\n",
                argc > 0 && argv[0] ? argv[0] : "solver");
        return 2;
    }
    if (!build_query_tables()) {
        fputs("could not build coordinate tables\n", stderr);
        return 1;
    }
    uint8_t path[MAX_DEPTH];
    uint32_t rank = rank_state(&state);
    int length = solve_coordinate((uint16_t) (rank / ORIENTATIONS),
                                  (uint16_t) (rank % ORIENTATIONS), path, NULL);
    if (!replay_solution(state, path, length)) {
        fputs("could not find a valid solution\n", stderr);
        return 1;
    }
    const char *separator = "";
    for (int i = 0; i < length; ++i) {
        printf("%s%s", separator, move_names[path[i]]);
        separator = " ";
    }
    putchar('\n');
    return output_failed();
}
