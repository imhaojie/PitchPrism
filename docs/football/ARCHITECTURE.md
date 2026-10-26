# Architecture

PitchPrism has two delivery modes with the same viewing interface:

| Mode | State and explanations | Media |
| --- | --- | --- |
| Local Python server | Source-time API snapshots; local editorial stories; optional configured Foundry calls | Hash-locked MP4 files with HTTP Range support |
| Static GitHub Pages | Six materialized observation states and 48 local story variants | The same released MP4 files |

The frontend uses native JavaScript modules. Shared stage, controls, glass surfaces, drawers and source/output mapping live under `product/watch/`; football-specific presentation lives under `product/football/watch/`.

## Evidence and clocks

`data/clip.json` binds reviewed observations to the original source SHA-256. Its `production.timeline` defines the enhanced movie's independent clock. Live sections advance source time, freezes hold it, rewind moves backwards and replay advances at half speed. `editorial-timeline.js` resolves chapter and reading-step jumps to their presentation times. The player derives evidence from source time, so seeking backwards removes later observations.

`data/tactical-story.json` contains the English burned-in readings. The web studio's localized readings use the same focus roles and option indices, enforced by tests. Foot anchors are reviewed image pixels; pitch coordinates are editorial schematic positions. Neither is a continuous tracking feed.

`data/match.json` is a separate synthetic analytics fixture. Its events and metrics never support stories about the real footage.

## Explanations

`clip.py` creates bounded snapshots and local editorial stories. `foundry.py` implements a separate Azure transport and validated tool loop: read match state, inspect evidence, validate the story. Provider labels reflect the actual result. Configured credentials alone do not prove inference succeeded.

`azure_services.py` adds opt-in Content Safety text analysis, private Blob receipt writes, Key Vault secret resolution and Application Insights metrics. Content Safety gates a cloud answer when enabled; optional operational failures are reported separately. These adapters default to off, acquire credentials only when enabled and keep configuration server-side. Container Apps and Entra identity are configured through the Azure templates. The public [integration overview](../../product/football/watch/azure.html) describes these implemented paths and their unverified cloud status.

## Delivery

`fetch_media.py` verifies all three release assets against `data/media-lock.json` and checks their data binding. `export_demo.py` checks media hashes and exact timeline agreement before exporting. The static demo needs no model key or server API. Source, enhanced video and release manifest are served as explicit media paths; unlisted build files and account receipts are not web assets.
