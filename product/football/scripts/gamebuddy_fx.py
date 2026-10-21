"""Use GameBuddy's original broadcast FX on hash-bound real football frames.

Foot anchors exist only at reviewed freeze frames. No live optical tracking is claimed.
"""
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'product/broadcast-fx'))
from broadcast_fx import legacy as fx
from broadcast_fx import tactics
HERE=ROOT/'product/football'
MATCH=json.loads((HERE/'data/clip.json').read_text())
FPS=25;W,H=1920,1080
fx.PRESENTATION_ENGLISH=True;fx.SHOW_PRODUCTION_NOTES=False
for key in ('DIN','DINA','CJK'):
    if not Path(getattr(fx,key)).is_file():setattr(fx,key,'/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf')
fx.font.cache_clear();cv2.setNumThreads(1)
_CAPTURE=None
_LAST=-1
_SOURCE=None


def configure(source):
    global _CAPTURE,_LAST,_SOURCE
    source=Path(source)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=MATCH['source']['sha256']:
        raise ValueError('Source hash differs from reviewed match. Analyse and annotate the new source first.')
    _SOURCE=source;_CAPTURE=cv2.VideoCapture(str(source));_LAST=-1
    if not _CAPTURE.isOpened():raise ValueError('Cannot open source video')


@lru_cache(maxsize=6)
def still(second):
    capture=cv2.VideoCapture(str(_SOURCE));capture.set(cv2.CAP_PROP_POS_FRAMES,round(second*FPS));ok,frame=capture.read();capture.release()
    if not ok:raise ValueError('Missing reviewed frame')
    return cv2.resize(frame,(W,H))


def frame_at(second):
    global _LAST
    index=min(1664,max(0,int(round(second*FPS))))
    if _LAST+1!=index:_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES,index)
    ok,frame=_CAPTURE.read();_LAST=index
    if not ok:raise ValueError(f'Cannot decode source frame {index}')
    return cv2.resize(frame,(W,H))


def locate(output):
    segments=MATCH['production']['timeline']
    segment=next((s for s in segments if s['outputStart']<=output<s['outputEnd']),segments[-1])
    ratio=fx.clamp((output-segment['outputStart'])/(segment['outputEnd']-segment['outputStart']))
    return segment,segment['sourceStart']+ratio*(segment['sourceEnd']-segment['sourceStart'])


def board(point):
    return np.array([650+point[0]*11.3,225+point[1]*5.55])


def pitch(layer,alpha):
    # A graphic field, not a homographic measurement of the broadcast camera.
    corners=np.array([board(p) for p in [(0,0),(100,0),(100,100),(0,100)]],np.int32)
    cv2.fillPoly(layer.sharp,[corners],(32,61,40,int(235*alpha)),cv2.LINE_AA)
    paths=[[(0,0),(100,0),(100,100),(0,100),(0,0)],[(50,0),(50,100)],[(0,20),(16,20),(16,80),(0,80)],[(100,20),(84,20),(84,80),(100,80)],[(0,36),(5,36),(5,64),(0,64)],[(100,36),(95,36),(95,64),(100,64)]]
    paths.append([(50+8.7*math.cos(a),50+13.4*math.sin(a)) for a in np.linspace(0,2*math.pi,80)])
    for points in paths:tactics.draw_path(layer,[board(p) for p in points],fx.CHALK,alpha=alpha*.55,width=2,arrow=False)


def freeze(scene,local,output):
    base=still(scene['second'])
    morph=fx.ease_in_out((local-.65)/.85)*(1-fx.ease_in_out((local-3.9)/.8))
    # Same camera-to-board rhythm, glow composite and elastic marker animation as GameBuddy.
    dim=(base.astype(np.float32)*(1-.78*morph)).astype(np.uint8)
    layer=fx.Layers(dim);pitch(layer,morph)
    layer=fx.Layers(layer.compose(.5))
    players={p['id']:p for p in scene['players']}
    positions={p['id']:np.array(p['foot'])*1.5*(1-morph)+board(p['board'])*morph for p in scene['players']}
    enter=fx.ease_out(local/.35)
    for route in scene['routes']:
        if route['kind']!='option':continue
        tactics.draw_path(layer,[positions[route['a']],positions[route['b']]],fx.CYAN,
                         reveal=fx.ease_out((local-.25)/.8),alpha=.9*enter,width=4,dashed=True)
    for p in scene['players']:
        color=fx.CYAN if p['team']=='MCI' else tactics.RED
        tactics.draw_marker(layer,positions[p['id']],color,p['label'] if p['active'] else '',output,
                           alpha=enter,active=p['active'],perspective=1-morph)
    if morph>.02:
        fx.rect(layer,70,250,570,760,fx.VOID,.82*morph)
        layer.paste(fx.text_rgba('TACTICAL SNAPSHOT',fx.DIN,30,fx.CYAN,2),100,285,alpha=morph)
        lines={'build':['CARRY TOWARDS','THE PRESS','Look ahead.','Notice the far-side width.'],
               'combine':['FROM WIDE','TO INSIDE','Follow the ball infield.','Check the runner ahead.'],
               'release':['A CROWDED','CENTRE','Look to the right.','Watch the next action.']}[scene['id']]
        for i,line in enumerate(lines):layer.paste(fx.text_rgba(line,fx.DIN,48 if i<2 else 27,fx.CHALK if i<2 else fx.MUTED,1),100,355+i*72,alpha=morph)
        layer.paste(fx.text_rgba('MCI',fx.DIN,26,fx.CYAN,2),680,800,alpha=morph)
        layer.paste(fx.text_rgba('NEW',fx.DIN,26,tactics.RED,2),810,800,alpha=morph)
        layer.paste(fx.text_rgba('DASHED = OPTION / NOT A COMPLETED PASS',fx.DIN,22,fx.MUTED,1),1000,806,alpha=morph)
    fx.draw_caption(layer,local,0,5,scene['title'],scene['subtitle'],color=fx.ORANGE)
    layer.paste(fx.text_rgba('EDITORIAL FREEZE / '+scene['clock'],fx.DIN,24,fx.CYAN,2),1820,170,anchor='rt')
    layer.paste(fx.text_rgba('REVIEWED FOOT ANCHORS / SCHEMATIC BOARD / NO OPTICAL TRACKING',fx.DIN,20,fx.MUTED,1),W-70,H-30,anchor='rt')
    return layer.compose(.65)


