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
from gamebuddy_fx import fx, tactics

W, H, FPS = 1920, 1080, 25
CLIP = json.loads((HERE / 'data/clip.json').read_text())
STORY = json.loads((HERE / 'data/tactical-story.json').read_text())
MINT, CORAL, GOLD = map(fx.hexc, ('a1f5d8', 'f29075', 'ffcd86'))
INK, PAPER, DIM = map(fx.hexc, ('0c1820', 'edf8f3', 'a6bec5'))
BODY = str(HERE / 'watch/fonts/dm-sans.ttf')
_SOURCE = None
_CAPTURE = None
_LAST = -1
_BUDDY = None
TEXT_AUDIT = None
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
    if not Path(fx.DIN).is_file():
        fx.DIN = fx.DINA = BODY
    if not Path(fx.CJK).is_file():
        fx.CJK = BODY
    _BUDDY = np.asarray(Image.open(buddy).convert('RGBA').resize((192, 204), Image.Resampling.LANCZOS))
    # Only this football process replaces the bookend asset; upstream stays unchanged.
    fx.gamebuddy_mascot_rgba = lambda closing=False: _BUDDY


@lru_cache(maxsize=6)
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


def text(layer, value, x, y, size=28, color=PAPER, alpha=1, face=BODY, anchor='lt', track=0, max_width=None):
    if any(ord(char) not in supported_characters(face) for char in value):
        raise ValueError('Missing font glyph in: ' + value)
    raster = fx.text_rgba(value, face, size, color, track)
    while max_width and raster.shape[1] > max_width and size > 14:
        size -= 1
        raster = fx.text_rgba(value, face, size, color, track)
    if max_width and raster.shape[1] > max_width:
        raise ValueError('Text cannot fit its declared box: ' + value)
    if TEXT_AUDIT is not None and alpha > .05:
        height, width = raster.shape[:2]
        xx, yy = x, y
        if anchor == 'c': xx, yy = x-width/2, y-height/2
        elif anchor == 'rt': xx = x-width
        elif anchor == 'rc': xx, yy = x-width, y-height/2
        elif anchor == 'lc': yy = y-height/2
        TEXT_AUDIT.append(dict(text=value, x=xx, y=yy, width=width, height=height, font=face, size=size))
    layer.paste(raster, x, y, alpha=alpha, anchor=anchor)


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


def board(point):
    # Crop the editorial schematic to its attacking portion; not a camera calibration.
    return np.array([930 + point[1] * 8.4, 220 + (100 - point[0]) * 12.97])


