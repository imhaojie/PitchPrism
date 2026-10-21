# Current validation — supplied match v2

2026-10-21. Replaces the synthetic v1's media/browser evidence.

- Full engineering gate: **556 behavior tests, no skips**, source privacy, Python/JavaScript syntax, 50 inherited offline CDK resource checks. Additional real-clip tests cover missing values, future-evidence exclusion, rewind, exact 25fps timeline boundaries, complete source coverage, reviewed anchors, role personalization, HTTP endpoints and the shared Foundry tool loop using fake transport.
- Source delivery: 1,665 frames, 1280×720, 25fps, 66.618s container. Original 66.6s video is repackaged without re-encoding. Input SHA is retained separately from the repackaged MP4 hash.
- Enhanced: 2,430 frames, 1920×1080, 25fps, **97.2s**, original live audio, half-speed replay. Both files passed `ffmpeg -v error -i … -f null -` full video/audio decode.
- Browser: actual Chrome playback and pause, speed, mute, fullscreen, immersive/full/half, drawer chapters, chapter-to-freeze seek, source/enhanced round trip at source 37.8s, local explanation, preferences and original inspector. No JavaScript page errors observed.
- Visual checks: opening, freeze overlays, field morph, replay/outro, original glass layout, readable evidence panel, 1440×900 and phone 390×844 initial view. Top-nav/panel overlap, evidence-surface contrast and mobile controls were corrected.
- Cloud: **not verified**. Adapter/tool tests do not count as actual Foundry calls. No Azure resource deployment, model inference or paid upgrade claimed.

Raw media, SHA receipts, reviewed frames and browser screenshots are generated under ignored build/artifact directories. Public source/data/output hashes are available in the release manifest and tracked media lock. Rendered captions are English; no generated narration is included. The video does not demonstrate autonomous extraction of events or automatic optical tracking.
