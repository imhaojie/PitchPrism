# Validation record — 2026-10-20

## Verified locally

- Original GameBuddy checkout: `git status --short` remains empty; no original file or Git metadata was changed.
- Football data: 22 fictional players, 19 ordered events, 48-second excerpt; generator output matches the checked-in fixture.
- New behavior suite: 32 tests pass, covering formulas, missing data, exact goal boundary, replay/rewind, preferences, source references, tool ordering/repair/budgets, HTTP allowlists, origin check and Range delivery.
- Full inherited gate plus football: **546 behavioral tests, no skips**, with external network blocked; syntax/privacy checks and 50 legacy CDK resource assertions pass. Legacy infrastructure results do not certify Azure.
- MP4: 48-second source and 64-second enhanced cut, 960 × 540, 24 fps, silent stereo track; both fully decoded through FFmpeg. Local `build/manifest.json` records SHA-256 identities and source/output mapping. No model was used to render them.
- Desktop 1440 × 1000 and mobile 390 × 844: visible playback, tactical map and focus tested; no horizontal overflow. Initial tactical canvas sizing bug fixed.
- Free static export: same UI at a nested `/site/` path, backed by 20 materialized Python event states and 2,760 audience/team/player combinations. Source/enhanced seeking requires HTTP Range support and passed with the production delivery implementation.
- Azure Bicep compiles successfully into ARM JSON using Bicep 0.48.1. This confirms syntax/type compilation, not deployed operation.

## Not yet verified

- Real Foundry inference: first Azure login found no subscriptions. User selected free-trial signup. No endpoint, model deployment or successful request trace exists yet.
- Azure resource deployment, managed identity at runtime, model quota/availability and public dynamic app: pending trial activation and explicit target verification.
- Local Docker build: daemon was not running. Dockerfile is provided; no built-image claim.
- Hackathon new-work eligibility: disclosed reuse needs organizer confirmation.
- Public video-platform submission URL: separate from a GitHub release MP4; user-account upload is still required if no connected video publisher is available.

Model transport doubles in unit tests validate protocol behavior only. LOCAL templates, media rendering and static demo success are never counted as real model calls.
