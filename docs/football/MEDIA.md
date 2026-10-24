# Media and releases

The current release is **v1.0.0**. Its 118.4-second English-captioned movie contains the full 66.6-second source, three 13.2-second tactical freezes, a half-speed replay and football bookends. The MP4 is 1920×1080, 25fps, H.264/yuv420p with AAC audio. Live sections keep broadcast sound; editorial freezes are silent.

## Timing

Chapter labels are source seconds; chapter jumps enter the relevant freeze where one exists.

| Chapter source | Enhanced jump | Content |
| --- | --- | --- |
| 0.0 | 2.8 | Patient build-up |
| 8.0 | 11.2 | First tactical reading |
| 20.4 | 36.4 | Bernardo close-up |
| 26.6 | 42.6 | Work inside |
| 37.8 | 54.2 | Second tactical reading |
| 56.8 | 86.4 | Third tactical reading |

The freezes span **10.8–24.0**, **53.8–67.0** and **86.0–99.2** enhanced seconds. Each reading changes at local freeze offsets 0, 4.1 and 8.2 seconds. Reading-step jumps include a 0.4-second settling offset. Replay runs at 109.6–115.2 enhanced seconds and covers source 56.8–59.6. The committed timeline is authoritative.

## Fetch and export

```bash
python product/football/scripts/fetch_media.py
python product/football/scripts/export_demo.py
python product/football/scripts/serve_demo.py --port 4181
```

`source.mp4`, `enhanced.mp4` and `manifest.json` must match the committed lock. The manifest binds the original source identity, input-remux identity, exact video bytes, English story, render-input data and published player data. Original and remux hashes are deliberately distinct. The optional `render-inputs.zip` release asset preserves the original rendering script, reviewed input data, English story and companion PNG; its component hashes match the render receipt.

## Render an editorial movie

Install Python 3.11+, the dependencies in `product/football/requirements.txt`, and Node.js 22+. The renderer uses FFmpeg or the pinned portable FFmpeg package. It uses bundled DM Sans where system DIN is unavailable; that fallback can change typography and output hashes.

```bash
python -m pip install -r product/football/requirements.txt
npm ci --prefix product/football/watch --ignore-scripts
node product/football/scripts/export_football_buddy.cjs product/football/build/rendered/football-buddy.png
python product/football/scripts/render_tactical_video.py --source product/football/build/source.mp4
```

The input must be the exact reviewed original or its separately hash-locked lossless remux. A different match requires new observations, reviewed anchors and source identity. The renderer writes a separate MP4, previews and provenance receipt; it does not silently replace the public demo. It checks glyph coverage, measured text bounds, source coverage, frame metadata and full decode.

## Promote a reviewed render

Preserve the exact `clip.json` used by the render as `render-input-clip.json`. Align the active `production.timeline` with the reviewed receipt, then run:

```bash
python product/football/scripts/package_media.py \
  --video /path/to/reviewed.mp4 \
  --receipt /path/to/reviewed.manifest.json \
  --review-input /path/to/render-input-clip.json
```

Packaging verifies video bytes, source identity, observations, anchors, story and timeline, then writes the canonical media manifest and lock without re-encoding. A presentation-only update retains the original render-input hash separately from the current player-data hash.

Before publishing: run the full engineering gate, decode both media files, inspect encoded frames, test all chapters and source switching in the browser, and export the static demo. Upload all three canonical assets to a new versioned GitHub Release; update the fetch URL and docs with the same version. Never overwrite assets of a released version. Commit source and locks, not MP4s, account receipts or build directories.

Source code's MIT license does not grant broadcast redistribution rights. See [third-party notices](../../THIRD_PARTY_NOTICES.md). Competition submission requirements are separate from software release; see [submission notes](SUBMISSION.md).
