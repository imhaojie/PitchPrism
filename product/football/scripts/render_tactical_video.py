"""Burn reviewed, three-step football readings into a standalone English MP4.

Accepts the exact original input or the separately hash-locked, lossless remux.
Writes a separate render and receipt; publishing requires explicit media packaging.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
sys.path.insert(0, str(HERE))
import tactical_geometry
from gamebuddy_fx import fx
import pitch3d as p3

W, H, FPS = 1920, 1080, 25
CLIP = json.loads((HERE / 'data/clip.json').read_text())
STORY = json.loads((HERE / 'data/tactical-story.json').read_text())
GEOMETRY = json.loads((HERE / 'data/tactical-geometry.json').read_text())
# Broadcast identity: deep violet ink, electric cyan as the house accent, signal green and hot magenta.
# Team colours stay semantic: sky blue for City, warm coral for Newcastle, gold for space and the carrier.
MINT, CORAL, GOLD = map(fx.hexc, ('7ff0ff', 'ff6f61', 'ffd166'))
CYAN, GREEN, MAGENTA, VIOLET = map(fx.hexc, ('2ee6ff', '00f58c', 'ff2d87', '5b2bd1'))
INK, PAPER, DIM = map(fx.hexc, ('1a0634', 'ffffff', 'b9b0d6'))
SHADOW, CHALK, TURF, TURF_ALT = map(fx.hexc, ('0a0218', 'e6e0ff', '1d1147', '190e3e'))
STEP = CLIP['production']['readingStepSeconds']
FREEZE = STORY['freezeDurationSeconds']
BODY = str(HERE / 'watch/fonts/dm-sans.ttf')
DISPLAY = str(HERE / 'watch/fonts/BarlowCondensed-ExtraBold.ttf')
DISPLAY_ITALIC = str(HERE / 'watch/fonts/BarlowCondensed-ExtraBoldItalic.ttf')
LABEL = str(HERE / 'watch/fonts/BarlowCondensed-SemiBold.ttf')
MARK = HERE / 'watch/mark.svg'
_SOURCE = None
_CAPTURE = None
_LAST = -1
_BUDDY = None
TEXT_AUDIT = None
LABEL_AUDIT = None
PANEL_AUDIT = None
ROLE_LABELS = {'carrier': 'CARRIER', 'press': 'OPPONENT', 'support': 'LINK',
               'runner': 'SUPPORT', 'right': 'RIGHT', 'wide': 'WIDE'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_source(source):
    actual = digest(source)
    if actual == CLIP['source']['sha256']:
        return {'inputKind': 'reviewed-original', 'inputSha256': actual}
    lock = json.loads((HERE / 'data/source-lock.json').read_text())
    if actual != lock['remuxSha256'] or CLIP['source']['sha256'] != lock['originalSha256']:
        raise ValueError('Input is neither the reviewed original nor its hash-locked lossless remux')
    return {'inputKind': 'hash-locked-lossless-remux', 'inputSha256': actual,
            'reviewedOriginalSha256': CLIP['source']['sha256']}


def validate_story():
    observations = {o['id']: o for o in CLIP['observations']}
    for scene in CLIP['scenes']:
        plan = STORY['scenes'][scene['id']]
        observation = observations[plan['evidenceId']]
        if observation.get('scene') != scene['id'] or observation['second'] != scene['second']:
            raise ValueError('Story is not bound to the correct reviewed frame')
        roles = {p['id'] for p in scene['players']}
        if len(plan['steps']) != 3:
            raise ValueError('Each reviewed scene needs three readings')
        for step in plan['steps']:
            if not set(step['focus']) <= roles or not all(0 <= i < len(scene['routes']) for i in step['routes']):
                raise ValueError('Story references an unreviewed role or route')
            referenced = {v for layer in step.get('layers', []) for k, v in layer.items() if k in ('from', 'to', 'by', 'around', 'ball')}
            referenced |= {pid for layer in step.get('layers', []) for pid in layer.get('defenders', [])} | set(step.get('labels', {}))
            if not referenced <= roles:
                raise ValueError('Story layer references an unreviewed role')
            # Geometry must support every option, covered lane, carry and zone that is drawn.
            tactical_geometry.check_step(scene, step, measured()[scene['id']]['ground'])


def timeline():
    result, current = [], 0.0
    for original in CLIP['production']['timeline']:
        segment = dict(original)
        kind = segment['kind']
        if kind == 'freeze':
            duration = STORY['freezeDurationSeconds']
        elif kind == 'rewind':
            duration = .6
        elif kind == 'replay':
            segment['sourceEnd'] = 59.6
            duration = 5.6
        elif kind == 'outro':
            duration = 3.2
        else:
            duration = original['outputEnd'] - original['outputStart']
        segment.update(outputStart=round(current, 2), outputEnd=round(current + duration, 2))
        current = segment['outputEnd']
        result.append(segment)
    if current >= 120:
        raise ValueError('The English demonstration must remain strictly under two minutes')
    live = [s for s in result if s['kind'] == 'live']
    if live[0]['sourceStart'] != 0 or live[-1]['sourceEnd'] != CLIP['durationSeconds']:
        raise ValueError('Original coverage is incomplete')
    if any(a['sourceEnd'] != b['sourceStart'] for a, b in zip(live, live[1:])):
        raise ValueError('The complete source must be retained in order')
    return result


TIMELINE = timeline()


def setup(source, buddy):
    global _SOURCE, _CAPTURE, _LAST, _BUDDY
    _SOURCE = str(source)
    _CAPTURE = cv2.VideoCapture(_SOURCE)
    if not _CAPTURE.isOpened():
        raise ValueError('Cannot open verified input')
    if (round(_CAPTURE.get(cv2.CAP_PROP_FRAME_COUNT)), round(_CAPTURE.get(cv2.CAP_PROP_FPS))) != (1665, 25):
        raise ValueError('Unexpected source frame count or frame rate')
    _LAST = -1
    cv2.setNumThreads(1)
    fx.PRESENTATION_ENGLISH, fx.SHOW_PRODUCTION_NOTES = True, False
    # Bundled Barlow Condensed replaces system DIN, so every machine renders the same typography.
    fx.DIN, fx.DINA = LABEL, DISPLAY
    if not Path(fx.CJK).is_file():
        fx.CJK = BODY
    _BUDDY = np.asarray(Image.open(buddy).convert('RGBA'))
    # Only this football process replaces the bookend asset; upstream stays unchanged.
    fx.gamebuddy_mascot_rgba = lambda closing=False: _BUDDY


@lru_cache(maxsize=8)
def still(second):
    cap = cv2.VideoCapture(_SOURCE)
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * FPS))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise ValueError('Could not decode reviewed still')
    return cv2.resize(frame, (W, H))


def frame_at(second):
    global _LAST
    index = min(1664, max(0, round(second * FPS)))
    if index != _LAST + 1:
        _CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = _CAPTURE.read()
    _LAST = index
    if not ok:
        raise ValueError('Could not decode source frame')
    return cv2.resize(frame, (W, H))


@lru_cache(maxsize=8)
def supported_characters(face):
    from fontTools.ttLib import TTFont
    with TTFont(face, fontNumber=0) as font:
        return frozenset(font.getBestCmap())


def text(layer, value, x, y, size=28, color=PAPER, alpha=1, face=BODY, anchor='lt', track=0, max_width=None, reveal=1):
    if any(ord(char) not in supported_characters(face) for char in value):
        raise ValueError('Missing font glyph in: ' + value)
    raster = fx.text_rgba(value, face, size, color, track)
    while max_width and raster.shape[1] > max_width and size > 14:
        size -= 1
        raster = fx.text_rgba(value, face, size, color, track)
    if max_width and raster.shape[1] > max_width:
        raise ValueError('Text cannot fit its declared box: ' + value)
    height, width = raster.shape[:2]
    xx, yy = x, y
    if anchor == 'c': xx, yy = x-width/2, y-height/2
    elif anchor == 'rt': xx = x-width
    elif anchor == 'rc': xx, yy = x-width, y-height/2
    elif anchor == 'lc': yy = y-height/2
    # Audit the complete line even while a wipe reveals it, so every final position is checked.
    if TEXT_AUDIT is not None and alpha > .05:
        TEXT_AUDIT.append(dict(text=value, x=xx, y=yy, width=width, height=height, font=face, size=size))
    keep = round(width * fx.clamp(reveal))
    if keep > 0:
        layer.paste(raster[:, :keep], xx, yy, alpha=alpha)


def caps_top(top, box, size):
    # DIN rasters carry ascender room; centre the visible capitals inside a box instead.
    return top + (box - .7 * size) / 2 - (.04 * size + 2)


def wrap(value, width, size):
    lines, row = [], ''
    for word in value.split():
        proposed = (row + ' ' + word).strip()
        if row and fx.text_rgba(proposed, BODY, size, PAPER).shape[1] > width:
            lines.append(row)
            row = word
        else:
            row = proposed
    if row:
        lines.append(row)
    return lines


def paragraph(layer, value, x, y, width=650, size=27, color=DIM, alpha=1, line_height=38, max_height=None):
    lines = wrap(value, width, size)
    if max_height and (len(lines)-1)*line_height + fx.text_rgba(lines[-1],BODY,size,PAPER).shape[0] > max_height:
        raise ValueError('Paragraph exceeds its declared box: ' + value)
    for i, row in enumerate(lines):
        text(layer, row, x, y + i * line_height, size, color, alpha, max_width=width)


def poly(canvas, points, color, alpha):
    if alpha <= .003:
        return
    colour = tuple(int(c) for c in color) + ((int(alpha * 255),) if canvas.shape[2] == 4 else ())
    cv2.fillPoly(canvas, [np.round(np.asarray(points) * 16).astype(np.int32)], colour, cv2.LINE_AA, 4)


def panel(layer, x0, y0, x1, y1, alpha, accent=None, opacity=.86, hairline=True, accent_width=6, name=None):
    """Frosted broadcast card: the footage behind is softened, then tinted with ink."""
    x0, y0, x1, y1 = (int(round(max(0, x0))), int(round(max(0, y0))), int(round(min(W, x1))), int(round(min(H, y1))))
    if alpha <= .003 or x1 - x0 < 2 or y1 - y0 < 2:
        return
    if PANEL_AUDIT is not None and name and alpha > .05:
        PANEL_AUDIT.append(dict(name=name, box=(x0, y0, x1 - x0, y1 - y0)))
    roi = layer.img[y0:y1, x0:x1]
    h, w = roi.shape[:2]
    small = cv2.resize(roi, (max(1, w // 8), max(1, h // 8)), interpolation=cv2.INTER_AREA)
    frosted = cv2.resize(cv2.GaussianBlur(small, (0, 0), 1.6), (w, h), interpolation=cv2.INTER_LINEAR)
    target = frosted * (1 - opacity) + np.array(INK, np.float32) * opacity
    roi[:] = roi * (1 - alpha) + target * alpha
    if hairline:
        fx.rect(layer, x0, y0, x1, y0 + 1, PAPER, .16 * alpha)
    if accent is not None:
        fx.rect(layer, x0, y0, x0 + accent_width, y1, accent, alpha)


def chip_size(label, size=26):
    return fx.text_rgba(label, fx.DIN, size, PAPER, 1).shape[1] + 26, 38


def chip(layer, x, y, label, accent, alpha, size=26):
    w, h = chip_size(label, size)
    panel(layer, x, y, x + w, y + h, alpha, accent=accent, opacity=.9, hairline=False, accent_width=5)
    text(layer, label, x + 15, caps_top(y, h, size), size, PAPER, alpha, face=fx.DIN, track=1)
    if LABEL_AUDIT is not None and alpha > .05:
        LABEL_AUDIT.append(dict(text=label, box=(x, y, w, h)))


def stature(y):
    # Approximate on-screen player height at a reviewed foot row; used only for label/spotlight room.
    return 30 + .1 * y


BOARD_BOX = (915, 204, 870, 800)
FULL_RECT = (0, 0, W, H)
BOARD_RECT = (BOARD_BOX[0], BOARD_BOX[1], BOARD_BOX[0] + BOARD_BOX[2], BOARD_BOX[1] + BOARD_BOX[3])
# Where the camera swings for the third reading: an angle behind the attack, turned per scene.
HERO_TURN = {'build': -.42, 'combine': .38, 'release': -.5}
HERO_DRIFT, HERO_ELEVATION = .2, math.radians(23)
GOAL_CENTRE = np.array(tactical_geometry.GOAL_CENTRE)


@lru_cache(maxsize=1)
def measured():
    return tactical_geometry.measure(CLIP, GEOMETRY)


@lru_cache(maxsize=4)
def ground_model(scene_id):
    """Homography from a reviewed still to pitch metres, fitted from its visible Law 1 markings."""
    model = measured()[scene_id]
    ground = {pid: np.array(g, float) for pid, g in model['ground'].items()}
    inverse = np.linalg.inv(np.array(model['homography'], float))
    side = np.sign((inverse @ np.array([*np.mean(list(ground.values()), axis=0), 1.0]))[2])
    return inverse, side, ground


def world3d(points, z=0.0):
    """Measured ground (metres along, metres from far touchline) -> 3D world used by pitch3d."""
    points = np.atleast_2d(points)
    return np.column_stack([points[:, 0], 68 - points[:, 1], np.full(len(points), z)])


def team_of(scene, pid):
    return next(p['team'] for p in scene['players'] if p['id'] == pid)


def ease(a, b, local, start, end):
    return a.mix(b, fx.ease_in_out((local - start) / (end - start)))


def side_pose(scene):
    # A high touchline angle, like the main broadcast camera, before rising into the schematic.
    return p3.Pose(world3d(ground_model(scene['id'])[2]['carrier'])[0], 78, -math.pi / 2, math.radians(19), centre=(W / 2, H / 2))


@lru_cache(maxsize=4)
def hero_poses(scene_id):
    focus = STORY['scenes'][scene_id]['steps'][2]['focus']
    points = world3d(np.array([g for pid, g in ground_model(scene_id)[2].items() if pid in focus]))
    target = points.mean(axis=0)
    inner = (BOARD_RECT[0] + 105, BOARD_RECT[1] + 105, BOARD_RECT[2] - 105, BOARD_RECT[3] - 60)
    azimuth = -math.pi + HERO_TURN[scene_id]
    for distance in np.arange(36, 240, 2.0):
        poses = [p3.Pose(target, distance, azimuth + drift, HERO_ELEVATION) for drift in (0, HERO_DRIFT)]
        fits = True
        for pose in poses:
            camera = p3.Camera(pose)
            for z in (0, 2.9):
                cam = camera.to_camera(points + [0, 0, z])
                xy = camera.screen(cam)
                fits &= bool((cam[:, 2] > 5).all() and (xy[:, 0] > inner[0]).all() and (xy[:, 0] < inner[2]).all()
                             and (xy[:, 1] > inner[1]).all() and (xy[:, 1] < inner[3]).all())
        if fits:
            return tuple(poses)
    raise ValueError('Cannot frame the third reading inside the tactical view')


@lru_cache(maxsize=4)
def top_pose(scene_id):
    """Overhead shot framed on this still's players and tactical zones, attack pointing up the screen."""
    ground = ground_model(scene_id)[2]
    points = list(ground.values())
    for step in STORY['scenes'][scene_id]['steps']:
        for layer in step.get('layers', []):
            if layer['type'] in ('space', 'pressure'):
                points += [ground[layer['around']] + [dx, dy] for dx in (-layer['radius'], layer['radius']) for dy in (-layer['radius'], layer['radius'])]
            elif layer['type'] == 'carry':
                points.append(ground[layer['from']] + layer['offset'])
    points = np.array(points)
    low, high = points.min(axis=0), points.max(axis=0)
    # Screen height follows pitch length, screen width follows pitch width; keep room for labels.
    scale = min((BOARD_BOX[3] - 230) / max(1, high[0] - low[0]), (BOARD_BOX[2] - 260) / max(1, high[1] - low[1]))
    distance = float(np.clip(p3.FOCAL / scale, 48, p3.TOP_DISTANCE))
    target = world3d((low + high) / 2)[0]
    return p3.Pose(target, distance, -math.pi, math.pi / 2)


