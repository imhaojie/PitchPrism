<div align="center">

<img src="product/football/watch/mark.svg" width="64" alt="PitchPrism">

# PitchPrism

**An AI-powered football companion that turns match data into visual stories and personalized insights.**

[Live demo](https://imhaojie.github.io/PitchPrism/) · [Watch / download MP4](https://github.com/imhaojie/PitchPrism/releases/download/v1.0.0/enhanced.mp4) · [Documentation](docs/README.md) · [Releases](https://github.com/imhaojie/PitchPrism/releases)

[![Quality](https://github.com/imhaojie/PitchPrism/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/imhaojie/PitchPrism/actions/workflows/quality.yml)
[![Demo](https://github.com/imhaojie/PitchPrism/actions/workflows/football.yml/badge.svg?branch=main)](https://github.com/imhaojie/PitchPrism/actions/workflows/football.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-a1f5d8)](LICENSE)

![PitchPrism tactical studio](https://github.com/imhaojie/PitchPrism/releases/download/v1.0.0/tactical-studio.jpg)

</div>

See the carrier, compare the options, and return to the action. PitchPrism brings a cinematic football player, a tactical studio and evidence-backed explanations into one viewing experience.

## Features

- **Tactics inside the video.** A reviewed 118.4-second, 1080p/25fps movie includes animated option arrows, role highlights, nine reading steps, pitch transitions and half-speed replay. English text is burned into the MP4.
- **An interactive tactical studio.** Explore three reviewed moments with source-frame highlights, a pitch diagram and independent routes, focus-area and label controls.
- **One source clock.** Six chapters, tactical steps and source/enhanced switching resolve to the same original moment, including freezes and replay.
- **A personal viewing experience.** Choose immersive, full-pitch or half-pitch layouts; adjust football familiarity and focus on a visible role. A football companion reacts to playback.
- **Inspectable explanations.** Read the evidence behind each local editorial story. The optional Azure Foundry adapter adds a bounded read → inspect → validate tool loop.

## Quick start

Requires **Python 3.11+**. Playback and local explanations use the Python standard library; the frontend is native JavaScript and needs no build step.

```bash
git clone https://github.com/imhaojie/PitchPrism.git
cd PitchPrism
python3 -m venv .venv
source .venv/bin/activate
python product/football/scripts/fetch_media.py
python -m product.football.server --port 4180
```

Open **http://127.0.0.1:4180/**. On Windows, activate with `.venv\Scripts\activate`. No account or cloud credentials are needed. Media downloads are checked against committed SHA-256 values before use.

**Controls:** Space plays/pauses; F toggles fullscreen; Esc closes panels. Open **战术演播室 / Tactical Studio** for the three-step readings. Chapter labels use source time; the player shows enhanced-video time.

## What the demo knows

The demonstration uses a supplied **66.6-second Manchester City × Newcastle excerpt**, with a visible **0–0** scoreboard. All 1,665 source frames appear once in order before the additional replay; live sections retain broadcast audio. Explanatory freezes and bookends are silent.

Selected foot anchors and observations were manually reviewed. Pitch positions and dashed arrows are editorial schematics: an arrow shows an option, not a completed pass or measured open lane. Official events, xG, full-match statistics, continuous tracking and unverified player identities remain unavailable. A separate synthetic analytics fixture is used for tests and is never joined to this footage.

The public demo uses **LOCAL EDITORIAL** explanations. **Live Azure inference and deployment have not been verified.** Adapter tests and infrastructure compilation are separate from cloud execution.

## Develop and verify

Use **Node.js 22+** for the complete engineering gate:

```bash
npm ci --prefix product --ignore-scripts
python product/scripts/check.py --full
python product/football/scripts/export_demo.py
python product/football/scripts/serve_demo.py --port 4181
```

The static export opens at **http://127.0.0.1:4181/site/**. It uses the same media, observations and source/output mapping as the local server. The exporter rejects mismatched media hashes or timing. Browser playback and full media decode are checked separately from offline tests.

[Development guide](CONTRIBUTING.md) · [Architecture](docs/football/ARCHITECTURE.md) · [Media pipeline](docs/football/MEDIA.md) · [Validation](docs/football/VALIDATION.md)

## Optional Azure Foundry

Install `product/football/requirements.txt`, copy `.env.example` to `.env`, and configure the server-side endpoint and deployment. Entra/managed identity is supported; credentials never belong in browser code.

```bash
python -m pip install -r product/football/requirements.txt
python product/football/scripts/verify_foundry.py
```

A successful API response with a validated tool trace is required before a real Foundry receipt exists. See [Azure configuration](infra/azure/README.md). Cloud deployment is optional and is not performed by the quick start or GitHub Pages workflow.

## Repository map

| Path | Purpose |
| --- | --- |
| `product/football/` | Application, evidence, editorial stories, media tools and tests |
| `product/watch/` | Shared viewing, layout, controls and time-mapping modules |
| `product/broadcast-fx/` | Rendering primitives |
| `product/tests/` | Shared behavior and regression tests |
| `infra/azure/` | Optional Azure configuration and guarded deployment tooling |
| `docs/football/` | Product, media and validation documentation |
| `docs/archive/` | Historical engineering records and source provenance |

Media, credentials, build outputs and account receipts stay outside Git. Versioned video assets are distributed through Releases.

## License and credits

Code is available under the [MIT License](LICENSE). Third-party software, fonts and source attribution are documented in [Third-party notices](THIRD_PARTY_NOTICES.md). Broadcast video, audio and third-party marks retain their owners' rights and are not licensed by the code's MIT license.
