"""A small perspective camera for the editorial pitch schematic.

World units are metres on a nominal 105x68m IFAB Law 1 pitch: +X runs towards the attacked goal,
Z is up. Board points are the reviewed editorial percentages, never measured match coordinates.
The top-down pose reproduces the flat tactical board exactly, so the 3D views are presentation only.
"""
import math

import cv2
import numpy as np

LENGTH, WIDTH = 105.0, 68.0
GOAL_HALF, GOAL_HEIGHT, GOAL_DEPTH = 3.66, 2.44, 1.2
# Flat board: 8.4px per width-percent and 12.97px per length-percent, i.e. 12.353px per metre.
BOARD_SCALE = 8.4 / .68
BOARD_CENTRE = (1350.0, 609.0)
TOP_DISTANCE = 120.0
FOCAL = BOARD_SCALE * TOP_DISTANCE
NEAR = .5
# Figures are stylised broadcast tokens, drawn larger than life so they read at board scale.
FIGURE_BODY = 1.8
FIGURE_HEIGHT = FIGURE_BODY + .8


def world(point, z=0.0):
    """Editorial board percentages -> world metres (screen-right on the board is -Y)."""
    return np.array([point[0] * LENGTH / 100, (100 - point[1]) * WIDTH / 100, z], float)


class Pose:
    __slots__ = ('target', 'distance', 'azimuth', 'elevation', 'centre')

    def __init__(self, target, distance, azimuth, elevation, centre=BOARD_CENTRE):
        self.target = np.asarray(target, float)
        self.distance, self.azimuth, self.elevation = float(distance), float(azimuth), float(elevation)
        self.centre = np.asarray(centre, float)

    def mix(self, other, k):
        lerp = lambda a, b: a + (b - a) * k
        return Pose(lerp(self.target, other.target), lerp(self.distance, other.distance),
                    lerp(self.azimuth, other.azimuth), lerp(self.elevation, other.elevation),
                    lerp(self.centre, other.centre))


TOP = Pose((73.5, 34.0, 0.0), TOP_DISTANCE, -math.pi, math.pi / 2)


class Camera:
    def __init__(self, pose, focal=FOCAL):
        az, el = pose.azimuth, pose.elevation
        self.pose, self.focal, self.centre = pose, focal, pose.centre
        self.eye = pose.target + pose.distance * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        forward = pose.target - self.eye
        forward /= np.linalg.norm(forward)
        right = np.array([-math.sin(az), math.cos(az), 0.0])
        self.basis = np.stack([right, np.cross(forward, right), forward])

    def to_camera(self, points):
        return (np.atleast_2d(points) - self.eye) @ self.basis.T

    def screen(self, cam):
        cam = np.atleast_2d(cam)
        return self.centre + self.focal * cam[:, :2] / cam[:, 2:3]

    def project(self, points):
        """Screen positions of points in front of the camera (callers clip anything near the lens)."""
        return self.screen(self.to_camera(points))

    def scale(self, point):
        """Pixels per metre at a point, relative to the flat board."""
        return self.focal / max(NEAR, self.to_camera(point)[0, 2]) / BOARD_SCALE

    def horizon(self):
        """Screen row of the horizon, or None when the camera looks straight down."""
        ahead = self.basis @ np.array([-math.cos(self.pose.azimuth), -math.sin(self.pose.azimuth), 0.0])
        return None if ahead[2] < 1e-3 else float(self.centre[1] + self.focal * ahead[1] / ahead[2])

    def tilt(self, point):
        """Vertical squash of a ground circle seen from the camera (1 = straight down)."""
        ray = np.asarray(point, float) - self.eye
        return abs(ray[2]) / np.linalg.norm(ray)


def clip_polygon(cam):
    """Sutherland-Hodgman against the near plane, in camera coordinates."""
    out = []
    for a, b in zip(cam, np.roll(cam, -1, axis=0)):
        ina, inb = a[2] >= NEAR, b[2] >= NEAR
        if ina:
            out.append(a)
        if ina != inb:
            out.append(a + (b - a) * (NEAR - a[2]) / (b[2] - a[2]))
    return np.array(out)


def clip_segment(a, b):
    if a[2] < NEAR and b[2] < NEAR:
        return None
    if a[2] < NEAR:
        a = a + (b - a) * (NEAR - a[2]) / (b[2] - a[2])
    elif b[2] < NEAR:
        b = b + (a - b) * (NEAR - b[2]) / (a[2] - b[2])
    return a, b


