"""Burn English editorial captions into an actual Playwright screen recording.

No cloud call, generated voice or copyrighted music is used. Requires Pillow/FFmpeg.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[1]
record = json.loads((HERE / 'build/recording/segments.json').read_text())
source = Path(record['recordingFile'])
target = HERE / 'build/PitchPrism-English-Demo.mp4'
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-of', 'json', str(source)]))
raw_duration = float(probe['format']['duration'])
trim = max(0, raw_duration - record['recordingEnd'])
duration = min(record['recordingEnd'], 110)
fps, width, height = 24, 1440, 1000
decode = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(trim), '-i', str(source), '-t', str(duration),
    '-vf', f'fps={fps},scale={width}:{height}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
encode = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
    '-video_size', '1920x1080', '-framerate', str(fps), '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
    '-t', str(duration), '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
font = ImageFont.truetype(str(HERE / 'watch/fonts/dm-sans.ttf'), 27)
small = ImageFont.truetype(str(HERE / 'watch/fonts/dm-sans.ttf'), 13)
captions = []
for item in record['segments']:
    panel = Image.new('RGB', (1920, 100), '#1b3428')
    draw = ImageDraw.Draw(panel)
    lines = textwrap.wrap(item['text'], width=112)
    for index, line in enumerate(lines):
        draw.text((960, 22 + index * 34), line, fill='#eef4df', font=font, anchor='mt')
    captions.append(panel)

frame_bytes, count = width * height * 3, 0
try:
    while True:
        raw = decode.stdout.read(frame_bytes)
        if not raw:
            break
        if len(raw) != frame_bytes:
            raise RuntimeError('Truncated decoded screen frame')
        frame = Image.new('RGB', (1920, 1080), '#f5f4ee')
        frame.paste(Image.frombytes('RGB', (width, height), raw), (240, 0))
        second = count / fps
        index = max(i for i, item in enumerate(record['segments']) if item['start'] <= second)
        frame.paste(captions[index], (0, 980))
        draw = ImageDraw.Draw(frame)
        draw.text((25, 950), 'PITCHPRISM', fill='#61754e', font=small)
        draw.text((1680, 950), 'ACTUAL APP RECORDING', fill='#61754e', font=small)
        encode.stdin.write(frame.tobytes())
        count += 1
finally:
    decode.stdout.close()
    encode.stdin.close()
if decode.wait() or encode.wait():
    raise RuntimeError('Screen recording decode/encode failed')
subprocess.run(['ffmpeg', '-v', 'error', '-i', str(target), '-f', 'null', '-'], check=True)
metadata = {'file': target.name, 'durationSeconds': count / fps, 'width': 1920, 'height': 1080,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'fullDecode': True,
            'language': 'English captions', 'audio': 'silent stereo; no narration/music',
            'actualApplicationRecording': True, 'cloudStatusDisclosed': 'LOCAL; live Azure verification pending'}
(HERE / 'build/demo-manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