def draw_pitch(layer, alpha):
    if alpha < .003:
        return
    x0, y0, width, height = 930, 220, 840, 778.2
    cv2.rectangle(layer.sharp, (x0 - 15, y0 - 16), (x0 + width + 15, round(y0 + height + 6)), (*fx.hexc('102e30'), round(246 * alpha)), -1)
    for i in range(12):
        top, bottom = round(y0 + i * height / 12), round(y0 + (i + 1) * height / 12)
        color = fx.hexc('18433b' if i % 2 == 0 else '123b35')
        cv2.rectangle(layer.sharp, (x0, top), (x0 + width, bottom), (*color, round(245 * alpha)), -1)
    # IFAB Law 1 geometry on a nominal 105x68m drawing, never measured match coordinates.
    length, pitch_width, goal_width = 105.0, 68.0, 7.32
    pct_x = lambda metres: metres / length * 100
    pct_y = lambda metres: metres / pitch_width * 100
    penalty_x, goal_area_x, spot_x = 100 - pct_x(16.5), 100 - pct_x(5.5), 100 - pct_x(11)
    penalty_y = pct_y((pitch_width - goal_width) / 2 - 16.5)
    goal_area_y = pct_y((pitch_width - goal_width) / 2 - 5.5)
    goal_y = pct_y((pitch_width - goal_width) / 2)
    paths = [[(40, 0), (100, 0), (100, 100), (40, 100)],
             [(50, 0), (50, 100)], [(100, penalty_y), (penalty_x, penalty_y), (penalty_x, 100-penalty_y), (100, 100-penalty_y)],
             [(100, goal_area_y), (goal_area_x, goal_area_y), (goal_area_x, 100-goal_area_y), (100, 100-goal_area_y)],
             [(100, goal_y), (101.1, goal_y), (101.1, 100-goal_y), (100, 100-goal_y)]]
    angles = np.linspace(0, 2 * math.pi, 90)
    paths.append([(50 + pct_x(9.15) * math.cos(a), 50 + pct_y(9.15) * math.sin(a)) for a in angles])
    theta = math.acos((11 - 16.5) / 9.15)
    paths.append([(spot_x + pct_x(9.15) * math.cos(a), 50 + pct_y(9.15) * math.sin(a))
                  for a in np.linspace(theta, 2*math.pi-theta, 60)])
    for side in (0,100):
        paths.append([(100-pct_x(math.cos(a)), side+(1 if side==0 else -1)*pct_y(math.sin(a)))
                      for a in np.linspace(0,math.pi/2,24)])
    for points in paths:
        tactics.draw_path(layer, [board(p) for p in points], fx.hexc('b8dcd1'), alpha=alpha * .52, width=2, arrow=False)
    for point in ([spot_x, 50],[50,50]):
        fx.ellipse(layer.sharp, board(point), (3, 3), PAPER, .7 * alpha, -1)


def route(layer, start, end, alpha, t, reveal=1, dashed=True, arrow=True, color=MINT, width=5):
    start, end = np.array(start), np.array(end)
    delta = end - start
    length = np.linalg.norm(delta)
    if length < 85 or alpha <= .003:
        return
    direction = delta / length
    normal = np.array([-direction[1], direction[0]])
    start, end = start + direction * 42, end - direction * 42
    control = (start + end) / 2 + normal * min(35, length * .13)
    us = np.linspace(0, fx.clamp(reveal), 70)
    points = np.array([(1 - u) ** 2 * start + 2 * (1 - u) * u * control + u ** 2 * end for u in us])
    if dashed:
        travelled = 0.0
        for a, b in zip(points[:-1], points[1:]):
            distance = np.linalg.norm(b - a)
            if (travelled + t * 38) % 42 < 24:
                fx.line(layer.sharp, a, b, color, alpha, width)
                fx.line(layer.glow, a, b, fx.scale_c(color, alpha * .4), 1, width + 3)
            travelled += distance
    else:
        tactics.draw_path(layer, points, color, alpha=alpha, width=width, arrow=False)
    if arrow and len(points) > 1:
        a, tip = points[-3], points[-1]
        d = (tip - a) / max(.1, np.linalg.norm(tip - a))
        side = np.array([-d[1], d[0]])
        for sign in (-1, 1):
            fx.line(layer.sharp, tip - d * 26 + side * 14 * sign, tip, color, alpha, width)