def _fill(canvas, points, color, alpha):
    if alpha <= .003 or len(points) < 3:
        return
    colour = tuple(int(c) for c in color) + ((int(alpha * 255),) if canvas.shape[2] == 4 else ())
    cv2.fillPoly(canvas, [np.round(np.asarray(points) * 16).astype(np.int32)], colour, cv2.LINE_AA, 4)


def fill_world(canvas, camera, polygon, color, alpha):
    cam = clip_polygon(camera.to_camera(polygon))
    if len(cam) >= 3:
        _fill(canvas, camera.screen(cam), color, alpha)


def polyline(canvas, camera, points, color, alpha, width=2):
    cam = camera.to_camera(points)
    colour = tuple(int(c) for c in color) + ((int(alpha * 255),) if canvas.shape[2] == 4 else ())
    for a, b in zip(cam[:-1], cam[1:]):
        segment = clip_segment(a, b)
        if segment is None:
            continue
        p, q = camera.screen(np.array(segment))
        cv2.line(canvas, tuple(np.round(p * 16).astype(int)), tuple(np.round(q * 16).astype(int)), colour, width, cv2.LINE_AA, 4)


def circle(centre, radius, z=0.0, count=48, start=0.0, end=2 * math.pi):
    angles = np.linspace(start, end, count)
    return np.stack([centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles), np.full(count, z)], axis=1)


def markings():
    """IFAB Law 1 line work on the nominal pitch, as world-space polylines."""
    half_goal = WIDTH / 2
    box_y, area_y = GOAL_HALF + 16.5, GOAL_HALF + 5.5
    lines = [[(0, 0), (LENGTH, 0), (LENGTH, WIDTH), (0, WIDTH), (0, 0)], [(LENGTH / 2, 0), (LENGTH / 2, WIDTH)]]
    for end, sign in ((LENGTH, -1), (0, 1)):
        lines.append([(end, half_goal - box_y), (end + sign * 16.5, half_goal - box_y), (end + sign * 16.5, half_goal + box_y), (end, half_goal + box_y)])
        lines.append([(end, half_goal - area_y), (end + sign * 5.5, half_goal - area_y), (end + sign * 5.5, half_goal + area_y), (end, half_goal + area_y)])
        spot = end + sign * 11
        theta = math.acos(5.5 / 9.15)
        start = math.pi - theta if sign < 0 else -theta
        lines.append(circle((spot, half_goal), 9.15, start=start, end=start + 2 * theta, count=40)[:, :2])
    lines = [np.column_stack([np.asarray(l, float), np.zeros(len(l))]) for l in lines]
    lines.append(circle((LENGTH / 2, half_goal), 9.15, count=90))
    for x, y, a in ((0, 0, 0), (LENGTH, 0, math.pi / 2), (LENGTH, WIDTH, math.pi), (0, WIDTH, -math.pi / 2)):
        lines.append(circle((x, y), 1.0, start=a, end=a + math.pi / 2, count=12))
    spots = [(LENGTH / 2, half_goal), (LENGTH - 11, half_goal), (11, half_goal)]
    return lines, spots


LINES, SPOTS = markings()


def goal_frame(end=LENGTH):
    sign = 1 if end == LENGTH else -1
    y0, y1, back = WIDTH / 2 - GOAL_HALF, WIDTH / 2 + GOAL_HALF, end + sign * GOAL_DEPTH
    frame = [[(end, y0, 0), (end, y0, GOAL_HEIGHT), (end, y1, GOAL_HEIGHT), (end, y1, 0)]]
    net = [[(end, y0, GOAL_HEIGHT), (back, y0, GOAL_HEIGHT * .8), (back, y0, 0), (end, y0, 0)],
           [(end, y1, GOAL_HEIGHT), (back, y1, GOAL_HEIGHT * .8), (back, y1, 0), (end, y1, 0)],
           [(back, y0, GOAL_HEIGHT * .8), (back, y1, GOAL_HEIGHT * .8)], [(back, y0, 0), (back, y1, 0)]]
    mesh = [[(end + (back - end) * k, y0, GOAL_HEIGHT * (1 - .2 * k)), (end + (back - end) * k, y1, GOAL_HEIGHT * (1 - .2 * k))] for k in (.33, .66)]
    mesh += [[(back, y, 0), (back, y, GOAL_HEIGHT * .8)] for y in np.linspace(y0, y1, 9)[1:-1]]
    as_array = lambda paths: [np.asarray(p, float) for p in paths]
    return as_array(frame), as_array(net), as_array(mesh)


GOAL = goal_frame()


