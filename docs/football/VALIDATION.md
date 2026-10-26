# Release validation — v1.1.0

2026-10-26. The current demo uses the broadcast-package **118.4-second** movie (v1.1.0). Timing, observations and anchors are unchanged from v1.0.0, so every chapter and reading jump below still applies. Earlier preview receipts are retained in the [preview archive](../archive/football-previews/README.md).

v1.1.0 replaces the movie and corrects two tactical readings that measured ground positions contradicted (see the [changelog](../../CHANGELOG.md)). The web Tactical Studio uses the same corrected script and measured board positions.

## Engineering

The complete offline gate passed **575 behavior tests, no skips**, source privacy checks, syntax checks and 50 preserved offline infrastructure assertions. New regressions cover all six chapter mappings, all nine reading-step jumps, freeze boundaries, replay/rewind, web/video focus and option agreement, altered media bytes, stale timelines, manifest/data identity, and label bounds/collisions across all nine readings. Offline infrastructure assertions do not certify Azure deployment or cloud inference.

The optional companion PNG export and renderer preview command also ran successfully with the documented local tooling. Generated media and QA receipts remain outside Git.

## Media

- Enhanced movie: **2,960 frames**, **1920×1080**, **25fps**, **118.4s**, H.264/yuv420p and AAC. SHA-256 `9b6c807bdbd31d45311738e3ae42f655fe35d63d43078c2af0f10bde659af613`; identical to the reviewed render, packaged without re-encoding.
- Source: lossless remux, **1,665 video frames**, **1280×720**, **25fps**, 66.6s video / 66.618s container. Its hash differs from the original input and is locked separately.
- Both canonical release files passed full video/audio decode again during release preparation. All source frames occur once in order before the additional replay.
- The render audit checked every frame: **38,605 text boxes** inside the frame, and **17,186 label pairs/label–panel pairs** with zero overlaps and zero labels covered by captions or headers. Bundled Barlow Condensed/DM Sans glyph coverage was checked. These checks concern this export, not arbitrary future inputs.
- Tactical layers use ground positions measured from visible pitch markings (largest marking residual 0.98 m, penalty-arc check within 1.2 m). Every option, covered lane, carry and zone is checked against those positions at render time and in the offline tests.
- Nominal pitch geometry follows IFAB Law 1 proportions. Options and board positions remain editorial; no optimal play, calibrated tracking, offside decision or completed pass is inferred.

## Browser

v1.1.0: the exported static demo was played in Chrome at 1440×900 and 390×844 (new movie, 118.4s, 1920×1080, playback advancing, intro/freeze/outro frames inspected). All six corrected Tactical Studio readings were stepped through with the new text and measured board positions. The only failed request is a pre-existing basketball theme asset (`dallas-mavericks.svg`), unchanged from v1.0.1 and not visible in the football demo. The v1.0.1 browser checks below cover timing that v1.1.0 did not change.

The actual static export was exercised in Chrome, including real video playback, all six chapter buttons and all nine reading-step buttons. Chapter output times were 2.8, 11.2, 36.4, 42.6, 54.2 and 86.4 seconds. Source preview stills remained at the corresponding 8.0, 37.8 or 56.8 seconds during step changes.

Source/enhanced switching was exercised at source 37.8: enhanced step 58.3 → source 37.8 → enhanced first reading 54.2. Actual playback reached readyState 4 and the football companion entered its running state. Desktop and 390×844 studio layouts were visually inspected with no horizontal overflow or clipped reading/heading text in the checked states. All nine readings were rechecked in the browser after adding label avoidance: camera and board role labels had zero pairwise overlaps in these states. Modal entry/close, option semantics, chapter copy and responsive wrapping were inspected separately from automated tests.

Additional English UI QA covers all 12 appearance-editor groups, the shared controls and chapter drawer, all nine English readings, accessibility attributes and 320/390px layouts.

## Limits

The public demo uses **LOCAL EDITORIAL** explanations. No real Azure inference/deployment is certified by this release. Missing official events, xG, full-match statistics, identities and tracking remain missing. Competition eligibility, broadcast permissions and a supported public video-platform submission URL remain separate [submission requirements](SUBMISSION.md).
