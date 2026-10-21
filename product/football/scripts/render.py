"""Render the reviewed user clip through the original GameBuddy broadcast FX library."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parents[1]


def chunk(job):
    from gamebuddy_fx import configure,render_frame
    source,start,end,destination=job;configure(source)
    encoder=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','bgr24',
        '-video_size','1920x1080','-framerate','25','-i','-','-an','-c:v','libx264','-preset','veryfast',
        '-crf','20','-pix_fmt','yuv420p','-threads','2',destination],stdin=subprocess.PIPE)
    try:
        for index in range(start,end):encoder.stdin.write(render_frame(index/25).tobytes())
    finally:encoder.stdin.close()
    if encoder.wait():raise RuntimeError('Original GameBuddy FX encode failed')
    return destination


def audio(source,timeline,target):
    chains=[];labels=[]
    for i,s in enumerate(timeline):
        duration=round(s['outputEnd']-s['outputStart'],3);label=f'a{i}';labels.append(f'[{label}]')
        if s['kind'] in ('live','replay'):
            rate=(s['sourceEnd']-s['sourceStart'])/duration
            chains.append(f"[0:a]atrim=start={s['sourceStart']}:end={s['sourceEnd']},asetpts=PTS-STARTPTS,atempo={rate},apad,atrim=duration={duration},afade=t=in:d=0.025,afade=t=out:st={max(0,duration-.025)}:d=0.025[{label}]")
        else:chains.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={duration}[{label}]')
    chains.append(''.join(labels)+f'concat=n={len(labels)}:v=0:a=1[out]')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-filter_complex',';'.join(chains),'-map','[out]','-c:a','aac','-b:a','160k',str(target)],check=True)


def render(source,workers):
    from gamebuddy_fx import MATCH,reuse_manifest
    duration=MATCH['production']['durationSeconds'];frames=round(duration*25)
    build=HERE/'build';parts=build/'real-fx-chunks';parts.mkdir(exist_ok=True,parents=True)
    jobs=[(str(source),i,min(i+100,frames),str(parts/f'{i:05}.mp4')) for i in range(0,frames,100)]
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for n,result in enumerate(pool.map(chunk,jobs)):print(f'{n+1}/{len(jobs)} chunks: {Path(result).name}',flush=True)
    playlist=parts/'concat.txt';playlist.write_text(''.join(f"file '{Path(j[-1]).name}'\n" for j in jobs))
    audio(source,MATCH['production']['timeline'],parts/'sound.m4a')
    target=build/'enhanced.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(playlist),'-i',str(parts/'sound.m4a'),'-map','0:v','-map','1:a','-t',str(duration),'-c','copy','-movflags','+faststart',str(target)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-map','0:v:0','-map','0:a:0','-c','copy','-map_metadata','-1','-movflags','+faststart',str(build/'source.mp4')],check=True)
    outputs=[]
    for path in [build/'source.mp4',target]:
        subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        outputs.append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),durationSeconds=float(probe['format']['duration']),frames=int(video['nb_frames']),width=video['width'],height=video['height'],fps=video['r_frame_rate'],fullDecode=True,audio='Original broadcast audio, preserved without re-encoding.' if path.name=='source.mp4' else 'Original broadcast audio on live sections; half-speed replay; silence on editorial freezes/branding'))
    manifest=dict(synthetic=False,source=MATCH['source'],renderer='Original GameBuddy broadcast-fx library',reuse=reuse_manifest(),modelUsedForRender=False,notTracking=True,outputs=outputs,timeline=MATCH['production']['timeline'],dataSha256=hashlib.sha256((HERE/'data/clip.json').read_bytes()).hexdigest())
    (build/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Real match render and full decode complete',flush=True)


if __name__=='__main__':
    import cv2
    from gamebuddy_fx import configure,render_frame
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--poster-only',action='store_true');parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();source=args.source.resolve();configure(source);build=HERE/'build';build.mkdir(exist_ok=True)
    for second in [1.4,11.3,13.1,46.8,70.7,89.2,94.7]:cv2.imwrite(str(build/f'match-fx-{second}.jpg'),render_frame(second),[cv2.IMWRITE_JPEG_QUALITY,93])
    cv2.imwrite(str(HERE/'watch/poster.jpg'),render_frame(11.3),[cv2.IMWRITE_JPEG_QUALITY,93])
    if not args.poster_only:render(source,args.workers)
