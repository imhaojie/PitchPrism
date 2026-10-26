"""Ground-plane geometry for the three reviewed stills, using only the standard library.

A homography is fitted from visible Law 1 markings (frame pixels -> metres). The reviewed foot
anchors are projected through it unchanged. Every drawn tactical layer is checked against these
measured positions, so a graphic cannot claim an open lane, free space or pressure that the frame
does not show. This is approximate single-frame geometry, not tracking.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOAL_CENTRE = (105.0, 34.0)
TOLERANCE_METRES = 1.2
OPTION_CLEARANCE, COVER_DISTANCE, CARRY_CLEARANCE = 1.5, 2.0, 2.5


def _solve(matrix, vector):
    n = len(vector)
    rows = [list(map(float, r)) + [float(v)] for r, v in zip(matrix, vector)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(rows[r][col]))
        if abs(rows[pivot][col]) < 1e-12:
            raise ValueError('Degenerate marking layout')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(n):
            if r != col:
                k = rows[r][col] / rows[col][col]
                rows[r] = [a - k * b for a, b in zip(rows[r], rows[col])]
    return [rows[i][n] / rows[i][i] for i in range(n)]


def fit_homography(image, ground):
    """Least-squares DLT with h33 = 1, mapping image pixels to ground metres."""
    a, b = [], []
    for (x, y), (u, v) in zip(image, ground):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    normal = [[sum(r[i] * r[j] for r in a) for j in range(8)] for i in range(8)]
    rhs = [sum(r[i] * value for r, value in zip(a, b)) for i in range(8)]
    h = _solve(normal, rhs) + [1.0]
    return [h[0:3], h[3:6], h[6:9]]


def apply(h, point):
    x, y = point
    w = h[2][0] * x + h[2][1] * y + h[2][2]
    return ((h[0][0] * x + h[0][1] * y + h[0][2]) / w, (h[1][0] * x + h[1][1] * y + h[1][2]) / w)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def measure(clip, geometry):
    """Measured ground position of every reviewed anchor, per scene; raises if markings disagree."""
    result = {}
    for scene in clip['scenes']:
        spec = geometry['scenes'][scene['id']]
        h = fit_homography([m['image'] for m in spec['markings']], [m['ground'] for m in spec['markings']])
        errors = [distance(apply(h, m['image']), m['ground']) for m in spec['markings']]
        for check in spec.get('checks', []):
            errors += [abs(distance(apply(h, p), check['centre']) - check['radius']) for p in check['image']]
        if max(errors) > TOLERANCE_METRES:
            raise ValueError(f"Ground model for {scene['id']} misses its markings by {max(errors):.2f} m")
        ground = {p['id']: apply(h, (p['foot'][0] * 1.5, p['foot'][1] * 1.5)) for p in scene['players']}
        if any(not (0 <= x <= 105 and -2 <= y <= 70) for x, y in ground.values()):
            raise ValueError(f"A reviewed anchor in {scene['id']} falls off the pitch")
        result[scene['id']] = {'homography': h, 'ground': ground, 'error': max(errors)}
    return result


def lane_offset(start, end, point):
    """(t along start->end, perpendicular metres) of a point against a straight lane."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    rx, ry = point[0] - start[0], point[1] - start[1]
    length2 = dx * dx + dy * dy
    return (rx * dx + ry * dy) / length2, abs(dx * ry - dy * rx) / math.sqrt(length2)


def check_step(scene, step, ground):
    """Refuse any option, covered lane, carry or zone that the measured geometry does not support."""
    team = {p['id']: p['team'] for p in scene['players']}
    rivals = lambda pid: [p for p in team if team[p] != team[pid]]
    for index in step['routes']:
        route = scene['routes'][index]
        for pid in rivals(route['a']):
            t, off = lane_offset(ground[route['a']], ground[route['b']], ground[pid])
            if .1 < t < .9 and off < OPTION_CLEARANCE:
                raise ValueError(f"{scene['id']}: option {route['a']}->{route['b']} is covered by {pid}")
    for layer in step.get('layers', []):
        kind = layer['type']
        if kind == 'covered':
            t, off = lane_offset(ground[layer['from']], ground[layer['to']], ground[layer['by']])
            if not (.15 < t < .85 and off <= COVER_DISTANCE) or team[layer['by']] == team[layer['from']]:
                raise ValueError(f"{scene['id']}: {layer['by']} does not cover {layer['from']}->{layer['to']}")
        elif kind == 'carry':
            start = ground[layer['from']]
            end = (start[0] + layer['offset'][0], start[1] + layer['offset'][1])
            for pid in rivals(layer['from']):
                t, off = lane_offset(start, end, ground[pid])
                if -.05 < t < 1.15 and off < CARRY_CLEARANCE:
                    raise ValueError(f"{scene['id']}: carry path is blocked by {pid}")
        elif kind in ('space', 'pressure'):
            centre = ground[layer['around']]
            inside = [pid for pid in rivals(layer['around']) if distance(ground[pid], centre) < layer['radius']]
            if (kind == 'space') == bool(inside):
                raise ValueError(f"{scene['id']}: {kind} zone around {layer['around']} contradicts the measured positions")
        elif kind == 'goal-side':
            reach = distance(ground[layer['ball']], GOAL_CENTRE)
            for pid in layer['defenders']:
                if distance(ground[pid], GOAL_CENTRE) >= reach or team[pid] == team[layer['ball']]:
                    raise ValueError(f"{scene['id']}: {pid} is not goal-side of the ball")
        else:
            raise ValueError('Unknown tactical layer: ' + kind)


def load():
    read = lambda name: json.loads((HERE / 'data' / name).read_text())
    return read('clip.json'), read('tactical-story.json'), read('tactical-geometry.json')


def validate(clip=None, story=None, geometry=None):
    clip, story, geometry = clip or load()[0], story or load()[1], geometry or load()[2]
    measured = measure(clip, geometry)
    for scene in clip['scenes']:
        for step in story['scenes'][scene['id']]['steps']:
            check_step(scene, step, measured[scene['id']]['ground'])
    return measured