def camera_pose(scene, local):
    side, top, (hero_a, hero_b) = side_pose(scene), top_pose(scene['id']), hero_poses(scene['id'])
    if local < 4.2:
        return ease(side, top, local, 2.8, 4.2)
    if local < 8.4:
        return top
    if local < 9.6:
        return ease(top, hero_a, local, 8.4, 9.6)
    if local < 11.6:
        return ease(hero_a, hero_b, local, 9.6, 11.6)
    return ease(hero_b, side, local, 11.6, 12.6)


def on_still(state, points):
    """Ground metres -> pixels on the (pushed-in) reviewed still, with a validity mask."""
    inverse, side = state['inverse'], state['side']
    points = np.atleast_2d(points)
    h = np.column_stack([points, np.ones(len(points))]) @ inverse.T
    valid = h[:, 2] * side > 1e-6
    xy = h[:, :2] / np.where(np.abs(h[:, 2:3]) < 1e-9, 1e-9, h[:, 2:3])
    return state['centre'] + (xy - state['centre']) * state['zoom'], valid


def to_screen(state, points):
    """Ground metres -> screen, blending the still and the 3D view by the morph."""
    flat, valid = on_still(state, points)
    morph, camera = state['morph'], state['camera']
    if camera is None or morph <= 0:
        return flat, valid
    cam = camera.to_camera(world3d(points))
    in_front = cam[:, 2] > 1
    projected = camera.screen(np.where(in_front[:, None], cam, [[0, 0, 1]]))
    if morph >= 1:
        return projected, in_front
    return flat * (1 - morph) + projected * morph, valid & in_front


def resample(points, count=60):
    points = np.asarray(points, float)
    if len(points) < 2:
        return None
    distance = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    if distance[-1] < 1e-6:
        return None
    targets = np.linspace(0, distance[-1], count)
    return np.column_stack([np.interp(targets, distance, points[:, i]) for i in (0, 1)])


def truncate(points, fraction):
    distance = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    keep = distance <= distance[-1] * fx.clamp(fraction) + 1e-6
    cut = points[keep]
    if fraction < 1 and keep.sum() < len(points):
        i = keep.sum()
        k = (distance[-1] * fraction - distance[i - 1]) / max(1e-6, distance[i] - distance[i - 1])
        cut = np.vstack([cut, points[i - 1] + (points[i] - points[i - 1]) * k])
    return cut


def ground_curve(a, b, bend, count=90):
    a, b = np.asarray(a, float), np.asarray(b, float)
    delta = b - a
    length = np.linalg.norm(delta)
    normal = np.array([-delta[1], delta[0]]) / max(length, 1e-6)
    control = (a + b) / 2 + normal * min(bend, length * .13)
    u = np.linspace(0, 1, count)[:, None]
    return (1 - u) ** 2 * a + 2 * (1 - u) * u * control + u ** 2 * b


def head_polygon(tip, before, size):
    tangent = (tip - before) / max(1e-6, np.linalg.norm(tip - before))
    side = np.array([-tangent[1], tangent[0]])
    return np.array([tip, tip - tangent * size + side * size * .55, tip - tangent * size * .62, tip - tangent * size - side * size * .55])


def ground_arrow(state, curve, reveal, ends=(True, True), head=True):
    """Project a ground curve; on the still trim it at the foot rings, in 3D at ring radius in metres."""
    morph, camera = state['morph'], state['camera']
    versions = []
    if morph < 1:
        flat, valid = on_still(state, curve)
        if valid.all():
            keep = np.ones(len(flat), bool)
            for end, enabled in ((flat[0], ends[0]), (flat[-1], ends[1])):
                if enabled:
                    keep &= ((flat[:, 0] - end[0]) / 56) ** 2 + ((flat[:, 1] - end[1]) / 24) ** 2 > 1
            shown = resample(truncate(flat[keep], reveal)) if keep.sum() > 2 else None
            if shown is not None:
                versions.append((1 - morph, shown, head_polygon(shown[-1], shown[-4], 30)))
    if morph > 0 and camera is not None:
        keep = np.ones(len(curve), bool)
        for end, enabled in ((curve[0], ends[0]), (curve[-1], ends[1])):
            if enabled:
                keep &= np.linalg.norm(curve - end, axis=1) > 2.3
        trimmed = resample(truncate(curve[keep], reveal)) if keep.sum() > 2 else None
        if trimmed is not None:
            world = world3d(trimmed)
            if (camera.to_camera(world)[:, 2] > 1).all():
                tip_head = head_polygon(trimmed[-1], trimmed[-4], 2.1)
                versions.append((morph, camera.project(world), camera.project(world3d(tip_head))))
    if not versions:
        return None
    if len(versions) == 1:
        return versions[0][1], versions[0][2] if head else None
    (wa, pa, ha), (wb, pb, hb) = versions
    return pa * wa + pb * wb, (ha * wa + hb * wb) if head else None