def draw_pitch(canvas, camera, alpha, palette):
    """Turf, Law 1 markings and a goal frame with net, drawn with near-plane clipping."""
    surround, turf, turf_alt, chalk = palette
    fill_world(canvas, camera, np.array([(-6, -6, 0), (LENGTH + 6, -6, 0), (LENGTH + 6, WIDTH + 6, 0), (-6, WIDTH + 6, 0)]), surround, alpha)
    stripe = 5.25
    for i in range(20):
        x1 = LENGTH - i * stripe
        x0 = x1 - stripe
        fill_world(canvas, camera, np.array([(x0, 0, 0), (x1, 0, 0), (x1, WIDTH, 0), (x0, WIDTH, 0)]), turf if i % 2 == 0 else turf_alt, alpha)
    for line in LINES:
        polyline(canvas, camera, line, chalk, .58 * alpha, 2)
    for x, y in SPOTS:
        fill_world(canvas, camera, circle((x, y), .3, count=12), chalk, .8 * alpha)
    frame, net, mesh = GOAL
    for path in mesh:
        polyline(canvas, camera, path, chalk, .22 * alpha, 1)
    for path in net:
        polyline(canvas, camera, path, chalk, .45 * alpha, 1)
    for path in frame:
        polyline(canvas, camera, path, (255, 255, 255), .95 * alpha, 3)


def figure(canvas, camera, position, color, alpha, rise, shade, light=(-.55, .45)):
    """An anonymous team-coloured figure (no likeness, number or identity) that rises from the turf."""
    if alpha <= .003 or rise <= .01:
        return
    x, y = position[:2]
    body, head = FIGURE_BODY * rise, (FIGURE_BODY + .46) * rise
    base, top = circle((x, y), .5, 0, 20), circle((x, y), .42, body, 20)
    cam = camera.to_camera(np.vstack([base, top]))
    if cam[:, 2].min() < NEAR:
        return
    flat = camera.screen(cam)
    hull = cv2.convexHull(flat.astype(np.float32)).reshape(-1, 2)
    _fill(canvas, hull, shade(color, .52), alpha)
    lit = np.cos(np.linspace(0, 2 * math.pi, 20)) * light[0] + np.sin(np.linspace(0, 2 * math.pi, 20)) * light[1] > 0
    lit_points = np.vstack([flat[:20][lit], flat[20:][lit]])
    if len(lit_points) >= 3:
        _fill(canvas, cv2.convexHull(lit_points.astype(np.float32)).reshape(-1, 2), color, alpha)
    centre = camera.project(np.array([x, y, head]))[0]
    radius = max(1.5, camera.focal * .33 * rise / camera.to_camera(np.array([x, y, head]))[0, 2])
    colour = tuple(int(c) for c in shade(color, 1.18)) + (int(alpha * 255),)
    cv2.circle(canvas, tuple(np.round(centre * 16).astype(int)), int(round(radius * 16)), colour, -1, cv2.LINE_AA, 4)
    rim = tuple(int(c) for c in (238, 248, 243)) + (int(alpha * .45 * 255),)
    cv2.polylines(canvas, [np.round(hull * 16).astype(np.int32)], True, rim, 1, cv2.LINE_AA, 4)
    return centre - np.array([0, radius])


def beam(glow, camera, position, color, strength, rise, height=8.0, width=.9):
    """A soft light column above a focus figure, billboarded towards the camera."""
    if strength <= .003 or rise <= .01:
        return
    side = camera.basis[0] * width / 2
    base = np.array([position[0], position[1], 0.0])
    quad = np.array([base - side, base + side, base + side + [0, 0, height * rise], base - side + [0, 0, height * rise]])
    cam = clip_polygon(camera.to_camera(quad))
    if len(cam) >= 3:
        _fill(glow, camera.screen(cam), tuple(min(255, int(c * strength)) for c in color), 1)


def ground_shadow(image, camera, position, alpha, rise, light=(-.55, .45)):
    """Blend a soft contact shadow into the composed image under each standing figure."""
    if alpha <= .003 or rise <= .01:
        return
    offset = np.array(light) * -.5 * rise
    cam = clip_polygon(camera.to_camera(circle((position[0] + offset[0], position[1] + offset[1]), .85, 0, 24)))
    if len(cam) < 3:
        return
    points = camera.screen(cam)
    x0, y0 = np.floor(points.min(0)).astype(int) - 2
    x1, y1 = np.ceil(points.max(0)).astype(int) + 2
    h, w = image.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.fillPoly(mask, [np.round((points - [x0, y0]) * 16).astype(np.int32)], 1.0, cv2.LINE_AA, 4)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.5)[..., None]
    image[y0:y1, x0:x1] *= 1 - .45 * alpha * mask
