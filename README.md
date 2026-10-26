<div align="center">

<img src="product/football/watch/mark.svg" width="76" alt="PitchPrism logo">

# PitchPrism

### See the game. Understand the moment.

An AI-powered football companion that turns match data into visual stories and personalized insights.

[**Try the demo**](https://imhaojie.github.io/PitchPrism/) · [**Watch the film**](https://vimeo.com/1239357832) · [Documentation](docs/README.md) · [Releases](https://github.com/imhaojie/PitchPrism/releases)

[![Quality](https://github.com/imhaojie/PitchPrism/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/imhaojie/PitchPrism/actions/workflows/quality.yml)
[![Demo](https://github.com/imhaojie/PitchPrism/actions/workflows/football.yml/badge.svg?branch=main)](https://github.com/imhaojie/PitchPrism/actions/workflows/football.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](#quick-start)
[![JavaScript](https://img.shields.io/badge/JavaScript-native-F7DF1E?logo=javascript&logoColor=black)](#architecture)
[![License: MIT](https://img.shields.io/badge/Code-MIT-a1f5d8)](LICENSE)

![A 3D tactical reading in PitchPrism](https://github.com/imhaojie/PitchPrism/releases/download/v1.1.0/still-3d-tactics.jpg)

**Cinematic tactical video · Interactive studio · Evidence you can inspect · Microsoft Azure integrations**

</div>

## Overview

A scoreline tells you what happened. PitchPrism helps you read the passing option, the defender in the lane and the space around the ball. Move from the broadcast into a tactical view, explore an explanation, and return to the same moment in the match.

The featured experience pairs a **118.4-second English tactical film** with a browser-based player and Tactical Studio. It runs without an account or cloud credentials. A Python API also provides an independent synthetic football scenario, personalized explanations and optional Microsoft cloud adapters.

[What makes PitchPrism different](#what-makes-pitchprism-different) · [Visual showcase](#visual-showcase) · [Competition requirements](#competition-requirements-and-evidence) · [Features](#features) · [Quick start](#quick-start) · [Microsoft integrations](#microsoft-integrations) · [Architecture](#architecture) · [Development](#development) · [Contributing](#contributing)

## What makes PitchPrism different

**The explanation becomes part of the viewing experience.** PitchPrism connects a cinematic football film, an interactive tactical reading and inspectable evidence through the same source clock.

- **From broadcast to 3D, without losing the moment.** Three tactical freezes rise into a perspective pitch view, reveal the options and return to the action. Nine reading steps, role highlights, arrows and replay are burned into the downloadable film.
- **One tactical script, two ways to explore it.** The film and browser studio use the same reviewed readings, role focus and option indices. Viewers can pause, toggle explanatory layers and jump to the matching step.
- **Time-aware explanations.** Source time and enhanced-video time remain aligned through freezes and replay. Current-context readings exclude future evidence, including after rewinding.
- **Graphics checked against their evidence.** Reviewed foot anchors and approximate pitch geometry constrain option arrows, covered lanes and editorial zones. Automated checks reject inconsistent configurations and audit text bounds and collisions.
- **Personalization backed by an event trail.** The independent synthetic scenario provides casual/analyst explanations and club/player preferences, with deterministic statistics and cited event IDs. The real-footage experience adds viewing layouts, familiarity settings and visible-role focus.
- **A bounded Microsoft AI workflow.** The implemented Foundry agent reads state, inspects evidence and validates its story. Optional moderation, private receipts, secret resolution and metrics extend the same server pipeline.

Together, these choices connect visual storytelling, interaction and evidence in a reproducible viewing experience. [Explore the architecture](docs/football/ARCHITECTURE.md) · [Inspect the validation](docs/football/VALIDATION.md).

## Visual showcase

### 01 · A broadcast identity made for the pitch

![PitchPrism opening identity and film artwork](https://github.com/imhaojie/PitchPrism/releases/download/v1.1.0/thumbnail.jpg)

A consistent visual language joins the opening, tactical sequences and replay: spectrum accents, bold display typography and restrained English captions.

### 02 · Read the action inside the broadcast

![PitchPrism broadcast overlay with English tactical labels and highlights](https://github.com/imhaojie/PitchPrism/releases/download/v1.1.0/still-broadcast-overlay.jpg)

Role highlights and option arrows direct attention to the reviewed moment. Explanatory graphics remain labelled interpretations of the supplied footage.

### 03 · Step into the tactical view

![PitchPrism perspective 3D tactical view with role markers and explanatory routes](https://github.com/imhaojie/PitchPrism/releases/download/v1.1.0/still-3d-tactics.jpg)

Perspective camera movement, anonymous team figures, light columns and route graphics give each freeze a clear spatial reading. All nine steps share the film's source/output timing.

### 04 · Make the reading your own

![PitchPrism interactive Tactical Studio with source evidence and pitch diagram](https://github.com/imhaojie/PitchPrism/releases/download/v1.1.0/tactical-studio-web.png)

Compare the source frame with the pitch diagram, switch layers and seek directly to a reading. The film and studio preserve the same tactical story.

[**Watch the complete 118.4-second film**](https://vimeo.com/1239357832) · [**Open the interactive demo**](https://imhaojie.github.io/PitchPrism/)

## Competition requirements and evidence

Prepared for **Inside the Game: Developer Hackathon**. The implementation and submitted materials address the challenge through the following concrete deliverables. This table maps requirements to evidence; it does not replace organizer eligibility or acceptance decisions.

| Requirement | PitchPrism implementation or submitted evidence |
| --- | --- |
| **Ingest synthetic football events** | Original Northbridge / Riverside passes, shots, tackles, recoveries and pressure events in [the synthetic fixture](product/football/data/match.json). |
| **Interpret match state and statistics** | Time-bounded snapshots, pass distance, pass accuracy, goals and scenario shot xG in [the analytics engine](product/football/analytics.py). |
| **Explain why a moment matters** | Evidence-linked local explanations and the implemented Foundry read → inspect → validate tool loop; [Microsoft verification scope](docs/football/AZURE-VERIFICATION.md). |
| **Render insights alongside the match** | Released tactical film, synchronized player overlays and interactive Tactical Studio. The featured film uses separately reviewed real footage; synthetic statistics never describe that footage. |
| **Personalize the experience** | Casual/analyst and club/player parameters in the synthetic API; viewing layout, familiarity and visible-role focus in the film player. |
| **English project pitch and Microsoft technology description** | Saved on [the competition project](https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/127054), with seven implemented Microsoft connections. |
| **Public demonstration video under two minutes** | [Vimeo demo](https://vimeo.com/1239357832), 118.4 seconds, English explanatory captions, 1080p. |
| **Public GitHub source and reproducible application** | This repository, [quick start](#quick-start), synthetic API examples and [589 passing offline tests](docs/football/VALIDATION.md). |
| **Source permissions and new-work eligibility** | The owner reports confirmation of footage permissions and organizer eligibility confirmation; attribution and code licenses are preserved in [the notices](THIRD_PARTY_NOTICES.md). |

The public demo runs local editorial explanations. Live Microsoft verification covers **Entra authentication and Content Safety F0 analysis**; generative Foundry inference and the other cloud services have the documented separate status. Optional examples in the rules, such as optical tracking, measured speed and auto-eventing, are not represented as implemented features.

[Official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md) · [Submission materials](docs/football/SUBMISSION.md) · [Per-service verification](docs/football/AZURE-VERIFICATION.md)

## Features

| Feature | Experience |
| --- | --- |
| **Tactics in the film** | Three 3D tactical sequences, nine English reading steps, option arrows, role highlights, space/pressure zones and half-speed replay. 1080p at 25 fps. |
| **Interactive Tactical Studio** | Compare reviewed source frames and a pitch diagram. Toggle routes, focus areas and labels, then jump to the matching reading step. |
| **Synchronized playback** | Six chapters and source/enhanced switching share a source clock, including freezes and replay. |
| **Personal viewing** | Immersive, full-pitch and half-pitch layouts; football familiarity and role focus; an animated football companion. |
| **Explainable intelligence** | Evidence-linked editorial readings, time-bounded synthetic analytics and a Foundry read → inspect → validate agent. |
| **Microsoft platform integration** | Seven implemented service/authentication connections, with opt-in execution and server-side configuration. |



## Quick start

**Requirements:** Python 3.11+ and Git. The local player and API use Python's standard library; the frontend needs no build step.

```bash
git clone https://github.com/imhaojie/PitchPrism.git
cd PitchPrism
python3 -m venv .venv
source .venv/bin/activate
python product/football/scripts/fetch_media.py
python -m product.football.server --port 4180
```

Open **http://127.0.0.1:4180/**. On Windows, activate the environment with `.venv\Scripts\activate`. The media downloader verifies released files against committed SHA-256 values.

1. Play the enhanced film and try the chapter buttons.
2. Open **Tactical Studio** to explore all three moments and nine reading steps.
3. Toggle explanatory layers and compare source/enhanced playback.
4. Adjust viewing preferences and inspect the evidence behind an explanation.

**Keyboard:** Space — play/pause; F — fullscreen; Esc — close panels. Chapter labels use source time; the player shows enhanced-video time.

### Explore the synthetic API

The original Northbridge × Riverside scenario is fictional and separate from the broadcast film. With the local server running:

```bash
# State and statistics from events played up to scenario second 20.
curl 'http://127.0.0.1:4180/api/snapshot?t=20'

# A personalized local explanation; no cloud call or credentials required.
curl 'http://127.0.0.1:4180/api/explain' \
  -H 'Content-Type: application/json' \
  -d '{"second":20,"mode":"analyst","team":"NBR","player":"NBR-10","provider":"local"}'

# An explicitly scoped recap of the synthetic excerpt.
curl 'http://127.0.0.1:4180/api/recap'
```

## Microsoft integrations

| Connection | Purpose |
| --- | --- |
| **Microsoft Foundry / Azure OpenAI** | Generate grounded explanations through a bounded tool loop. |
| **Azure AI Content Safety** | Check generated text before returning an enabled cloud answer. |
| **Azure Blob Storage** | Store minimized operational receipts in a private container. |
| **Azure Key Vault** | Resolve an explicitly named server secret when configured. |
| **Application Insights** | Record minimal explanation metrics without prompts or prose. |
| **Azure Container Apps** | Host the HTTPS API and player with Consumption scaling. |
| **Microsoft Entra ID** | Authenticate through local CLI identity or hosted managed identity. |

A **real Content Safety F0 check and Entra authentication passed** on an existing English tactical caption. The public Pages demo uses **local editorial explanations**. Generative Foundry inference, hosted managed identity and the other cloud services have separate verification scopes; implementation does not imply every service is deployed.

[Integration overview](https://imhaojie.github.io/PitchPrism/azure.html) · [Configuration guide](infra/azure/README.md) · [Per-service verification](docs/football/AZURE-VERIFICATION.md)

To configure cloud adapters, install `product/football/requirements.txt` and copy [.env.example](.env.example) to an ignored `.env`. Supporting adapters default to off. Credentials stay on the server. The deployment helper accepts only eligible student/trial subscriptions with spending protection; it does not upgrade billing plans.

## Architecture

The native JavaScript frontend shares layout, playback, controls and source/output time mapping. The Python backend serves reviewed clip evidence, synthetic analytics and optional cloud adapters. The renderer produces the released film from the reviewed tactical script and approximate pitch geometry.

| Directory | Responsibility |
| --- | --- |
| [`product/football/watch/`](product/football/watch/) | Active web application, Tactical Studio, companion and integration overview |
| [`product/football/data/`](product/football/data/) | Media-bound observations, tactical script and independent synthetic fixture |
| [`product/football/scripts/`](product/football/scripts/) | Media fetching, rendering, export and explicit cloud verification tools |
| [`product/football/tests/`](product/football/tests/) | Football behavior, evidence, media and Azure adapter tests |
| [`product/watch/`](product/watch/) | Shared player, layout, UI and time-mapping modules |
| [`product/broadcast-fx/`](product/broadcast-fx/) | Reusable rendering primitives |
| [`infra/azure/`](infra/azure/) | Guarded deployment tooling and modular Bicep templates |
| [`docs/`](docs/) | Architecture, media, validation and contributor documentation |

Historical modules remain available for provenance and regression; `product/football/` is the active application. Media, generated bundles, credentials and account receipts stay outside Git. Versioned media is distributed through GitHub Releases.

### Data and interpretation

The film uses a supplied 66.6-second Manchester City × Newcastle excerpt. Selected foot anchors and observations were manually reviewed. Pitch positions, arrows and zones are editorial schematics derived from approximate single-frame geometry. They do not represent continuous tracking, confirmed passes or calibrated pressure measurements.

The visible 0–0 scoreboard applies only to the excerpt. Official events, xG, full-match statistics and unverified player identities remain unavailable. The synthetic fixture supplies its own fictional events and shot xG inputs and is never joined to the real footage. Current-context explanations exclude future events; full recaps are explicit.

## Development

Use **Node.js 22+** for the complete engineering gate:

```bash
npm ci --prefix product --ignore-scripts
python product/scripts/check.py --full
```

The current gate passes **589 behavioral tests with no skips**, source/privacy and syntax checks, plus 50 preserved offline infrastructure assertions. All Azure Bicep templates compile. Browser playback, full media decode and live cloud checks have separate evidence in the [validation guide](docs/football/VALIDATION.md).

To preview the static export:

```bash
python product/football/scripts/export_demo.py
python product/football/scripts/serve_demo.py --port 4181
```

Open **http://127.0.0.1:4181/site/**. Export verifies media hashes and the shared timeline before publishing the same local editorial experience as GitHub Pages.

## Documentation

- [Demo walkthrough](docs/football/JUDGING.md)
- [Architecture](docs/football/ARCHITECTURE.md)
- [Media pipeline](docs/football/MEDIA.md)
- [Validation](docs/football/VALIDATION.md)
- [Microsoft platform verification](docs/football/AZURE-VERIFICATION.md)
- [Changelog](CHANGELOG.md)

## Contributing

Bug reports and focused pull requests are welcome. Read the [contribution guide](CONTRIBUTING.md), use the [issue templates](.github/ISSUE_TEMPLATE/), and run the offline gate before requesting review. Report vulnerabilities through the [security policy](SECURITY.md).

## License and acknowledgments

Code is released under the [MIT License](LICENSE). Fonts, third-party software and source attribution are documented in [Third-party notices](THIRD_PARTY_NOTICES.md) and [source provenance](docs/football/MIGRATION.md). Broadcast footage, audio and third-party marks retain their owners' rights and are not covered by the code's MIT license.