def draw_option(layer, geometry, alpha, t, width, complete, color=MINT, pulse=True):
    """Dashed editorial option: dark under-stroke, flowing dashes, notched head and a travelling pulse."""
    points, head = geometry
    if alpha <= .003 or len(points) < 2:
        return
    distance = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    head_length = np.linalg.norm(head[0] - head[2]) / .62 if head is not None else 0
    shaft = [(a, b) for a, b, d in zip(points[:-1], points[1:], distance)
             if d < distance[-1] - head_length * .7 and (d - t * 46) % 40 < 24]
    for a, b in shaft:
        fx.line(layer.sharp, a, b, SHADOW, .5 * alpha, width + 5)
    if head is not None:
        poly(layer.sharp, head.mean(axis=0) + (head - head.mean(axis=0)) * 1.3, SHADOW, .5 * alpha)
    for a, b in shaft:
        fx.line(layer.sharp, a, b, color, alpha, width)
        fx.line(layer.glow, a, b, fx.scale_c(color, alpha * .45), 1, width + 4)
    if head is not None:
        poly(layer.sharp, head, color, alpha)
    if complete and pulse:
        # A light pulse runs from the passer to the option, reinforcing direction without implying a pass happened.
        u = (t * .55) % 1
        dot = points[min(len(points) - 1, int(u * (len(points) - 1)))]
        fade = math.sin(u * math.pi)
        fx.ellipse(layer.sharp, dot, (6.5, 6.5), PAPER, alpha * fade, -1)
        fx.ellipse(layer.glow, dot, (12, 12), fx.scale_c(color, alpha * fade), 1, -1)


def draw_carry(layer, geometry, alpha, t, width):
    """A solid gold carry arrow with chevrons flowing along it: space to run with the ball, not a recorded run."""
    points, head = geometry
    if alpha <= .003 or len(points) < 2:
        return
    stop = len(points) - 3
    for a, b in zip(points[:stop - 1], points[1:stop]):
        fx.line(layer.sharp, a, b, SHADOW, .45 * alpha, width + 6)
    for a, b in zip(points[:stop - 1], points[1:stop]):
        fx.line(layer.sharp, a, b, GOLD, alpha, width)
        fx.line(layer.glow, a, b, fx.scale_c(GOLD, alpha * .5), 1, width + 6)
    poly(layer.sharp, head.mean(axis=0) + (head - head.mean(axis=0)) * 1.3, SHADOW, .45 * alpha)
    poly(layer.sharp, head, GOLD, alpha)
    for k in range(3):
        u = ((t * .7 + k / 3) % 1) * .8
        i = int(u * (len(points) - 2))
        tip, before = points[i + 1], points[max(0, i - 2)]
        chevron = head_polygon(tip, before, 13)
        fx.line(layer.sharp, chevron[1], chevron[0], INK, .8 * alpha * math.sin(u / .8 * math.pi), 3)
        fx.line(layer.sharp, chevron[3], chevron[0], INK, .8 * alpha * math.sin(u / .8 * math.pi), 3)


def draw_zone(layer, outline, color, alpha):
    if alpha <= .003 or outline is None or len(outline) < 3:
        return
    poly(layer.sharp, outline, color, .17 * alpha)
    closed = np.vstack([outline, outline[:1]])
    for a, b in zip(closed[:-1], closed[1:]):
        fx.line(layer.sharp, a, b, color, .85 * alpha, 2)
    poly(layer.glow, outline, fx.scale_c(color, .18 * alpha), 1)


def zone_outline(state, layer, grow):
    ground = state['ground']
    if layer['type'] == 'goal-side':
        reach = np.linalg.norm(ground[layer['ball']] - GOAL_CENTRE) * grow
        angles = np.linspace(math.pi / 2, 3 * math.pi / 2, 72)
        arc = np.column_stack([GOAL_CENTRE[0] + reach * np.cos(angles), np.clip(GOAL_CENTRE[1] + reach * np.sin(angles), 0, 68)])
        shape = np.vstack([[105, arc[0, 1]], arc, [105, arc[-1, 1]]])
        anchor = np.array([GOAL_CENTRE[0] - reach, GOAL_CENTRE[1]])
    else:
        angles = np.linspace(0, 2 * math.pi, 64, endpoint=False)
        centre = ground[layer['around']]
        shape = centre + layer['radius'] * grow * np.column_stack([np.cos(angles), np.sin(angles)])
        anchor = centre
    screen, valid = to_screen(state, shape)
    return (screen if valid.all() else None), to_screen(state, anchor)[0][0]


def ground_marker(layer, point, color, alpha, active, t, flat, ping=-1, carrier=False, zoom=1, tilt=1):
    """Perspective foot ring on footage that settles into a disc on the pitch view."""
    if alpha <= .003:
        return
    r = (40 if active else 26) * (1 - flat) + (21 if active else 14) * zoom * flat
    ratio = .32 * (1 - flat) + tilt * flat
    axes = lambda k: (r * k, r * ratio * k)
    if carrier:
        fx.ellipse(layer.glow, point, axes(1.7), fx.scale_c(GOLD, .36 * flat * alpha), 1, -1)
    if active:
        fx.ellipse(layer.glow, point, axes(1.1), fx.scale_c(color, (.08 + .32 * flat) * alpha), 1, 8)
    fx.ellipse(layer.sharp, point, axes(1.08), SHADOW, (.4 + .3 * flat) * alpha, 5 if active else 3)
    fill = (.30 if active else .10) * (1 - flat) + (.95 if active else .32) * flat
    fx.ellipse(layer.sharp, point, axes(1), color, fill * alpha, -1)
    rim = fx.mix(color, PAPER, flat * .6) if active else color
    fx.ellipse(layer.sharp, point, axes(1), rim, (.95 if active else .55 + .35 * flat) * alpha, 3 if active else 2)
    if carrier:
        fx.ellipse(layer.sharp, point, axes(1.36), GOLD, .95 * alpha, 2)
        for a in range(0, 360, 120):
            start = a + t * 50
            fx.ellipse(layer.sharp, point, axes(1.36), GOLD, alpha, 4, start, start + 34)
    if 0 <= ping < 1:
        fx.ellipse(layer.sharp, point, axes(1 + .9 * fx.ease_out(ping)), PAPER, .8 * alpha * (1 - ping), 2)


