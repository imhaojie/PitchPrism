# Source provenance

PitchPrism retains MIT-licensed interface modules and rendering primitives from [GameBuddy](https://github.com/imhaojie/BroadcastCode-2026), snapshot `17d74fd2a5df64a240198a7305312174de7684b0`. The original repository is unchanged. Its NBA × AWS award belongs to that project, not PitchPrism. Copyright and third-party notices are preserved in the [license](../../LICENSE) and [notices](../../THIRD_PARTY_NOTICES.md).

The active product is `product/football/`. Shared layout, controls, glass surfaces, drawers, pitch-panel structure and source/output mapping live under `product/watch/`; reusable Python/OpenCV/Pillow/FFmpeg primitives live under `product/broadcast-fx/`. The football companion, Tactical Studio, reviewed football observations, English editorial readings, Azure context and release/media tooling are PitchPrism additions.

Historical basketball and AWS modules remain for attribution, provenance and regression. They are not PitchPrism's default application or deployment target. The active runtime has no AWS service dependency. Historical documents are indexed under [the provenance archive](../archive/provenance/INDEX.md).

## Current release

The published player and 118.4-second reviewed MP4 share one source/output timeline. Three 13.2-second freezes contain nine reading steps, option arrows and role highlights. The interactive studio uses the same roles and option indices. The reviewed video bytes are preserved exactly when packaging; source observations and anchors are unchanged. Render-input and published player-data hashes are recorded separately.

Foot anchors are manually reviewed points in selected source frames; board coordinates and dashed options remain editorial schematics. The independent synthetic fixture is never joined to the supplied real footage. See [architecture](ARCHITECTURE.md), [media](MEDIA.md) and [validation](VALIDATION.md).

The public demo uses local editorial explanations. Live Azure deployment/inference, new-work eligibility and broadcast rights are separate claims; see [submission notes](SUBMISSION.md).