def annotations(layer, scene, reading, morph, local, output, alpha):
    positions = {p['id']: np.array(p['foot']) * 1.5 * (1 - morph) + board(p['board']) * morph for p in scene['players']}
    focus = set(reading['focus'])
    carrier = positions['carrier']
    fx.ellipse(layer.glow, carrier, (110 - 32 * morph, 34 + 38 * morph), fx.scale_c(GOLD, alpha * .25), 1, 18)
    for i, item in enumerate(scene['routes']):
        # A spatial relation is not a pass or a defensive line: do not draw it as one.
        if item['kind'] != 'option':
            continue
        selected = i in reading['routes']
        is_option = item['kind'] == 'option'
        route(layer, positions[item['a']], positions[item['b']], alpha * (.95 if selected else .08), output,
              reveal=fx.ease_out((local % CLIP['production']['readingStepSeconds']) / .8) if selected else 1,
              dashed=is_option, arrow=is_option, color=MINT if is_option else DIM, width=6 if selected else 3)
    labels, label_jobs = [], []
    marker_boxes = [(p[0] - 34, p[1] - 26, 68, 52) for p in positions.values()]
    for player in scene['players']:
        active = player['id'] in focus
        color = MINT if player['team'] == 'MCI' else CORAL
        a = alpha * (1 if active else .30)
        point = positions[player['id']]
        tactics.draw_marker(layer, point, color, '', output, alpha=a, active=active, perspective=1 - morph)
        if active:
            x, y = point
            label = ROLE_LABELS.get(player['id'], 'DEF')
            raster = fx.text_rgba(label, fx.DIN, 28, PAPER, 1)
            w, h = raster.shape[1] + 24, 39
            options = [(x - w / 2, y - 88), (x + 42, y - 35), (x - w - 42, y - 35), (x - w / 2, y + 45)]
            def cost(origin):
                xx, yy = origin
                collisions = sum(xx < b[0] + b[2] and xx + w > b[0] and yy < b[1] + b[3] and yy + h > b[1] for b in labels)
                marker_collisions = sum(xx < b[0] + b[2] and xx + w > b[0] and yy < b[1] + b[3] and yy + h > b[1] for b in marker_boxes)
                return collisions * 100 + marker_collisions * 30 + (100 if yy < 195 or yy+h > 1010 else 0) + (100 if morph > .5 and (xx < 900 or xx + w > 1830) else 0)
            xx, yy = min(options, key=cost)
            labels.append((xx, yy, w, h))
            label_alpha = a * fx.clamp((abs(morph-.5)-.2)/.3)
            label_jobs.append((xx, yy, w, h, label, label_alpha))
    return label_jobs


def header(layer, scene, plan, alpha, local):
    slide = 20 * (1 - fx.ease_out(local / .4))
    fx.rect(layer, 56, 40, 1864, 180, INK, .94 * alpha)
    fx.rect(layer, 75, 62, 81, 165, MINT, alpha)
    text(layer, 'PITCHPRISM / TACTICAL STUDIO', 102, 54 + slide, 24, MINT, alpha, face=fx.DIN, track=3)
    text(layer, plan['title'], 100, 91 + slide, 76, PAPER, alpha, face=fx.DIN, track=2)
    text(layer, 'REVIEWED FRAME / ' + scene['clock'], 1825, 58, 26, MINT, alpha, face=fx.DIN, anchor='rt', track=1)
    text(layer, f"SOURCE {scene['second']:.2f}s   |   MCI 0 - 0 NEW", 1825, 106, 24, DIM, alpha, face=fx.DIN, anchor='rt', track=1)
    text(layer, 'EXCERPT ONLY / NO OFFICIAL EVENT FEED', 1825, 147, 18, DIM, alpha, face=fx.DIN, anchor='rt', track=1)