def spotlight(image, points, strength):
    """Dim everything except soft pools of light around the reviewed focus players."""
    if strength < .003:
        return image
    mask = np.zeros((H // 4, W // 4), np.float32)
    for x, y in points:
        body = stature(y)
        cv2.ellipse(mask, (round(x / 4), round((y - body * .45) / 4)),
                    (round((body * .55 + 40) / 4), round((body * .7 + 34) / 4)), 0, 0, 360, 1, -1)
    mask = np.clip(cv2.GaussianBlur(mask, (0, 0), 13) * 1.6, 0, 1)
    mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    pixels = image.astype(np.float32)
    grey = pixels.mean(axis=2, keepdims=True)
    muted = (grey + (pixels - grey) * .88) * .5
    k = strength * (1 - mask)
    return np.clip(pixels * (1 - k) + muted * k, 0, 255).astype(np.uint8)


def backdrop(image, amount):
    small = cv2.resize(image, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    soft = cv2.resize(cv2.GaussianBlur(small, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    soft = soft * .3 + np.array(INK, np.float32) * .3
    return (image * (1 - amount) + soft * amount).astype(np.uint8)


def overlaps(a, b, pad=4):
    return a[0] < b[0] + b[2] + pad and a[0] + a[2] + pad > b[0] and a[1] < b[1] + b[3] + pad and a[1] + a[3] + pad > b[1]


def layer_key(layer):
    return json.dumps(layer, sort_keys=True)


def scene_state(scene, local):
    """Everything about a freeze frame's geometry: camera, marker positions, figure heights and tactical layers."""
    plan = STORY['scenes'][scene['id']]
    step = min(2, int(local / STEP))
    morph = fx.ease_in_out((local - 2.8) / 1.0) * (1 - fx.ease_in_out((local - 11.6) / 1.0))
    players = {p['id']: p for p in scene['players']}
    inverse, side, ground = ground_model(scene['id'])
    # A slow push towards the carrier; it returns to 1.0 before the cut back to live footage.
    zoom = 1 + .045 * fx.ease_in_out(local / 2.8) * (1 - fx.ease_in_out((local - 11.6) / 1.0))
    centre = np.clip(np.array(players['carrier']['foot']) * 1.5, (W * .3, H * .3), (W * .7, H * .7))
    camera_xy = {pid: centre + (np.array(p['foot']) * 1.5 - centre) * zoom for pid, p in players.items()}
    state = dict(scene=scene, plan=plan, step=step, morph=morph, zoom=zoom, centre=centre, camera_xy=camera_xy,
                 inverse=inverse, side=side, ground=ground, world={pid: world3d(g)[0] for pid, g in ground.items()},
                 camera=None, positions=dict(camera_xy), tops={pid: xy[1] - stature(xy[1]) for pid, xy in camera_xy.items()},
                 visible=set(players), rise=0, window=FULL_RECT)
    if morph > 0:
        camera = p3.Camera(camera_pose(scene, local))
        rise = fx.ease_in_out((math.degrees(math.pi / 2 - camera.pose.elevation) - 4) / 26)
        window = tuple(a + (b - a) * morph for a, b in zip(FULL_RECT, BOARD_RECT))
        state.update(camera=camera, rise=rise, window=window, visible=set())
        for pid, point in state['world'].items():
            if camera.to_camera(point)[0, 2] < 2:
                continue
            state['visible'].add(pid)
            projected = camera.project(point)[0]
            state['positions'][pid] = camera_xy[pid] * (1 - morph) + projected * morph
            head = camera.project(point + [0, 0, p3.FIGURE_HEIGHT * rise])[0][1] - 4 if rise > .01 else projected[1]
            state['tops'][pid] = state['tops'][pid] * (1 - morph) + head * morph
    reading = plan['steps'][step]
    previous = plan['steps'][step - 1] if step else {'routes': [], 'layers': []}
    previous_layers = {layer_key(l) for l in previous.get('layers', [])}
    step_local = local - step * STEP
    grow_in = lambda carried: 1 if carried else fx.ease_out((step_local - .25) / .9)
    state['options'], state['marks'], state['zones'] = [], [], []
    for i, item in enumerate(scene['routes']):
        # A spatial relation is not a pass or a defensive line: only reviewed options are drawn, as dashed arrows.
        if item['kind'] != 'option' or i not in reading['routes']:
            continue
        reveal = grow_in(i in previous['routes'])
        if reveal > .003 and {item['a'], item['b']} <= state['visible']:
            geometry = ground_arrow(state, ground_curve(ground[item['a']], ground[item['b']], 2.6), reveal)
            if geometry is not None:
                state['options'].append((geometry, reveal >= 1))
    for layer in reading.get('layers', []):
        reveal = grow_in(layer_key(layer) in previous_layers)
        if reveal <= .003:
            continue
        kind = layer['type']
        if kind == 'covered':
            a, b, by = ground[layer['from']], ground[layer['to']], ground[layer['by']]
            t, _ = tactical_geometry.lane_offset(a, b, by)
            block = a + (b - a) * t
            lane = ground_curve(a, block, 0)
            geometry = ground_arrow(state, lane, reveal, ends=(True, False), head=False)
            normal = np.array([-(b - a)[1], (b - a)[0]]) / np.linalg.norm(b - a)
            bar, bar_ok = to_screen(state, np.array([block - normal * 2.4, block + normal * 2.4]))
            rest = ground_arrow(state, ground_curve(block, b, 0), 1, ends=(False, True), head=False) if reveal >= 1 else None
            state['marks'].append(('covered', geometry, bar if bar_ok.all() and reveal >= .98 else None, rest))
        elif kind == 'carry':
            start = ground[layer['from']]
            geometry = ground_arrow(state, ground_curve(start, start + np.array(layer['offset'], float), 1.2), reveal, ends=(True, False))
            state['marks'].append(('carry', geometry))
        else:
            outline, anchor = zone_outline(state, layer, fx.ease_out(reveal))
            color = GOLD if kind == 'space' else CORAL
            state['zones'].append((outline, color, reveal, layer.get('label'), anchor))
    state['route_boxes'] = [(x - 12, y - 12, 24, 24) for geometry, _ in state['options'] for x, y in geometry[0][::5]]
    for mark in state['marks']:
        if mark[1] is not None:
            state['route_boxes'] += [(x - 12, y - 12, 24, 24) for x, y in mark[1][0][::5]]
    return state


def label_slots(x, y, top, w, h, on_board):
    if on_board:
        high = min(top, y - 24)
        mid = (high + y + 24) / 2
        return [((x + 30, mid - h / 2), None), ((x - 30 - w, mid - h / 2), None),
                ((x - w / 2, high - 10 - h), None), ((x - w / 2, y + 32), None),
                ((x + 24, high - 4 - h), None), ((x + 24, y + 22), None),
                ((x - 24 - w, high - 4 - h), None), ((x - 24 - w, y + 22), None)]
    s = y - top
    return [((x - w / 2, y - s - 20 - h), 'pointer'),
            ((x + s * .3 + 22, y - s * .62 - h / 2), (x + s * .3 + 22, y - s * .62, x + s * .2, y - s * .62)),
            ((x - s * .3 - 22 - w, y - s * .62 - h / 2), (x - s * .3 - 22, y - s * .62, x - s * .2, y - s * .62)),
            ((x - w / 2, y + 24), (x, y + 24, x, y + 14))]


def zone_slots(outline, anchor, w, h):
    if outline is None:
        return [((anchor[0] - w / 2, anchor[1] - h / 2), None)]
    x0, y0 = outline.min(axis=0)
    x1, y1 = outline.max(axis=0)
    cx = (x0 + x1) / 2
    return [((cx - w / 2, y0 - h - 6), None), ((cx - w / 2, y1 + 6), None), ((x1 + 8, (y0 + y1) / 2 - h / 2), None),
            ((x0 - 8 - w, (y0 + y1) / 2 - h / 2), None), ((anchor[0] - w / 2, anchor[1] - h / 2), None)]


def role_label(state, pid):
    return state['plan']['steps'][state['step']].get('labels', {}).get(pid, ROLE_LABELS.get(pid, 'DEF'))


def choose_labels(state, blocked, preferred=None):
    """Pick a slot per focus player and zone, avoiding labels, panels, players and arrows; prefer a settled choice."""
    on_board = state['morph'] > .5
    positions, tops = state['positions'], state['tops']
    bodies = {}
    for pid in state['visible']:
        x, y = positions[pid]
        if on_board:
            high = min(tops[pid], y - 24)
            bodies[pid] = (x - 26, high - 4, 52, y + 28 - high)
        else:
            s = y - tops[pid]
            bodies[pid] = (x - s * .3 - 8, y - s - 6, s * .6 + 16, s + 18)
    frame = BOARD_BOX if on_board else (0, 0, W, 1018)
    focus = [pid for pid in sorted(state['plan']['steps'][state['step']]['focus'], key=lambda pid: pid != 'carrier')
             if pid in state['visible']]
    items = [(pid, role_label(state, pid), label_slots(*positions[pid], tops[pid], *chip_size(role_label(state, pid)), on_board))
             for pid in focus]
    for i, (outline, _, reveal, label, anchor) in enumerate(state['zones']):
        if label:
            items.append((f'zone-{i}', label, zone_slots(outline, anchor, *chip_size(label))))
    chosen, placed = {}, []
    for key, label, slots in items:
        w, h = chip_size(label)
        def cost(index):
            (xx, yy), _ = slots[index]
            box = (xx, yy, w, h)
            inside = frame[0] <= xx and frame[1] <= yy and xx + w <= frame[0] + frame[2] and yy + h <= frame[1] + frame[3]
            sticky = 0 if not preferred or preferred.get(key) in (None, index) else 60
            return (1000 * sum(overlaps(box, b) for b in placed) + 600 * sum(overlaps(box, b) for b in blocked)
                    + (0 if inside else 1000) + 120 * sum(overlaps(box, b, 0) for k, b in bodies.items() if k != key)
                    + 30 * any(overlaps(box, b, 0) for b in state['route_boxes']) + 3 * index + sticky)
        best = min(range(len(slots)), key=cost)
        (xx, yy), leader = slots[best]
        placed.append((xx, yy, w, h))
        chosen[key] = (best, (xx, yy, w, h), leader, label)
    return chosen


def place_labels(state, local, alpha, blocked):
    morph, plan, step = state['morph'], state['plan'], state['step']
    label_alpha = alpha * max(fx.clamp(1 - morph / .2), fx.clamp((morph - .8) / .2))
    if label_alpha < .003:
        return []
    preferred = None
    if morph > .5:
        # While the camera moves, keep each label in the slot it will occupy once the shot settles.
        reference = scene_state(state['scene'], 4.3 if local < 8.4 else 9.7)
        preferred = {key: slot[0] for key, slot in choose_labels(reference, blocked).items()}
    previous = plan['steps'][step - 1] if step else {'focus': [], 'labels': {}}
    step_local = local - step * STEP
    jobs = []
    for key, (_, (xx, yy, w, h), leader, label) in choose_labels(state, blocked, preferred).items():
        if key.startswith('zone-'):
            _, color, reveal, _, anchor = state['zones'][int(key[5:])]
            appear = fx.ease_out((reveal - .5) / .5)
            jobs.append(dict(x=xx, y=yy - 8 * (1 - appear), w=w, h=h, label=label, color=color,
                             alpha=label_alpha * appear, leader=None, anchor=anchor))
            continue
        team = MINT if team_of(state['scene'], key) == 'MCI' else CORAL
        carried = key in previous['focus'] and previous.get('labels', {}).get(key) == plan['steps'][step].get('labels', {}).get(key)
        appear = 1 if carried else fx.ease_out((step_local - (.3 if step == 0 else .15)) / .35)
        jobs.append(dict(x=xx, y=yy - 8 * (1 - appear), w=w, h=h, label=label, color=team, alpha=label_alpha * appear,
                         leader=leader, anchor=state['positions'][key]))
    return jobs


def clip_to(layer, rect):
    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    for canvas in (layer.sharp, layer.glow):
        canvas[:max(0, y0)] = 0
        canvas[max(0, y1):] = 0
        canvas[:, :max(0, x0)] = 0
        canvas[:, max(0, x1):] = 0


def pitch_view(layer, state, alpha):
    """The 3D schematic inside a window that contracts from full frame into the tactical panel."""
    morph, camera = state['morph'], state['camera']
    a = alpha * fx.ease_out(morph / .7)
    if camera is None or a < .003:
        return
    x0, y0, x1, y1 = (int(round(v)) for v in state['window'])
    # A graded studio backdrop rather than a flat void above the horizon in tilted views.
    shade = np.linspace(0, 1, max(1, y1 - y0))[:, None, None]
    sky = np.array(fx.hexc('050d0c'), np.float32) * (1 - shade) + np.array(fx.hexc('0f2a25'), np.float32) * shade
    roi = layer.img[y0:y1, x0:x1]
    roi[:] = roi * (1 - .92 * a) + sky * .92 * a
    horizon = camera.horizon()
    if horizon is not None and state['rise'] > .01:
        fx.line(layer.glow, (x0, horizon), (x1, horizon), fx.scale_c(MINT, .3 * a * state['rise']), 1, 46)
    p3.draw_pitch(layer.sharp, camera, a, (fx.hexc('0d2a25'), TURF, TURF_ALT, CHALK))
    clip_to(layer, state['window'])


def players_view(layer, state, local, output, alpha):
    plan, step, morph, camera = state['plan'], state['step'], state['morph'], state['camera']
    reading = plan['steps'][step]
    focus = set(reading['focus'])
    previous_focus = set(plan['steps'][step - 1]['focus']) if step else set()
    step_local = local - step * STEP
    team = {p['id']: MINT if p['team'] == 'MCI' else CORAL for p in state['scene']['players']}
    for outline, color, reveal, _, _ in state['zones']:
        draw_zone(layer, outline, color, alpha * fx.clamp(reveal * 2))
    standing = camera is not None and state['rise'] > .01
    if standing:
        for pid in state['visible']:
            p3.ground_shadow(layer.img, camera, state['world'][pid], morph * alpha * (1 if pid in focus else .6), state['rise'])
            if pid in focus:
                p3.beam(layer.glow, camera, state['world'][pid], team[pid], .5 * morph * alpha, state['rise'])
    width = round(6 - morph)
    for mark in state['marks']:
        if mark[0] == 'covered':
            _, geometry, bar, rest = mark
            if rest is not None:
                draw_option(layer, (rest[0], None), .6 * alpha, output, max(3, width - 1), False, DIM, pulse=False)
            if geometry is not None:
                draw_option(layer, (geometry[0], None), alpha, output, width, False, CORAL, pulse=False)
        elif mark[1] is not None:
            draw_carry(layer, mark[1], alpha, output, width + 1)
    for geometry, complete in state['options']:
        draw_option(layer, geometry, alpha, output, width, complete)
    order = sorted(state['visible'], key=lambda pid: (pid in focus, pid == 'carrier'))
    for pid in order:
        active = pid in focus
        entry = local - .2 if step == 0 else step_local - .1
        ping = entry / .9 if active and pid not in previous_focus else -1
        # Rings tighten as the figures stand, so the player, not the marker, carries the 3D view.
        zoom = min(1.15, camera.scale(state['world'][pid])) * (1 - .35 * state['rise']) if camera else 1
        tilt = camera.tilt(state['world'][pid]) if camera else 1
        ground_marker(layer, state['positions'][pid], team[pid], alpha * (1 if active else .62), active, output, morph,
                      ping, pid == 'carrier', zoom, tilt)
    for mark in state['marks']:
        # The block bar sits above the defender's marker: it is the point of the covered-lane graphic.
        if mark[0] == 'covered' and mark[2] is not None:
            a, b = mark[2]
            fx.line(layer.sharp, a, b, SHADOW, .7 * alpha, width + 9)
            fx.line(layer.sharp, a, b, CORAL, alpha, width + 3)
            fx.line(layer.sharp, (a + b) / 2 - (b - a) * .08, (a + b) / 2 + (b - a) * .08, PAPER, alpha, width + 3)
            fx.line(layer.glow, a, b, fx.scale_c(CORAL, .6 * alpha), 1, width + 12)
    if standing:
        # Paint far figures first so nearer ones overlap them.
        for pid in sorted(state['visible'], key=lambda pid: -camera.to_camera(state['world'][pid])[0, 2]):
            p3.figure(layer.sharp, camera, state['world'][pid], team[pid], morph * alpha * (1 if pid in focus else .7),
                      state['rise'], fx.scale_c)
    if camera is not None:
        clip_to(layer, state['window'])


def draw_labels(layer, jobs):
    for job in jobs:
        a, x, y, w, h = job['alpha'], job['x'], job['y'], job['w'], job['h']
        if a <= .003:
            continue
        if job['leader'] == 'pointer':
            cx = job['anchor'][0]
            poly(layer.sharp, [(cx - 9, y + h), (cx + 9, y + h), (cx, y + h + 10)], INK, .9 * a)
        elif job['leader']:
            x0, y0, x1, y1 = job['leader']
            fx.line(layer.sharp, (x0, y0), (x1, y1), PAPER, .75 * a, 2)
            fx.ellipse(layer.sharp, (x1, y1), (3, 3), PAPER, a, -1)
        chip(layer, x, y, job['label'], job['color'], a)


def header(layer, scene, plan, alpha, local):
    kicker, title = 'PITCHPRISM / TACTICAL STUDIO', plan['title']
    width = max(fx.text_w(kicker, fx.DIN, 22, 3), fx.text_w(title, DISPLAY_ITALIC, 64, 2)) + 66
    grow = fx.ease_out(local / .45)
    panel(layer, 56, 40, 56 + width * (.25 + .75 * grow), 156, alpha, accent=CYAN, name='header')
    gradient_bar(layer, 56, 152, 56 + width * (.25 + .75 * grow), 156, alpha)
    text(layer, kicker, 86, caps_top(52, 22, 22), 22, MINT, alpha, face=fx.DIN, track=3, reveal=fx.ease_out((local - .08) / .4))
    text(layer, title, 84, caps_top(86, 52, 64), 64, PAPER, alpha, face=DISPLAY_ITALIC, track=2, reveal=fx.ease_out((local - .16) / .5))
    clock = 'REVIEWED FRAME / ' + scene['clock']
    note = 'EXCERPT ONLY / NO OFFICIAL EVENT FEED'
    parts = [(f"SOURCE {scene['second']:.2f}s   |   ", DIM), ('MCI', MINT), ('  0 - 0  ', PAPER), ('NEW', CORAL)]
    score = sum(fx.text_w(value, fx.DIN, 26, 1) for value, _ in parts)
    right = max(fx.text_w(clock, fx.DIN, 26, 1), score, fx.text_w(note, fx.DIN, 17, 1)) + 56
    side = alpha * fx.ease_out((local - .12) / .4)
    panel(layer, 1864 - right, 40, 1864, 156, side, name='header-info')
    text(layer, clock, 1836, caps_top(50, 26, 26), 26, MINT, side, face=fx.DIN, anchor='rt', track=1)
    x = 1836 - score
    for value, color in parts:
        text(layer, value, x, caps_top(86, 26, 26), 26, color, side, face=fx.DIN, track=1)
        x += fx.text_w(value, fx.DIN, 26, 1)
    text(layer, note, 1836, caps_top(122, 20, 17), 17, DIM, side, face=fx.DIN, anchor='rt', track=1)


def reading_list(layer, plan, step, morph, alpha, local, output):
    a = morph * alpha
    head = fx.ease_out((morph - .2) / .5)
    text(layer, 'READ THE GAME', 80, caps_top(232 + 14 * (1 - head), 50, 54), 54, MINT, a * head, face=fx.DIN, track=2)
    text(layer, plan['subtitle'], 81, 300, 25, DIM, a * head)
    for i, item in enumerate(plan['steps']):
        enter = fx.ease_out((morph - .3 - i * .12) / .4)
        if enter < .003:
            continue
        yy, dx, ca = 372 + i * 177, -40 * (1 - enter), a * enter
        active = i == step
        panel(layer, 76 + dx, yy - 12, 854 + dx, yy + 157, ca, opacity=.9 if active else .8, name=f'step-{i}')
        if active:
            begin = i * STEP
            grow = fx.ease_out((local - begin) / .35) if i else 1
            span = 169 * (1 - grow) / 2
            fx.rect(layer, 76 + dx, yy - 12 + span, 82 + dx, yy + 157 - span, MINT, ca)
            progress = fx.clamp((local - begin) / ((FREEZE if i == 2 else begin + STEP) - begin))
            fx.rect(layer, 82 + dx, yy + 154, 82 + dx + 772 * progress, yy + 157, MINT, .7 * ca)
        row = ca * (1 if active else .6)
        text(layer, f'{i + 1:02}', 102 + dx, caps_top(yy, 46, 51), 51, MINT if active else DIM, row, face=fx.DIN)
        text(layer, item['title'], 174 + dx, caps_top(yy + 4, 34, 37), 37, PAPER, row, face=fx.DIN, track=1)
        paragraph(layer, item['text'], 175 + dx, yy + 46, width=640, size=25, color=PAPER if active else DIM,
                  alpha=row, line_height=32, max_height=104)
    mark(layer, 118, 958, 72, a * head, spin=.35 * math.sin(output * 1.4))
    text(layer, 'PITCHPRISM / YOUR FOOTBALL COMPANION', 172, caps_top(940, 36, 22), 22, DIM, a * head, face=LABEL, track=4)
    text(layer, 'TACTICAL VIEW / SCHEMATIC', 930, caps_top(172, 22, 22), 22, MINT, a * head, face=fx.DIN, track=2)
    label = 'ATTACK TO GOAL'
    text(layer, label, 1770, caps_top(172, 22, 20), 20, DIM, a * head, face=fx.DIN, anchor='rt', track=2)
    cx = 1770 - fx.text_w(label, fx.DIN, 20, 2) - 14
    poly(layer.sharp, [(cx, 175), (cx + 8, 190), (cx - 8, 190)], MINT, a * head)


def camera_caption(layer, reading, step, alpha, morph):
    """Reading lower third on the footage: a big italic step number, the title, then the explanation."""
    a = alpha * fx.clamp(1 - morph / .45)
    if a < .003:
        return
    drop = 60 * fx.ease_in_out(morph / .45)
    number, title = f'{step + 1:02}', reading['title']
    lines = wrap(reading['text'], 1000, 29)
    number_w = fx.text_w(number, DISPLAY_ITALIC, 64, 1)
    width = min(1180, max(number_w + 30 + fx.text_w(title, DISPLAY_ITALIC, 46, 2), max(fx.text_w(row, BODY, 29) for row in lines)) + 80)
    height = 86 + 41 * len(lines) + 18
    top = 990 - height + drop
    panel(layer, 72, top, 72 + width, top + height, a, opacity=.9, hairline=False, name='caption')
    poly(layer.sharp, [(72, top), (94, top), (82, top + height), (60, top + height)], CYAN, a)
    gradient_bar(layer, 72, top + height - 4, 72 + width, top + height, a)
    text(layer, number, 110, caps_top(top + 14, 64, 64), 64, CYAN, a, face=DISPLAY_ITALIC, track=1)
    text(layer, title, 110 + number_w + 30, caps_top(top + 20, 50, 46), 46, PAPER, a, face=DISPLAY_ITALIC, track=2)
    for i, row in enumerate(lines):
        text(layer, row, 112, top + 84 + i * 41, 29, PAPER, a, max_width=1000)


def footer(layer, local, alpha):
    x0, x1, y = 74, 1846, 1028
    fx.rect(layer, x0, y, x1, y + 3, DIM, .22 * alpha)
    fx.rect(layer, x0, y, x0 + (x1 - x0) * fx.clamp(local / FREEZE), y + 3, MINT, alpha)
    for k in (1, 2):
        tick = x0 + (x1 - x0) * k * STEP / FREEZE
        fx.rect(layer, tick - 1, y - 5, tick + 1, y + 8, PAPER, .55 * alpha)
    x, base = 76, 1044
    centre = base + 11
    legend = (('dot', MINT, 'CITY'), ('dot', CORAL, 'NEWCASTLE'), ('dash', MINT, 'OPTION, NOT A RECORDED PASS'),
              ('block', CORAL, 'COVERED LANE'), ('solid', GOLD, 'SPACE TO CARRY'), ('zone', GOLD, 'ZONE'),
              ('none', DIM, 'SCHEMATIC FROM PITCH MARKINGS, NOT TRACKING'))
    for kind, color, label in legend:
        if kind == 'dot':
            fx.ellipse(layer.sharp, (x + 7, centre), (6.5, 6.5), color, alpha, -1)
            x += 22
        elif kind in ('dash', 'block', 'solid'):
            if kind == 'solid':
                fx.line(layer.sharp, (x, centre), (x + 20, centre), color, alpha, 3)
            else:
                for dash in (0, 12):
                    fx.line(layer.sharp, (x + dash, centre), (x + dash + 7, centre), color, alpha, 3)
            if kind == 'block':
                fx.line(layer.sharp, (x + 27, centre - 7), (x + 27, centre + 7), color, alpha, 4)
            else:
                poly(layer.sharp, [(x + 32, centre), (x + 23, centre - 6), (x + 23, centre + 6)], color, alpha)
            x += 42
        elif kind == 'zone':
            fx.ellipse(layer.sharp, (x + 10, centre), (10, 6), color, .25 * alpha, -1)
            fx.ellipse(layer.sharp, (x + 10, centre), (10, 6), color, alpha, 2)
            x += 28
        text(layer, label, x, caps_top(base, 22, 18), 18, DIM, alpha, face=fx.DIN, track=2)
        x += fx.text_w(label, fx.DIN, 18, 2) + 30


def freeze(scene, local, output):
    state = scene_state(scene, local)
    plan, step, morph = state['plan'], state['step'], state['morph']
    reading = plan['steps'][step]
    alpha = min(fx.ease_out(local / .35), fx.ease_out((FREEZE - local) / .35))
    image = still(scene['second'])
    zoom, centre = state['zoom'], state['centre']
    if zoom > 1.0005:
        matrix = np.float32([[zoom, 0, centre[0] * (1 - zoom)], [0, zoom, centre[1] * (1 - zoom)]])
        image = cv2.warpAffine(image, matrix, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    image = spotlight(image, [state['camera_xy'][i] for i in reading['focus']], .78 * alpha * (1 - morph))
    if morph > .003:
        image = backdrop(image, morph)
    layer = fx.Layers(image)
    pitch_view(layer, state, alpha)
    # Compose the field before highlights, so translucent field fills never cover the marks.
    layer = fx.Layers(layer.compose(.3))
    players_view(layer, state, local, output, alpha)
    # Burn lines/glow first; typography must sit above every arrow and marker.
    layer = fx.Layers(layer.compose(.55))
    if morph > .4:
        x0, y0, x1, y1 = state['window']
        edge = alpha * fx.ease_out((morph - .4) / .6)
        for p, q in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            fx.line(layer.sharp, p, q, MINT, .45 * edge, 2)
    header(layer, scene, plan, alpha, local)
    blocked = [(56, 40, 1808, 116)]
    if morph < .5:
        blocked.append((72, 800, 1130, 190))
    draw_labels(layer, place_labels(state, local, alpha, blocked))
    if morph > .003:
        reading_list(layer, plan, step, morph, alpha, local, output)
    camera_caption(layer, reading, step, alpha, morph)
    footer(layer, local, alpha)
    image = layer.compose(.4)
    if local < .3:
        # Freeze-frame flash: a short exposure lift marks the moment the picture stops.
        image = np.clip(image.astype(np.float32) + 70 * (1 - local / .3) ** 2, 0, 255).astype(np.uint8)
    return image


@lru_cache(maxsize=4)
def graded(second, blur, gain, sat):
    return fx.grade(cv2.GaussianBlur(still(second), (0, 0), blur), sat=sat, gain=gain, vig=.55)


_GRID = None


def grid():
    global _GRID
    if _GRID is None:
        _GRID = np.mgrid[0:H, 0:W].astype(np.float32)
    return _GRID


def spectrum(t):
    """Cyan -> green -> magenta, the three rays of the mark."""
    stops = (CYAN, GREEN, MAGENTA)
    t = fx.clamp(t) * 2
    i = min(1, int(t))
    return fx.mix(stops[i], stops[i + 1], t - i)


def gradient_bar(layer, x0, y0, x1, y1, alpha, start=0.0, end=1.0):
    """A thin spectrum bar: the signature rule of the identity."""
    x0, x1 = int(round(x0)), int(round(x1))
    if alpha <= .003 or x1 - x0 < 1:
        return
    span = np.linspace(start, end, x1 - x0)
    colours = np.array([spectrum(u) for u in span], np.float32)[None]
    roi = layer.img[int(y0):int(y1), x0:x1]
    roi[:] = roi * (1 - alpha) + colours * alpha


def slash(canvas, lead, width, color, alpha, slant=320):
    poly(canvas, [(lead, 0), (lead + width, 0), (lead + width - slant, H), (lead - slant, H)], color, alpha)


def stinger(cover, revealed, progress):
    """Signature transition: three spectrum blades sweep across, the next picture opens behind the last one."""
    rows, cols = grid()
    blades = ((CYAN, 0, 150), (GREEN, .08, 110), (MAGENTA, .16, 190))
    lead = lambda delay: -500 + 2900 * fx.ease_in_out((progress - delay) / (1 - .16))
    edge = lead(.16) - 320 * rows / H
    mask = np.clip((edge - cols) / 2 + .5, 0, 1)[..., None]
    layer = fx.Layers((cover.astype(np.float32) * (1 - mask) + revealed.astype(np.float32) * mask).astype(np.uint8))
    for color, delay, width in blades:
        x = lead(delay)
        slash(layer.sharp, x, width, color, .92)
        slash(layer.glow, x, width, fx.scale_c(color, .55), 1)
    slash(layer.sharp, lead(.16) + 196, 14, PAPER, .9)
    return layer.compose(.45)


def light_streaks(layer, local, alpha, seed=7):
    """Fast diagonal light streaks behind the title, like a stadium-lit graphics package."""
    rng = np.random.default_rng(seed)
    for _ in range(14):
        speed, offset, y = rng.uniform(900, 1700), rng.uniform(0, 2600), rng.uniform(0, H)
        length, colour = rng.uniform(180, 520), spectrum(rng.uniform(0, 1))
        x = (offset + speed * local) % 2600 - 400
        a, b = np.array([x, y]), np.array([x + length, y - length * .32])
        fx.line(layer.glow, a, b, fx.scale_c(colour, .55 * alpha), 1, 6)
        fx.line(layer.sharp, a, b, colour, .35 * alpha, 2)


def mark(layer, x, y, size, alpha, spin=0.0):
    """The PitchPrism mark, optionally turning in on its vertical axis like a 3D badge."""
    if alpha <= .003:
        return
    scale = size / _BUDDY.shape[1]
    squash = max(.04, abs(math.cos(spin)))
    rgba = cv2.resize(_BUDDY, None, fx=scale * squash, fy=scale, interpolation=cv2.INTER_AREA)
    if math.cos(spin) < 0:
        rgba = rgba[:, ::-1]
    layer.paste(rgba, x, y, alpha=alpha, anchor='c')
    shine = fx.clamp(1 - abs(spin) / 1.2)
    if 0 < shine < 1:
        fx.ellipse(layer.glow, (x, y), (size * .55 * squash, size * .55), fx.scale_c(PAPER, .5 * shine * alpha), 1, -1)


def kinetic(layer, value, x, y, size, color, alpha, local, start, face=None, track=6, anchor='lt', max_width=None):
    """Title letters snap up from below one by one, with a short motion smear, like a sports title."""
    face = face or DISPLAY_ITALIC
    if alpha <= .003:
        return
    text(layer, value, x, y, size, color, alpha, face=face, track=track, anchor=anchor, max_width=max_width, reveal=0)
    raster = fx.text_rgba(value, face, size, color, track)
    width = raster.shape[1]
    left = x - width / 2 if anchor == 'c' else x
    top = y - raster.shape[0] / 2 if anchor == 'c' else y
    font = fx.font(face, size)
    cursor = 2
    for i, ch in enumerate(value):
        advance = font.getlength(ch) + track
        if ch != ' ':
            k = fx.ease_out((local - start - i * .035) / .32)
            if k > .003:
                glyph = raster[:, int(cursor):int(min(width, cursor + advance + 4))]
                rise = 46 * (1 - k)
                layer.paste(glyph, left + cursor, top + rise, alpha=alpha * k)
                if k < .9:
                    layer.paste(glyph, left + cursor, top + rise + 18, alpha=alpha * k * .25)
        cursor += advance


def intro(local):
    """Cold open: lights, spectrum blades, a spinning mark, then a kinetic title before the stinger into play."""
    fade = fx.ease_out(local / .25)
    background = graded(0, 9, .2, .3).astype(np.float32)
    tint = np.array(INK, np.float32) * .55
    layer = fx.Layers((background * .45 + tint).clip(0, 255).astype(np.uint8))
    layer.img *= fade
    light_streaks(layer, local, fade)
    for i, color in enumerate((CYAN, GREEN, MAGENTA)):
        sweep = fx.ease_in_out((local - .05 - i * .07) / .55)
        if 0 < sweep < 1:
            slash(layer.sharp, -600 + 3000 * sweep, 120 - 20 * i, color, .9)
            slash(layer.glow, -600 + 3000 * sweep, 120 - 20 * i, fx.scale_c(color, .6), 1)
    badge_in = fx.ease_out((local - .25) / .55)
    mark(layer, 960, 330, 250 * (.6 + .4 * fx.back_out(badge_in)), badge_in, spin=(1 - badge_in) * math.pi * 1.5)
    ring = fx.ease_out((local - .35) / .5)
    if 0 < ring < 1:
        fx.ellipse(layer.sharp, (960, 330), (130 + 260 * ring, 130 + 260 * ring), PAPER, .5 * (1 - ring), 3)
    kinetic(layer, 'PITCHPRISM', 960, 560, 168, PAPER, 1, local, .55, anchor='c', track=10, max_width=1700)
    rule = fx.ease_out((local - .95) / .45)
    gradient_bar(layer, 960 - 420 * rule, 652, 960 + 420 * rule, 658, rule)
    sub = fx.ease_out((local - 1.1) / .4)
    text(layer, 'YOUR AI FOOTBALL COMPANION', 960, 690 + 10 * (1 - sub), 34, PAPER, sub, face=LABEL, anchor='c', track=14)
    fixture = fx.ease_out((local - 1.3) / .4)
    if fixture > .003:
        parts = [('MANCHESTER CITY', MINT), ('   V   ', DIM), ('NEWCASTLE UNITED', CORAL)]
        total = sum(fx.text_w(v, LABEL, 30, 6) for v, _ in parts) + 60
        panel(layer, 960 - total / 2, 760, 960 + total / 2, 812, fixture, opacity=.8, hairline=False, name='intro-fixture')
        x = 960 - total / 2 + 30
        for value, color in parts:
            text(layer, value, x, caps_top(760, 52, 30), 30, color, fixture, face=LABEL, track=6)
            x += fx.text_w(value, LABEL, 30, 6)
    tag = fx.ease_out((local - 1.5) / .4)
    text(layer, 'SEE THE PLAY  /  READ THE SPACE  /  FOLLOW THE BALL', 960, 862, 24, DIM, tag, face=LABEL, anchor='c', track=8)
    image = layer.compose(.5)
    if local > 2.1:
        image = stinger(image, still(0), (local - 2.1) / .7)
    return image


def outro(local):
    """Full-time card: spectrum stinger in from the replay, score slab, the three readings, end slate with the mark."""
    base = graded(59.6, 10, .2, .3).astype(np.float32) * .5 + np.array(INK, np.float32) * .5
    layer = fx.Layers(base.clip(0, 255).astype(np.uint8))
    light_streaks(layer, local + 3, .6, seed=11)
    enter = fx.ease_out((local - .22) / .35)
    text(layer, 'FULL TIME  /  EXCERPT', 960, 150 + 10 * (1 - enter), 30, PAPER, enter, face=LABEL, anchor='c', track=14)
    kinetic(layer, 'BEYOND THE SCORE', 960, 236, 110, PAPER, 1, local, .25, anchor='c', track=6, max_width=1660)
    slab = fx.ease_out((local - .5) / .45)
    if slab > .003:
        width = 1120 * slab
        panel(layer, 960 - width / 2, 330, 960 + width / 2, 520, slab, opacity=.9, hairline=False, name='outro-score')
        gradient_bar(layer, 960 - width / 2, 516, 960 + width / 2, 522, slab)
        fx.rect(layer, 960 - width / 2, 330, 960 - width / 2 + 10, 516, MINT, slab)
        fx.rect(layer, 960 + width / 2 - 10, 330, 960 + width / 2, 516, CORAL, slab)
        text(layer, 'MAN CITY', 640, 425, 54, PAPER, slab, face=DISPLAY, anchor='c', track=4)
        text(layer, 'NEWCASTLE', 1280, 425, 54, PAPER, slab, face=DISPLAY, anchor='c', track=4)
        text(layer, '0-0', 960, 425, 150, PAPER, slab, face=DISPLAY_ITALIC, anchor='c', track=8)
    note = fx.ease_out((local - .8) / .35)
    text(layer, 'VISIBLE SCOREBOARD IN THE SUPPLIED EXCERPT', 960, 566, 22, DIM, note, face=LABEL, anchor='c', track=8)
    labels = [('01', 'SPOT THE SCREEN', CYAN), ('02', 'LOOK INSIDE', GREEN), ('03', 'READ THE PRESSURE', MAGENTA)]
    sizes = [fx.text_w(n, DISPLAY, 34, 2) + fx.text_w(l, LABEL, 30, 4) + 70 for n, l, _ in labels]
    xx = 960 - (sum(sizes) + 40) / 2
    for i, ((number, label, color), width) in enumerate(zip(labels, sizes)):
        a = fx.ease_out((local - .85 - i * .1) / .3)
        y = 630 + 16 * (1 - a)
        panel(layer, xx, y, xx + width, y + 60, a, opacity=.88, hairline=False, name=f'outro-{i}')
        fx.rect(layer, xx, y + 56, xx + width * a, y + 60, color, a)
        text(layer, number, xx + 20, caps_top(y, 60, 34), 34, color, a, face=DISPLAY, track=2)
        text(layer, label, xx + 30 + fx.text_w(number, DISPLAY, 34, 2), caps_top(y, 60, 30), 30, PAPER, a, face=LABEL, track=4)
        xx += width + 20
    end = fx.ease_out((local - 1.3) / .45)
    mark(layer, 960, 830, 96 * (.7 + .3 * fx.back_out(end)), end, spin=(1 - end) * math.pi)
    text(layer, 'PITCHPRISM', 960, 912, 44, PAPER, end, face=DISPLAY_ITALIC, anchor='c', track=10)
    text(layer, 'EVERY ANGLE TELLS A STORY', 960, 962, 22, DIM, end, face=LABEL, anchor='c', track=12)
    text(layer, 'REVIEWED OBSERVATIONS  /  EDITORIAL OPTIONS  /  NO OFFICIAL xG', 960, 1022, 18, DIM, end * .8, face=LABEL, anchor='c', track=6)
    image = layer.compose(.5)
    if local < .45:
        # Spectrum stinger out of the last replay frame into the full-time card.
        image = stinger(still(59.6), image, local / .45)
    return (image * (1 - fx.ease_in_out((local - 2.75) / .45))).astype(np.uint8)


def live_caption(layer, local, start, end, title, body, color=CYAN):
    """Broadcast lower third: a slanted spectrum tab, then a title bar and a body line that wipe in."""
    if not start <= local <= end:
        return
    alpha = min(fx.ease_out((local - start) / .35), fx.ease_out((end - local) / .3))
    grow = fx.ease_out((local - start) / .45)
    width = min(1730, max(fx.text_w(title, DISPLAY_ITALIC, 48, 3), min(1580, fx.text_w(body, BODY, 28))) + 96)
    x0, y0 = 75, 846
    panel(layer, x0, y0, x0 + width * (.12 + .88 * grow), 982, alpha, opacity=.9, hairline=False, name='live-caption')
    tab = fx.ease_out((local - start) / .3)
    poly(layer.sharp, [(x0, y0), (x0 + 22, y0), (x0 + 10, 982), (x0 - 12, 982)], color, alpha * tab)
    gradient_bar(layer, x0, 978, x0 + width * grow, 982, alpha)
    text(layer, title, x0 + 40, caps_top(y0 + 12, 50, 48), 48, PAPER, alpha, face=DISPLAY_ITALIC, track=3, max_width=width - 70,
         reveal=fx.ease_out((local - start - .08) / .45))
    body_alpha = alpha * fx.ease_out((local - start - .22) / .3)
    paragraph(layer, body, x0 + 41, 922 + 6 * (1 - body_alpha / max(alpha, 1e-6)), width=width - 70, size=28, color=DIM,
              alpha=body_alpha, line_height=36, max_height=48)


def corner_brackets(layer, alpha, grow):
    inset, arm = 22, 34 + 22 * grow
    for (x, sx), color in zip(((inset, 1), (W - inset, -1)), (CYAN, MAGENTA)):
        for y, sy in ((inset, 1), (H - inset, -1)):
            fx.line(layer.sharp, (x, y), (x + sx * arm, y), color, alpha, 4)
            fx.line(layer.sharp, (x, y), (x, y + sy * arm), color, alpha, 4)


def rewind_look(base, local):
    smear = cv2.blur(base, (61, 1)).astype(np.float32) * .65 + base.astype(np.float32) * .35
    grey = smear.mean(axis=2, keepdims=True)
    out = (grey + (smear - grey) * .35) * .72
    out[::4] *= .8
    out[:, :, 0] = np.roll(out[:, :, 0], -6, axis=1)
    out[:, :, 2] = np.roll(out[:, :, 2], 6, axis=1)
    return np.clip(out, 0, 255).astype(np.uint8)


def badge(layer, label, value, alpha):
    w = fx.text_w(label, DISPLAY_ITALIC, 34, 3) + fx.text_w(value, DISPLAY, 34, 2) + 70
    # Sits above the caption, clear of the broadcaster's score bug and sponsor marks.
    panel(layer, 75, 778, 75 + w, 830, alpha, opacity=.9, hairline=False, name='badge')
    poly(layer.sharp, [(75, 778), (95, 778), (85, 830), (65, 830)], MAGENTA, alpha)
    text(layer, label, 109, caps_top(778, 52, 34), 34, PAPER, alpha, face=DISPLAY_ITALIC, track=3)
    text(layer, value, 75 + w - 22, caps_top(778, 52, 34), 34, CYAN, alpha, face=DISPLAY, anchor='rt', track=2)


def locate(output):
    segment = next((s for s in TIMELINE if s['outputStart'] <= output < s['outputEnd']), TIMELINE[-1])
    ratio = fx.clamp((output - segment['outputStart']) / (segment['outputEnd'] - segment['outputStart']))
    return segment, segment['sourceStart'] + ratio * (segment['sourceEnd'] - segment['sourceStart'])


def render_frame(output):
    segment, second = locate(output)
    local, kind = output - segment['outputStart'], segment['kind']
    if kind == 'intro':
        return intro(local)
    if kind == 'outro':
        return outro(local)
    if kind == 'freeze':
        return freeze(next(s for s in CLIP['scenes'] if s['id'] == segment['scene']), local, output)
    base = frame_at(second)
    if kind == 'rewind':
        base = rewind_look(base, local)
    layer = fx.Layers(base)
    if kind == 'rewind':
        pulse = .75 + .25 * math.sin(local * 30)
        for offset in (-46, 30):
            poly(layer.sharp, [(960 + offset, 470), (1012 + offset, 432), (1012 + offset, 508)], MINT, pulse)
        text(layer, 'LOOK AGAIN', 960, 568, 48, PAPER, 1, face=fx.DIN, anchor='c', track=4)
    if kind == 'replay':
        envelope = min(fx.ease_out(local / .3), fx.ease_out((5.6 - local) / .3))
        corner_brackets(layer, .85 * envelope, fx.ease_out(local / .4))
        badge(layer, 'REPLAY', '0.5x', envelope)
        live_caption(layer, local, 0, 5.6, 'THE RIGHT-SIDE OPTION', 'Return to the original action. Watch how play continues.')
    if kind == 'live':
        cues = [(0, 5, 'PATIENCE BEFORE PROGRESSION', 'Watch City circulate, then carry towards halfway.'),
                (10, 16, 'USE THE FAR SIDE', 'The broadcast follows play towards the far touchline.'),
                (27.2, 33, 'COMBINE ON THE FLANK', 'Follow the short exchanges before the ball comes infield.'),
                (39, 44, 'DEFENDERS BETWEEN BALL AND GOAL', 'Compare the carrier and the defenders ahead.'),
                (49.5, 55, 'NEWCASTLE DEFEND IN NUMBERS', 'Count the dark shirts around the box as City probe the edge.'),
                (57, 62, 'FOLLOW THE NEXT ACTION', 'Play moves right; watch the contest continue.'),
                (62.4, 66.4, 'CONTEST BY THE CORNER', 'A City attacker and a Newcastle defender battle near the byline.')]
        for a, b, title, sub in cues:
            live_caption(layer, second, a, b, title, sub)
    # Raster widths include ~8px of padding, so the wordmark is set against the measured descriptor edge.
    descriptor = '/ SOURCE-GROUNDED VIEW'
    text(layer, descriptor, 1842, caps_top(1026, 22, 20), 20, DIM, .9, face=fx.DIN, anchor='rt', track=1)
    edge = 1842 - fx.text_w(descriptor, fx.DIN, 20, 1)
    text(layer, 'PITCHPRISM', edge - 2, caps_top(1026, 22, 20), 20, MINT, .9, face=fx.DIN, anchor='rt', track=2)
    return layer.compose(.4)


def audit_labels(index):
    labels, panels = LABEL_AUDIT, PANEL_AUDIT
    for i, a in enumerate(labels):
        x, y, w, h = a['box']
        if x < 0 or y < 0 or x + w > W or y + h > H:
            raise ValueError(f"Label outside frame {index}: {a}")
        for b in labels[i + 1:]:
            if overlaps(a['box'], b['box'], 0):
                raise ValueError(f"Overlapping role labels on frame {index}: {a['text']} / {b['text']}")
        for p in panels:
            if overlaps(a['box'], p['box'], 0):
                raise ValueError(f"Role label {a['text']} covered by {p['name']} on frame {index}")
    return len(labels) * (len(labels) - 1) // 2 + len(labels) * len(panels)


def encode_chunk(job):
    global TEXT_AUDIT, LABEL_AUDIT, PANEL_AUDIT
    start, end, destination, encoder = job
    process = subprocess.Popen([encoder, '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'bgr24',
        '-video_size', '1920x1080', '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
        '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-threads', '2', destination], stdin=subprocess.PIPE)
    try:
        checks = label_checks = 0
        fonts = set()
        for index in range(start, end):
            TEXT_AUDIT, LABEL_AUDIT, PANEL_AUDIT = [], [], []
            frame = render_frame(index / FPS)
            label_checks += audit_labels(index)
            for box in TEXT_AUDIT:
                if box['x'] < 0 or box['y'] < 0 or box['x']+box['width'] > W or box['y']+box['height'] > H:
                    raise ValueError(f"Text outside frame {index}: {box}")
                fonts.add(box['font'])
                checks += 1
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait():
        raise RuntimeError('Tactical video encoding failed')
    return {'path': destination, 'textBoxesChecked': checks, 'labelPairsChecked': label_checks, 'fonts': sorted(fonts)}


def make_audio(source, destination, encoder):
    filters, labels = [], []
    for i, segment in enumerate(TIMELINE):
        duration = round(segment['outputEnd'] - segment['outputStart'], 3)
        label = f'a{i}'
        labels.append(f'[{label}]')
        if segment['kind'] in ('live', 'replay'):
            rate = (segment['sourceEnd'] - segment['sourceStart']) / duration
            filters.append(f"[0:a]atrim=start={segment['sourceStart']}:end={segment['sourceEnd']},asetpts=PTS-STARTPTS,atempo={rate},apad,atrim=duration={duration},afade=t=in:d=0.025,afade=t=out:st={max(0, duration-.025)}:d=0.025[{label}]")
        else:
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={duration}[{label}]')
    filters.append(''.join(labels) + f'concat=n={len(labels)}:v=0:a=1[out]')
    subprocess.run([encoder, '-v', 'error', '-y', '-i', str(source), '-filter_complex', ';'.join(filters),
                    '-map', '[out]', '-c:a', 'aac', '-b:a', '160k', str(destination)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=HERE / 'build/source.mp4')
    parser.add_argument('--out', type=Path, default=HERE / 'build/rendered/PitchPrism-Enhanced.mp4')
    parser.add_argument('--buddy', type=Path, default=HERE / 'build/rendered/pitchprism-mark.png',
                        help='PNG of watch/mark.svg; see export_football_buddy.cjs --mark')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    provenance = validate_source(args.source)
    validate_story()
    encoder = shutil.which('ffmpeg')
    if not encoder:
        import imageio_ffmpeg
        encoder = imageio_ffmpeg.get_ffmpeg_exe()
    if not args.buddy.is_file():
        raise ValueError('Export the brand mark PNG first: node product/football/scripts/export_football_buddy.cjs --mark <png>')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.source.resolve() == args.out.resolve():
        raise ValueError('Do not overwrite source media')
    setup(args.source, args.buddy)
    previews = args.out.parent / 'previews'
    previews.mkdir(exist_ok=True)
    times = [1.4, 116.0]
    for segment in TIMELINE:
        if segment['kind'] == 'freeze':
            times += [segment['outputStart'] + delta for delta in (1.4, 5.4, 9.6, 12.4)]
    for second in times:
        cv2.imwrite(str(previews / f'{second:06.2f}.jpg'), render_frame(second), [cv2.IMWRITE_JPEG_QUALITY, 93])
    print(f'Previews ready; {TIMELINE[-1]["outputEnd"]:.2f}s / 1920x1080 / 25fps', flush=True)
    if args.preview_only:
        return
    parts = args.out.parent / 'chunks'
    parts.mkdir(exist_ok=True)
    total = round(TIMELINE[-1]['outputEnd'] * FPS)
    jobs = [(i, min(i + 100, total), str(parts / f'{i:05}.mp4'), encoder) for i in range(0, total, 100)]
    text_checks, label_checks, fonts = 0, 0, set()
    with ProcessPoolExecutor(max_workers=max(1, min(4, args.workers)), mp_context=multiprocessing.get_context('spawn'),
                             initializer=setup, initargs=(str(args.source), str(args.buddy))) as pool:
        for n, result in enumerate(pool.map(encode_chunk, jobs)):
            text_checks += result['textBoxesChecked']
            label_checks += result['labelPairsChecked']
            fonts.update(result['fonts'])
            print(f'Encoded {n + 1}/{len(jobs)} chunks', flush=True)
    playlist = parts / 'concat.txt'
    playlist.write_text(''.join(f"file '{Path(job[2]).name}'\n" for job in jobs))
    audio = parts / 'audio.m4a'
    make_audio(args.source, audio, encoder)
    staging = args.out.with_name(args.out.stem + '.pending.mp4')
    subprocess.run([encoder, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(playlist), '-i', str(audio),
        '-map', '0:v:0', '-map', '1:a:0', '-t', str(TIMELINE[-1]['outputEnd']), '-c', 'copy', '-movflags', '+faststart', str(staging)], check=True)
    subprocess.run([encoder, '-v', 'error', '-xerror', '-i', str(staging), '-f', 'null', '-'], check=True)
    cap = cv2.VideoCapture(str(staging))
    metadata = {'frames': round(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 'fps': cap.get(cv2.CAP_PROP_FPS),
                'width': round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 'height': round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    cap.release()
    if metadata != {'frames': total, 'fps': 25.0, 'width': 1920, 'height': 1080}:
        raise ValueError(f'Unexpected encoded video: {metadata}')
    staging.replace(args.out)
    manifest = {'source': CLIP['source'], **provenance, 'output': str(args.out.name), 'outputSha256': digest(args.out),
        'durationSeconds': TIMELINE[-1]['outputEnd'], **metadata, 'fullVideoAudioDecode': True, 'timeline': TIMELINE,
        'clipDataSha256': digest(HERE / 'data/clip.json'), 'storySha256': digest(HERE / 'data/tactical-story.json'),
        'rendererSha256': digest(__file__), 'pitchViewSha256': digest(HERE / 'scripts/pitch3d.py'), 'markSha256': digest(MARK), 'geometrySha256': digest(HERE / 'data/tactical-geometry.json'), 'buddySha256': digest(args.buddy), 'language': 'English burned-in text',
        'audio': 'Original broadcast audio on live sections; half-speed replay; silent editorial freezes and bookends.',
        'modelUsedForRender': False, 'notTracking': True, 'completeSourceRetained': True,
        'textAudit': {'checkedOnEveryFrame': True, 'textBoxesChecked': text_checks, 'outOfFrameBoxes': 0,
                      'fonts': sorted(fonts), 'paragraphBoxes': 'Measured raster wrapping and height limits enforced'},
        'labelAudit': {'checkedOnEveryFrame': True, 'pairsChecked': label_checks, 'labelOverlaps': 0, 'labelsCoveredByPanels': 0},
        'note': 'Options and board positions are editorial schematics, not official events, calibrated positions or completed passes.'}
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'VERIFIED MP4: {args.out} ({total} frames, {manifest["durationSeconds"]}s)', flush=True)


if __name__ == '__main__':
    main()
