"""Integer 3-D cube geometry used to generate and independently test the net.

Axes: +x=R, +y=U, +z=F. Face order is U,L,F,R,B,D. Corner order matches
the solver, followed by the fixed UFL corner. Orientation is the negative
cyclic offset in a consistently left-handed corner-face ordering.
"""
import sys

sys.dont_write_bytecode = True

NORMALS = ((0, 1, 0), (-1, 0, 0), (0, 0, 1), (1, 0, 0), (0, 0, -1), (0, -1, 0))
CORNERS = ((1, 1, 1), (1, -1, 1), (-1, -1, 1), (1, 1, -1),
           (1, -1, -1), (-1, -1, -1), (-1, 1, -1), (-1, 1, 1))
PALETTE = (0xFFFFFF, 0xFF9000, 0x00B050, 0xFF3030, 0x3050FF, 0xFFFF00)
ORIGINS = ((9, 2), (0, 9), (9, 9), (18, 9), (27, 9), (9, 16))


def corner_faces(position):
    x, y, z = position
    sides = ((x, 0, 0), (0, 0, z))
    if x * y * z < 0:
        sides = sides[::-1]
    return ((0, y, 0), *sides)


def face_positions(face):
    if face == 0:
        return ((-1, 1, -1), (1, 1, -1), (-1, 1, 1), (1, 1, 1))
    if face == 1:
        return ((-1, 1, -1), (-1, 1, 1), (-1, -1, -1), (-1, -1, 1))
    if face == 2:
        return ((-1, 1, 1), (1, 1, 1), (-1, -1, 1), (1, -1, 1))
    if face == 3:
        return ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1))
    if face == 4:
        return ((1, 1, -1), (-1, 1, -1), (1, -1, -1), (-1, -1, -1))
    return ((-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1))


FACELETS = tuple((p, NORMALS[f]) for f in range(6) for p in face_positions(f))
CORNER_COLORS = tuple(NORMALS.index(n) for p in CORNERS for n in corner_faces(p))
CORNER_FACELETS = tuple(FACELETS.index((p, n)) for p in CORNERS for n in corner_faces(p))


def rotate(vector, face):
    x, y, z = vector
    if face == 0:  # R clockwise: -90 degrees about +x
        return x, z, -y
    if face == 1:  # B clockwise: +90 degrees about +z
        return -y, x, z
    return z, y, -x  # D clockwise: +90 degrees about +y


def affected(position, face):
    return position[0] == 1 if face == 0 else position[2] == -1 if face == 1 else position[1] == -1


def corner_turn(face):
    source, twist = list(range(8)), [0] * 8
    for old, position in enumerate(CORNERS):
        if affected(position, face):
            destination = CORNERS.index(rotate(position, face))
            normal = rotate(corner_faces(position)[0], face)
            source[destination] = old
            twist[destination] = (-corner_faces(CORNERS[destination]).index(normal)) % 3
    assert source[7] == 7 and twist[7] == 0
    return source[:7], twist[:7]


def turn_facelets(colors, move):
    face, turns = divmod(move, 3)
    for _ in range(turns + 1):
        result = list(colors)
        for old, (position, normal) in enumerate(FACELETS):
            if affected(position, face):
                destination = FACELETS.index((rotate(position, face), rotate(normal, face)))
                result[destination] = colors[old]
        colors = result
    return colors


def facelets_from_cubies(state):
    result = [0] * 24
    for position in range(8):
        identity = state[position] if position < 7 else 7
        orientation = state[position + 7] if position < 7 else 0
        for j in range(3):
            result[CORNER_FACELETS[3 * position + j]] = CORNER_COLORS[3 * identity + (j + orientation) % 3]
    return result


def pixels(colors):
    result = [0] * (35 * 25)
    for facelet, color in enumerate(colors):
        face, slot = divmod(facelet, 4)
        x, y = ORIGINS[face]
        x += 4 * (slot % 2)
        y += 3 * (slot // 2)
        for dy in range(3):
            for dx in range(4):
                result[(y + dy) * 35 + x + dx] = PALETTE[color]
    return result


def emit_tables():
    from check_smoke import SOURCES, TWISTS
    turns = [corner_turn(f) for f in range(3)]
    assert tuple(tuple(s) for s, _ in turns) == SOURCES
    assert tuple(tuple(t) for _, t in turns) == TWISTS
    assert sorted(CORNER_FACELETS) == list(range(24))
    print('.section .rodata.renderer, "a", @progbits')
    for name, values in (('cube_render_source', [v for s, _ in turns for v in s]),
                         ('cube_render_twist', [v for _, t in turns for v in t]),
                         ('cube_corner_colors', CORNER_COLORS), ('cube_corner_facelets', CORNER_FACELETS)):
        print(f'{name}:\n.byte ' + ','.join(map(str, values)))
    print('.balign 4\ncube_palette:\n.4byte ' + ','.join(hex(c) for c in PALETTE))
    print('cube_led_offsets:')
    for f, (x, y) in enumerate(ORIGINS):
        for slot in range(4):
            print(f'.4byte 4*(({y + 3 * (slot // 2)})*LED_MATRIX_0_WIDTH+{x + 4 * (slot % 2)})')


if __name__ == '__main__':
    emit_tables()