def freeze(scene, local, output):
    plan = STORY['scenes'][scene['id']]
    step = min(2, int(local / CLIP['production']['readingStepSeconds']))
    reading = plan['steps'][step]
    alpha = min(fx.ease_out(local / .35), fx.ease_out((13.2 - local) / .35))
    morph = fx.ease_in_out((local - 2.8) / 1.0) * (1 - fx.ease_in_out((local - 11.6) / 1.0))
    base = (still(scene['second']).astype(np.float32) * (1 - .13 * alpha - .72 * morph)).astype(np.uint8)
    layer = fx.Layers(base)
    draw_pitch(layer, morph * alpha)
    # Compose the field before highlights, so translucent field fills never cover the marks.
    layer = fx.Layers(layer.compose(.3))
    label_jobs = annotations(layer, scene, reading, morph, local, output, alpha)
    # Burn lines/glow first; typography must sit above every arrow and marker.
    layer = fx.Layers(layer.compose(.55))
    for xx, yy, width, height, label, label_alpha in label_jobs:
        fx.rect(layer, xx, yy, xx + width, yy + height, INK, .94 * label_alpha)
        text(layer, label, xx + 12, yy + 3, 28, PAPER, label_alpha, face=fx.DIN, track=1)
    header(layer, scene, plan, alpha, local)
    if morph > .003:
        a = morph * alpha
        text(layer, 'READ THE GAME', 80, 242, 54, MINT, a, face=fx.DIN, track=2)
        text(layer, plan['subtitle'], 81, 307, 25, DIM, a)
        for i, item in enumerate(plan['steps']):
            yy = 377 + i * 177
            active = i == step
            row_alpha = a * (1 if active else .76)
            fx.rect(layer, 76, yy - 12, 854, yy + 157, INK, .94 * a)
            if active:
                fx.rect(layer, 76, yy - 12, 81, yy + 157, MINT, a)
            text(layer, f'{i + 1:02}', 102, yy, 51, MINT if active else DIM, row_alpha, face=fx.DIN)
            text(layer, item['title'], 174, yy + 1, 37, PAPER, row_alpha, face=fx.DIN, track=1)
            paragraph(layer, item['text'], 175, yy + 50, width=640, size=25, alpha=row_alpha, line_height=34, max_height=107)
        text(layer, 'TACTICAL VIEW / SCHEMATIC', 930, 185, 22, MINT, a, face=fx.DIN, track=1)
        text(layer, 'ATTACK TO GOAL', 1770, 185, 20, DIM, a, face=fx.DIN, anchor='rt', track=1)
        layer.paste(_BUDDY, 78, 913 + 5 * math.sin(output * 3), alpha=a, scale=.48)
        text(layer, 'PRISM / YOUR FOOTBALL COMPANION', 190, 950, 20, DIM, a, face=fx.DIN, track=1)
    camera_alpha = alpha * (1 - morph)
    if camera_alpha > .003:
        fx.rect(layer, 72, 808, 1200, 992, INK, .92 * camera_alpha)
        fx.rect(layer, 72, 808, 79, 992, GOLD, camera_alpha)
        text(layer, f'{step + 1:02} / {reading["title"]}', 103, 824, 42, PAPER, camera_alpha, face=fx.DIN, track=1)
        paragraph(layer, reading['text'], 104, 884, width=1040, size=29, color=PAPER, alpha=camera_alpha, line_height=42)
    fx.rect(layer, 74, 1032, 1846, 1036, DIM, .2 * alpha)
    fx.rect(layer, 74, 1032, 74 + 1772 * fx.clamp(local / 13.2), 1036, MINT, alpha)
    text(layer, 'MINT = CITY  /  CORAL = NEWCASTLE  /  DASHED ARROWS = OPTIONS, NOT RECORDED PASSES  /  SCHEMATIC, NOT TRACKING', 76, 1045, 18, DIM, alpha, face=fx.DIN, track=1)
    return layer.compose(.55)


def intro(local):
    reveal=fx.ease_in_out((local-2.05)/.65)
    fade=1-reveal
    base=still(8)
    blur=cv2.GaussianBlur(base,(0,0),6*(1-reveal)+.01)
    layer=fx.Layers(fx.grade(blur,sat=.7,gain=.32+.68*reveal,vig=.5))
    brand=fx.ease_out((local-.16)/.4)*fade
    layer.paste(_BUDDY,130,65,alpha=brand,scale=.94)
    text(layer,'PITCHPRISM',335,90,82,PAPER,brand,face=fx.DINA,track=2,max_width=1350)
    text(layer,'YOUR AI FOOTBALL COMPANION',339,185,27,DIM,brand,face=fx.DIN,track=3,max_width=1350)
    headline=fx.ease_out((local-.28)/.35)*fade
    text(layer,'SEE THE PLAY',130,304+18*(1-headline),205,PAPER,headline,face=fx.DIN,track=5,max_width=1660)
    context=fx.ease_out((local-.65)/.4)*fade
    text(layer,'FROM BUILD-UP TO THE BOX',134,568,80,MINT,context,face=fx.DIN,track=4,max_width=1650)
    text(layer,'Manchester City x Newcastle / a source-grounded story',137,677,32,PAPER,context,max_width=1620)
    tag=fx.ease_out((local-1.18)/.35)*fade
    value='READ THE SPACE. FOLLOW THE BALL.'
    raster=fx.text_rgba(value,fx.DIN,49,INK,2)
    # Size the banner from the complete glyph image; no inherited NBA unit/tag slot.
    fx.rect(layer,130,794,130+raster.shape[1]+48,874,MINT,.94*tag)
    text(layer,value,154,808,49,INK,tag,face=fx.DIN,track=2,max_width=1570)
    if local>2.05:
        p=fx.ease_in_out((local-2.05)/.65)
        xx=-350+2600*p
        cv2.fillPoly(layer.sharp,[np.array([[xx,0],[xx+75,0],[xx-235,H],[xx-310,H]],np.int32)],(*MINT,170),cv2.LINE_AA)
    return layer.compose(.25)