def render_frame(output,enhanced=True):
    if not enhanced:return frame_at(output)
    segment,second=locate(output);local=output-segment['outputStart']
    if segment['kind']=='intro':
        return fx.render_intro(round(local*fx.FPS),round(2.8*fx.FPS),base_frame=still(8),copy={
            'brand':True,'brandName':'PITCHPRISM','brandTagline':'YOUR AI FOOTBALL COMPANION',
            'headline':'SEE THE PLAY','headlineSize':192,'contextEn':'FROM BUILD-UP TO THE BOX',
            'contextSubEn':'Manchester City x Newcastle / a source-grounded story',
            'player':'READ THE SPACE. FOLLOW THE BALL.','team':'MCI'})
    if segment['kind']=='outro':
        return fx.render_outro(round(local*fx.FPS),round(4.4*fx.FPS),base_frame=still(66.56),copy={
            'nameEn':'BEYOND THE SCORE','nameCn':'MANCHESTER CITY x NEWCASTLE / SUPPLIED EXCERPT',
            'points':'0 - 0','pointsUnit':'','pointsLabel':'VISIBLE SCOREBOARD',
            'chips':[('BUILD',fx.CYAN),('COMBINE',fx.ORANGE),('LOOK RIGHT',fx.GREEN)],
            'sourceNote':'USER-SUPPLIED FOOTAGE / REVIEWED OBSERVATIONS / NO OFFICIAL xG',
            'brandCredit':'PitchPrism / EVERY ANGLE TELLS A STORY'})
    if segment['kind']=='freeze':return freeze(next(s for s in MATCH['scenes'] if s['id']==segment['scene']),local,output)
    base=frame_at(second)
    if segment['kind']=='rewind':
        base[:,:,0]=np.roll(base[:,:,0],-7,axis=1);base[:,:,2]=np.roll(base[:,:,2],7,axis=1);base[::3]=(base[::3]*.7).astype(np.uint8)
    layer=fx.Layers(base)
    if segment['kind'] in ('replay','rewind'):
        fx.rect(layer,90,175,445,236,fx.VOID,.85)
        layer.paste(fx.text_rgba('REPLAY / 0.5x' if segment['kind']=='replay' else 'LOOK AGAIN',fx.DIN,32,fx.CYAN,2),110,186)
    if segment['kind']=='replay':fx.draw_caption(layer,local,0,7.6,'THE RIGHT-SIDE OPTION','Watch the ball leave the central crowd. Original action, slowed for clarity.',color=fx.CYAN)
    if segment['kind']=='live':
        cues=[(0,5,'PATIENCE BEFORE PROGRESSION','Watch City circulate, then carry towards halfway.'),(10,16,'USE THE FAR SIDE','The broadcast follows play towards the far touchline.'),(27.2,33,'COMBINE ON THE FLANK','Follow the short exchanges before the ball comes infield.'),(39,44,'DEFENDERS BETWEEN BALL AND GOAL','The central route remains contested.'),(57,62,'FOLLOW THE NEXT ACTION','Play moves right; watch the contest continue.')]
        for a,b,title,sub in cues:fx.draw_caption(layer,second,a,b,title,sub,color=fx.CYAN)
    layer.paste(fx.text_rgba('PITCHPRISM / SOURCE-GROUNDED VIEW',fx.DIN,20,fx.MUTED,1),W-65,H-30,anchor='rt')
    return layer.compose(.4)


def reuse_manifest():
    files=[Path(fx.__file__),Path(tactics.__file__),Path(__file__)]
    return {'library':'product/broadcast-fx/library.json','functions':['legacy.render_intro','legacy.render_outro','legacy.Layers','legacy.draw_caption','legacy.ease_in_out','tactics.draw_marker','tactics.draw_path'],
            'rendererHashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
