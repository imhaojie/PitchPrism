# PitchPrism maintenance handoff

Updated 2026-10-24. Read the [README](README.md), [architecture](docs/football/ARCHITECTURE.md), [media workflow](docs/football/MEDIA.md) and [source provenance](docs/football/MIGRATION.md). The application lives in `product/football/`; start it with `python -m product.football.server --port 4180`.

## Interface and media

The v1.0.1 interface is English throughout: navigation, chapters, nine tactical readings, insights, preferences, help, accessibility labels and all 12 appearance-editor groups. The web readings use the reviewed English movie script. Shared components retain their existing defaults; the active app opts into English. The appearance editor uses an explicit translation hook and a football-owned copy catalog. Narrow layouts at 320px and 390px were checked for English wrapping and clipping.

The reviewed movie is unchanged from the v1.0.0 media release: 118.4 seconds, 1920×1080, 25fps, SHA-256 `986f282682283a789c40150832840db910dd1ce16e0017318558fda021f5e0ed`. The canonical `build/enhanced.mp4` is byte-identical to the reviewed delivery. Media stays outside Git and is distributed through Releases.

The source excerpt is 66.6 seconds, MCI 0–0 NEW, with no goal shown. Original and lossless-remux identities differ; see `data/source-lock.json`. Reviewed observations and foot anchors remain unchanged. `data/clip.json` retains the media-bound source data, including historical display names; the interface renders English role names without changing its hash. The release manifest separates original rendering inputs from published player data.

## Time and evidence

The three enhanced freezes span 10.8–24.0, 53.8–67.0 and 86.0–99.2 seconds. They correspond to source 8.0, 37.8 and 56.8 seconds. Readings change at local offsets 0, 4.1 and 8.2 seconds; chapter/step jumps include a 0.4-second settling offset. `product/watch/adapters/editorial-timeline.js` owns these jump helpers. Source/enhanced switching preserves source time.

`data/tactical-story.json` is the English editorial script. Role highlights refer to manually reviewed source pixels. Pitch positions and dashed options are editorial schematics, not tracking, offside decisions or completed passes. Nominal field geometry follows 105×68m proportions and IFAB Law 1. The football companion is an original SVG/CSS component.

`data/match.json` is a separate synthetic test fixture and must never support stories about the real footage. Keep official events, xG, full-match statistics, tracking and unverified identities missing. Do not use future observations in live explanations.

## Verification and publication

Run `python3 product/scripts/check.py --full`. Browser checks, media decode, Bicep compilation and actual cloud inference are separate verification layers. The English update passes 570 offline behavior tests. All nine readings and six chapter mappings retain the reviewed movie timing. [Validation](docs/football/VALIDATION.md).

Fetching and static export verify media hashes, player-data binding and the exact timeline. The English update reuses the immutable v1.0.0 media; its screenshot is a separate v1.0.1 release asset. Do not overwrite released assets or commit generated media, account receipts, credentials or build outputs.

Azure Foundry and Bicep tooling exist, but real deployment/inference remains unverified. The public demo is LOCAL EDITORIAL. The free-trial-only restriction, prohibition on paid upgrades and prohibition on AWS resource changes remain in force. Competition eligibility, media permission and a supported video-platform submission URL are separate requirements; software publication does not establish them.
