# Shortest migration path

Created 2026-10-20 in a separate directory from GameBuddy's tracked-file snapshot `17d74fd2a5df64a240198a7305312174de7684b0`. Ignored media, credentials, weights and dependencies were not copied. Original files and Git metadata remain unchanged.

The plain Python/native ESM approach is preserved. `product/football/` is the active adaptation; basketball source remains for provenance/regression. This is not a service-for-service port of every AWS resource.

## Direct reuse

- `watch/media/player-controls.js` and CSS are actually imported. Optional English accessibility was added; existing defaults/tests remain.
- `watch/adapters/catalog.js`: actually imported source/output time mapping and preference persistence. A storage adapter isolates PitchPrism's key.
- `watch/stage/layout.js`: actually imported `fitContain` for pitch geometry. Basketball court geometry is unused.
- The bounded read-tools/validate-tools Agent pattern was adapted to football and Foundry. Basketball prompts and trained Qwen weights are not used.
- FFmpeg encoding, canonical facts, hashes, full decode and independent media/model evidence retain the upstream approach. The small new renderer creates an original synthetic football scene.

| Original role | Active football path |
|---|---|
| AgentCore + Bedrock | Python tool loop + Azure OpenAI v1 / Foundry |
| Lambda API/Worker | One containerized Python app for a fixed pre-rendered scenario |
| S3 + CloudFront | Container Apps HTTPS for dynamic app; Pages for labelled local demo |
| SageMaker training/endpoint | No training; Foundry tools read canonical evidence |
| Queue/workflow/job database | Unneeded for fixed scenario; no inactive Azure facsimiles added |

The synthetic feed is ingested as the source clock advances. Arbitrary uploaded video event extraction, full live broadcast ingestion and retraining are outside this demo. The hourly in-memory model limit resets after process restart; it is not a subscription spending cap.

## Rules and ownership

Newly created projects and synthetic football data are required. Open-source enhancement is permitted, but an already winning submission cannot be resubmitted. Reuse is disclosed; the organizers must decide eligibility. GameBuddy's award does not transfer to PitchPrism.

The new demo uses no real club marks, licensed match feed, broadcast footage or music. DM Sans follows SIL OFL; original code is MIT. Preserved upstream materials retain their notices.
