"""Hash-bound observations for the user-supplied match, separate from synthetic fixtures."""
import json
import math
from pathlib import Path

CLIP = json.loads((Path(__file__).parent / 'data/clip.json').read_text())


def snapshot(second):
    if isinstance(second, bool) or not isinstance(second, (int, float)):
        raise ValueError('Source time must be numeric')
    second = float(second)
    if not math.isfinite(second) or not 0 <= second <= CLIP['durationSeconds']:
        raise ValueError('Source time is outside the supplied clip')
    events = [o for o in CLIP['observations'] if o['second'] <= second]
    scene = next((s for s in reversed(CLIP['scenes']) if s['second'] <= second), None)
    chapter = next((c for c in CLIP['chapters'] if c['start'] <= second < c['end']), CLIP['chapters'][-1])
    return dict(matchId=CLIP['id'], synthetic=False, sourceSecond=second, events=events,
                scene=scene, chapter=chapter, scope=CLIP['scope'],
                stats={'scoreboard': {'MCI': 0, 'NEW': 0}, 'xg': None, 'passAccuracy': None},
                facts=[{'id': 'clip-score', 'label': 'Visible scoreboard', 'value': '0–0', 'source': events[0]['source']}],
                missing=CLIP['missing'])


def angles(state):
    return [dict(id=e['id'], evidenceIds=[e['id']], description=e['text']) for e in state['events']]


def local_story(state, mode='casual', team='all', player='all'):
    latest = state['events'][-1]
    scene = state['scene']
    if latest.get('scene') and scene:
        text = scene['analysis'] if mode == 'analyst' else scene['casual']
        title = scene['title']
        role = next((p for p in scene['players'] if p['id'] == player), None)
        if role:
            text += ' Focus on the highlighted ' + role['label'].lower() + ' role in the selected still.'
    else:
        text, title = latest['text'], state['chapter']['title'].split(' / ', 1)[-1].upper()
    return dict(headline=title, explanation=text, evidenceIds=[latest['id']], angle=latest['id'],
                provider='local', sourceSecond=state['sourceSecond'], mode=mode,
                validation='Manually reviewed source observation; local editorial template, no model call.')


SYSTEM = """You are PitchPrism's football companion. This context is a real user-provided broadcast excerpt,
not the separate synthetic analytics fixture. Use read_match_state, read_evidence, then validate_story.
Only supplied manually reviewed observations are evidence. Distinguish visible actions from interpretation.
Board coordinates and dashed routes are editorial schematics, never measured tracking or completed passes.
Do not invent xG, possession, player identities, speed, event counts, match date or full-match results.
The scoreboard is visible but numbers are rendered by code: do not write numbers or quantitative claims in prose.
No future events, causal certainty, predictions or claims about unseen space. Explain in English.
Choose an available angle and cite its inspected evidence. Keep headline under 70 characters and explanation
under 340 characters. Submit by validate_story tool. Be concrete for a fan, precise and cautious for an analyst."""

AGENT_CONTEXT = dict(system=SYSTEM, angles=angles, local_story=local_story)