def outro(local):
    base=cv2.GaussianBlur(still(66.56),(0,0),8)
    layer=fx.Layers(fx.grade(base,sat=.45,gain=.24,vig=.6))
    enter=fx.ease_out(local/.4)
    text(layer,'BEYOND THE SCORE',960,250,119,PAPER,enter,face=fx.DIN,anchor='c',track=6,max_width=1660)
    text(layer,'MANCHESTER CITY x NEWCASTLE / SUPPLIED EXCERPT',960,349,28,DIM,enter,anchor='c',max_width=1630)
    score=fx.ease_out((local-.35)/.4)
    text(layer,'MCI',625,528,59,MINT,score,face=fx.DIN,anchor='c',track=2)
    text(layer,'0 - 0',960,528,235,PAPER,score,face=fx.DIN,anchor='c',track=9,max_width=590)
    text(layer,'NEW',1295,528,59,CORAL,score,face=fx.DIN,anchor='c',track=2)
    text(layer,'VISIBLE SCOREBOARD / EXCERPT ONLY',960,688,27,DIM,score,anchor='c',max_width=1500)
    labels=[('BUILD',MINT),('COMBINE',GOLD),('LOOK RIGHT',CORAL)]
    sizes=[fx.text_rgba(label,fx.DIN,38,color,2).shape[1]+44 for label,color in labels]
    xx=960-(sum(sizes)+40)/2
    for i,((label,color),width) in enumerate(zip(labels,sizes)):
        a=fx.ease_out((local-.9-i*.12)/.25)
        fx.rect(layer,xx,777,xx+width,841,INK,.9*a)
        fx.rect(layer,xx,838,xx+width,841,color,a)
        text(layer,label,xx+22,786,38,color,a,face=fx.DIN,track=2,max_width=width-38)
        xx+=width+20
    layer.paste(_BUDDY,1680,800,alpha=enter,scale=.75)
    end=fx.ease_out((local-1.45)/.4)
    text(layer,'REVIEWED OBSERVATIONS / EDITORIAL OPTIONS / NO OFFICIAL xG',960,947,23,DIM,end,anchor='c',max_width=1480)
    text(layer,'PitchPrism / EVERY ANGLE TELLS A STORY',960,1007,24,PAPER,end,anchor='c',max_width=1570)
    image=layer.compose(.2)
    return (image*(1-fx.ease_in_out((local-2.65)/.55))).astype(np.uint8)


