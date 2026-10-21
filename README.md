<div align="center">

<img src="product/football/watch/mark.svg" width="65" alt="PitchPrism mark">

# PitchPrism

**An AI-powered football companion that turns match data into visual stories and personalized insights.**

[Open the demo](https://imhaojie.github.io/PitchPrism/) · [97-second match video](https://github.com/imhaojie/PitchPrism/releases/download/football-match-v2/enhanced.mp4) · [Judge instructions](docs/football/JUDGING.md) · [Project pitch](docs/football/PITCH.md)

![PitchPrism match room](docs/football/match-room.png)

</div>

Watch a Manchester City × Newcastle excerpt through **GameBuddy's original glass player, three-state layout, drawer, controls and animated companion**. The original broadcast FX functions provide the branded opening, glowing foot markers, animated options, camera-to-board transitions and closing sequence. The adaptation changes the sport, source evidence and service adapter; it preserves the original interaction and animation system.

The supplied **66.6-second source** becomes a **97.2-second, 1080p/25fps enhanced video** with three reviewed tactical freezes and a half-speed replay. All original video frames are retained before the additional replay. Broadcast audio is preserved on live sections; editorial freezes/branding are silent. Captions are English; generated narration is not included.

## What you can test

- Play, seek, change speed, sound and fullscreen in the original player.
- Open full-pitch or half-pitch views; inspect the diagram from the labelled source still.
- Revisit six chapters and switch between source/enhanced video at the same source moment.
- Read the observation behind an explanation; change fan/analyst familiarity or focus on a role.
- Inspect genuine missing values: official xG and full-match pass accuracy remain **unavailable**.

The scoreboard reads **MCI 0–0 NEW** throughout the reviewed excerpt. No goal is shown. Only the close-up shirt text **BERNARDO / 20** is identified; other players are represented by roles. Foot anchors are manually reviewed on selected frames. Board coordinates and dashed arrows are editorial schematics, not optical tracking, measured positions or completed-pass records.

The separate fictional fixture in `data/match.json` still tests football analytics. It is never joined to the real video. See [source analysis](docs/football/SOURCE-ANALYSIS.md).

## Run locally

Python 3.11+; the app frontend needs no npm build:

```bash
git clone https://github.com/imhaojie/PitchPrism.git
cd PitchPrism
python3 -m venv .venv
# Fetch the frozen, hash-verified demo media; uses Python standard library.
.venv/bin/python product/football/scripts/fetch_media.py
.venv/bin/python -m product.football.server --port 4180
```

Open **http://127.0.0.1:4180/**. Space plays/pauses; F toggles fullscreen; Esc closes the current panel. The tactical panel explicitly labels the reviewed still's timestamp rather than pretending to follow players live.

To reproduce the FX from the exact original input, install FFmpeg and the renderer dependencies:

```bash
.venv/bin/pip install -r product/football/requirements.txt
.venv/bin/python product/football/scripts/render.py --source /path/to/original/match.mp4
.venv/bin/python product/football/scripts/export_demo.py
```

The input must match the SHA-256 in `product/football/data/clip.json`. A different video requires its own analysis and anchors. MP4s, build outputs and credentials stay outside Git; frozen media is in [Releases](https://github.com/imhaojie/PitchPrism/releases/tag/football-match-v2).

## Microsoft integration

The active football app has no AWS runtime dependency. The **Azure Foundry / Azure OpenAI v1** adapter reuses the bounded **read state → inspect evidence → validate story** tool loop, with a separate prompt/context for the real clip and the synthetic test fixture. It supports Entra/managed identity or a server-side key. Context limits, evidence references, source-time bounds and numeric guards are enforced before a response is accepted.

**Live Foundry and Azure deployment remain unverified.** No active Azure subscription has been confirmed. The public demo uses honest **LOCAL EDITORIAL** explanations; it never simulates a cloud response. The user selected the free trial; no paid upgrade or Azure resources have been created.

```bash
cp .env.example .env
# Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT.
# Entra: az login, AZURE_USE_ENTRA=1, Cognitive Services OpenAI User access.
.venv/bin/python product/football/scripts/verify_foundry.py
```

[Azure setup and Bicep](infra/azure/README.md) target Container Apps Consumption with managed identity, scale-to-zero and bounded calls. Adapter tests and template compilation do not prove cloud inference.

## Verification and reuse

```bash
npm ci --prefix product --ignore-scripts
.venv/bin/python product/scripts/check.py --full
```

The gate passes **556 behavior tests**, privacy/syntax checks and 50 inherited offline CDK resource assertions. Both MP4s pass full decode. Browser checks cover actual playback, layout transitions, chapter/freezes, source switching, evidence, preferences and controls. [Validation](docs/football/VALIDATION.md) · [QA inventory](docs/football/QA-v2.md).

PitchPrism adapts MIT-licensed [GameBuddy](https://github.com/imhaojie/BroadcastCode-2026), snapshot `17d74fd2a5df64a240198a7305312174de7684b0`, in an independent repository. The original checkout is unchanged. Directly imported modules include StageLayout, GlassManager, PlayerControls, Drawer, ContentPanel, Inspector, GameBuddyAmbient, CourtPanel and source/output mapping. The renderer calls the original `broadcast_fx.legacy` and `broadcast_fx.tactics` functions. These source assets use Python/OpenCV/Pillow/FFmpeg rather than Remotion. [Migration details](docs/football/MIGRATION.md).

The NBA × AWS award belongs to **GameBuddy**, not PitchPrism. The organizers must confirm eligibility of an enhancement to previously winning open-source work. The supplied broadcast excerpt is a development/demo input, separate from the synthetic event fixture required for competition. Submission eligibility and media permission are not established by this implementation. [Official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md).

Original code is MIT; broadcast footage and third-party assets retain their owners' rights. The MIT licence does not grant broadcast redistribution rights. See [notices](THIRD_PARTY_NOTICES.md). Earlier `football-demo-v1` is a superseded synthetic prototype, not evidence for the current visuals, media or model integration.
