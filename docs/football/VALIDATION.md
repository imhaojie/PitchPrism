# Release validation — v1.0.0

2026-10-24. The current demo uses the reviewed **118.4-second** movie. Earlier preview receipts are retained in the [preview archive](../archive/football-previews/README.md).

## Engineering

The complete offline gate passed **567 behavior tests, no skips**, source privacy checks, syntax checks and 50 preserved offline infrastructure assertions. New regressions cover all six chapter mappings, all nine reading-step jumps, freeze boundaries, replay/rewind, web/video focus and option agreement, altered media bytes, stale timelines, manifest/data identity, and label bounds/collisions across all nine readings. Offline infrastructure assertions do not certify Azure deployment or cloud inference.

The optional companion PNG export and renderer preview command also ran successfully with the documented local tooling. Generated media and QA receipts remain outside Git.

## Media

- Enhanced movie: **2,960 frames**, **1920×1080**, **25fps**, **118.4s**, H.264/yuv420p and AAC. SHA-256 `986f282682283a789c40150832840db910dd1ce16e0017318558fda021f5e0ed`; identical to the reviewed delivery.
- Source: lossless remux, **1,665 video frames**, **1280×720**, **25fps**, 66.6s video / 66.618s container. Its hash differs from the original input and is locked separately.
- Both canonical release files passed full video/audio decode again during release preparation. All source frames occur once in order before the additional replay.
- The reviewed render's audit recorded **27,084 visible text-box checks**, **2,811 role-label pair checks with zero overlaps**, and 20 encoded-frame comparisons. System DIN/DM Sans glyph coverage and measured text bounds were checked during rendering. These checks concern this reviewed export, not arbitrary future inputs.
- Nominal pitch geometry follows IFAB Law 1 proportions. Options and board positions remain editorial; no optimal play, calibrated tracking, offside decision or completed pass is inferred.

## Browser

The actual static export was exercised in Chrome, including real video playback, all six chapter buttons and all nine reading-step buttons. Chapter output times were 2.8, 11.2, 36.4, 42.6, 54.2 and 86.4 seconds. Source preview stills remained at the corresponding 8.0, 37.8 or 56.8 seconds during step changes.

Source/enhanced switching was exercised at source 37.8: enhanced step 58.3 → source 37.8 → enhanced first reading 54.2. Actual playback reached readyState 4 and the football companion entered its running state. Desktop and 390×844 studio layouts were visually inspected with no horizontal overflow or clipped reading/heading text in the checked states. All nine readings were rechecked in the browser after adding label avoidance: camera and board role labels had zero pairwise overlaps in these states. Modal entry/close, option semantics, chapter copy and responsive wrapping were inspected separately from automated tests.

## Limits

The public demo uses **LOCAL EDITORIAL** explanations. No real Azure inference/deployment is certified by this release. Missing official events, xG, full-match statistics, identities and tracking remain missing. Competition eligibility, broadcast permissions and a supported public video-platform submission URL remain separate [submission requirements](SUBMISSION.md).