def live_caption(layer,local,start,end,title,body,color=MINT):
    if not start<=local<=end:
        return
    alpha=min(fx.ease_out((local-start)/.35),fx.ease_out((end-local)/.25))
    width=max(fx.text_rgba(title,fx.DIN,48,color,2).shape[1],min(1580,fx.text_rgba(body,BODY,27,PAPER).shape[1]))+64
    width=min(1730,width)
    fx.rect(layer,75,820,75+width,990,INK,.90*alpha)
    fx.rect(layer,75,820,81,990,color,alpha)
    text(layer,title,103,833,48,color,alpha,face=fx.DIN,track=2,max_width=width-64)
    paragraph(layer,body,104,906,width=width-64,size=27,color=PAPER,alpha=alpha,line_height=35,max_height=80)


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
        base[:, :, 0] = np.roll(base[:, :, 0], -7, axis=1)
        base[:, :, 2] = np.roll(base[:, :, 2], 7, axis=1)
        base[::3] = (base[::3] * .7).astype(np.uint8)
    layer = fx.Layers(base)
    if kind in ('replay', 'rewind'):
        fx.rect(layer, 80, 165, 430, 230, INK, .9)
        text(layer, 'REPLAY / 0.5x' if kind == 'replay' else 'LOOK AGAIN', 103, 177, 34, MINT, face=fx.DIN, track=2)
    if kind == 'replay':
        live_caption(layer, local, 0, 5.6, 'THE RIGHT-SIDE OPTION', 'Return to the original action. Watch how play continues.')
    if kind == 'live':
        cues = [(0, 5, 'PATIENCE BEFORE PROGRESSION', 'Watch City circulate, then carry towards halfway.'),
                (10, 16, 'USE THE FAR SIDE', 'The broadcast follows play towards the far touchline.'),
                (27.2, 33, 'COMBINE ON THE FLANK', 'Follow the short exchanges before the ball comes infield.'),
                (39, 44, 'DEFENDERS BETWEEN BALL AND GOAL', 'Compare the carrier and the defenders ahead.'),
                (57, 62, 'FOLLOW THE NEXT ACTION', 'Play moves right; watch the contest continue.')]
        for a, b, title, sub in cues:
            live_caption(layer, second, a, b, title, sub)
    text(layer, 'PITCHPRISM / SOURCE-GROUNDED VIEW', 1850, 1035, 20, DIM, face=fx.DIN, anchor='rt', track=1)
    return layer.compose(.4)


def encode_chunk(job):
    global TEXT_AUDIT
    start, end, destination, encoder = job
    process = subprocess.Popen([encoder, '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'bgr24',
        '-video_size', '1920x1080', '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
        '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-threads', '2', destination], stdin=subprocess.PIPE)
    try:
        checks = 0
        fonts = set()
        for index in range(start, end):
            TEXT_AUDIT = []
            frame = render_frame(index / FPS)
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
    return {'path': destination, 'textBoxesChecked': checks, 'fonts': sorted(fonts)}


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
    parser.add_argument('--buddy', type=Path, default=HERE / 'build/rendered/football-buddy.png')
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
        raise ValueError('Export the football SVG companion PNG first; see export_football_buddy.cjs')
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
    text_checks, fonts = 0, set()
    with ProcessPoolExecutor(max_workers=max(1, min(4, args.workers)), mp_context=multiprocessing.get_context('spawn'),
                             initializer=setup, initargs=(str(args.source), str(args.buddy))) as pool:
        for n, result in enumerate(pool.map(encode_chunk, jobs)):
            text_checks += result['textBoxesChecked']
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
        'rendererSha256': digest(__file__), 'buddySha256': digest(args.buddy), 'language': 'English burned-in text',
        'audio': 'Original broadcast audio on live sections; half-speed replay; silent editorial freezes and bookends.',
        'modelUsedForRender': False, 'notTracking': True, 'completeSourceRetained': True,
        'textAudit': {'checkedOnEveryFrame': True, 'textBoxesChecked': text_checks, 'outOfFrameBoxes': 0,
                      'fonts': sorted(fonts), 'paragraphBoxes': 'Measured raster wrapping and height limits enforced'},
        'note': 'Options and board positions are editorial schematics, not official events, calibrated positions or completed passes.'}
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'VERIFIED MP4: {args.out} ({total} frames, {manifest["durationSeconds"]}s)', flush=True)


if __name__ == '__main__':
    main()
