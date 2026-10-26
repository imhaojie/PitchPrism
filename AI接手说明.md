# PitchPrism maintenance handoff

Updated 2026-10-26. Read the [README](README.md), [architecture](docs/football/ARCHITECTURE.md), [media workflow](docs/football/MEDIA.md) and [source provenance](docs/football/MIGRATION.md). The application lives in `product/football/`; start it with `python -m product.football.server --port 4180`.

## Interface and media

The v1.0.1 interface is English throughout: navigation, chapters, nine tactical readings, insights, preferences, help, accessibility labels and all 12 appearance-editor groups. The web readings use the reviewed English movie script. Shared components retain their existing defaults; the active app opts into English. The appearance editor uses an explicit translation hook and a football-owned copy catalog. Narrow layouts at 320px and 390px were checked for English wrapping and clipping.

The v1.1.0 movie (broadcast package, 3D tactical view, measured tactical layers, new mark and bookends) replaces v1.0.0 with identical timing: 118.4 seconds, 1920×1080, 25fps, SHA-256 `9b6c807bdbd31d45311738e3ae42f655fe35d63d43078c2af0f10bde659af613`. It is rendered by `render_tactical_video.py` + `pitch3d.py`; tactical layers are validated by `tactical_geometry.py` against `data/tactical-geometry.json`. The canonical `build/enhanced.mp4` is byte-identical to the render. Media stays outside Git and is distributed through Releases.

The source excerpt is 66.6 seconds, MCI 0–0 NEW, with no goal shown. Original and lossless-remux identities differ; see `data/source-lock.json`. Reviewed observations and foot anchors remain unchanged. `data/clip.json` retains the media-bound source data, including historical display names; the interface renders English role names without changing its hash. The release manifest separates original rendering inputs from published player data.

## Time and evidence

The three enhanced freezes span 10.8–24.0, 53.8–67.0 and 86.0–99.2 seconds. They correspond to source 8.0, 37.8 and 56.8 seconds. Readings change at local offsets 0, 4.1 and 8.2 seconds; chapter/step jumps include a 0.4-second settling offset. `product/watch/adapters/editorial-timeline.js` owns these jump helpers. Source/enhanced switching preserves source time.

`data/tactical-story.json` is the English editorial script. Role highlights refer to manually reviewed source pixels. Pitch positions and dashed options are editorial schematics, not tracking, offside decisions or completed passes. Nominal field geometry follows 105×68m proportions and IFAB Law 1. The football companion is an original SVG/CSS component.

`data/match.json` is a separate synthetic test fixture and must never support stories about the real footage. Keep official events, xG, full-match statistics, tracking and unverified identities missing. Do not use future observations in live explanations.

## Verification and publication

Run `python3 product/scripts/check.py --full`. Browser checks, media decode, Bicep compilation and actual cloud inference are separate verification layers. The v1.1.0 working tree passes 575 offline behavior tests. All nine readings and six chapter mappings retain the reviewed movie timing. [Validation](docs/football/VALIDATION.md).

Fetching and static export verify media hashes, player-data binding and the exact timeline. The v1.1.0 update publishes new movie bytes and a matching manifest and media lock; the older v1.0.0/v1.0.1 releases remain immutable. Publish the v1.1.0 media before updating the default branch so Pages can fetch the matching files. Do not overwrite released assets or commit generated media, account receipts, credentials or build outputs.

Azure Foundry and Bicep tooling exist, but real deployment/inference remains unverified. The public demo is LOCAL EDITORIAL. The free-trial-only restriction, prohibition on paid upgrades and prohibition on AWS resource changes remain in force. Competition eligibility, media permission and a supported video-platform submission URL are separate requirements; software publication does not establish them.

## Azure integration-only update — 26 October 2026

Keep the reviewed film and main demo. `azure_services.py` implements optional Content Safety, Blob operational receipts, Key Vault secret resolution and Application Insights, alongside existing Foundry, Container Apps and Entra identity. All supporting service flags default to off. `watch/azure.html` presents the seven implemented connections. The student account has an enabled subscription and credit; Azure OpenAI preflight was rejected by local regulatory eligibility. Do not bypass it or imply a successful generative model run. A separately authorized minimal Content Safety F0 call succeeded through Entra ID on one existing English caption. See [per-service verification](docs/football/AZURE-VERIFICATION.md). Account-specific receipts remain ignored. Vimeo URL: https://vimeo.com/1239357832, saved to the competition project.
