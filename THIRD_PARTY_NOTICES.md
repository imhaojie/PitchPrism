# Third-party materials and license scope

The root MIT license applies to GameBuddy's original source code and original technical documentation. Third-party materials retain their own licenses and rights. Inclusion, attribution, or an accessible URL does not grant additional redistribution rights.

| Material | Location / source | Scope |
|---|---|---|
| liquidGL 3.0.0 | `product/watch/vendor/liquid-gl/` | Preserve the bundled [MIT license](product/watch/vendor/liquid-gl/LICENSE), attribution and [local patch notes](product/watch/glass/VENDOR_PATCH.md). |
| Fusion Pixel font | `product/web/assets/fonts/` | Distributed under the bundled [SIL Open Font License 1.1](product/web/assets/fonts/OFL.txt). |
| Noto CJK render fonts | Fixed media build tools in `readiness-lab/prepare_build.py` | Font downloads retain the upstream license alongside the font; generated build layers are excluded from Git. |
| FFmpeg / ffprobe | External tools prepared by `readiness-lab/prepare_build.py`; local render environments | Not relicensed by this repository. Observe the licenses of the actual binary builds and enabled components when distributing binaries. |
| NBA statistics and Inside the Game snapshots | `product/data/`, `product/research/`, `product/rl/data/`, and formal event data | Official facts, source responses, and derived metrics retain their provenance. No additional license to NBA data or upstream tracking systems is granted. |
| NBA game footage, frames, and presentation screenshots | Documentation images and local media | Used to explain the competition prototype. Original MP4s are excluded from Git; obtain the necessary rights for your own use or redistribution. |
| NBA, AWS, and team logos | Team asset documentation and architecture figure source manifests | Trademarks belong to their respective owners. Their use describes the competition and integrations, not independent certification or endorsement. |
| Qwen2.5-3B-Instruct | [Upstream model](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) | Model use and adapted weights are subject to the upstream model license. Weights are not bundled in Git. |
| Doubao / MOSS-TTS / Polly speech | Narration scripts and corresponding provider/model references | Generated audio and model access are subject to the applicable provider and model terms. API keys and generated audio remain outside Git. |
| Competition group photograph | `docs/assets/project/hackathon-group.jpg` | Supplied by the team for this project page, preserved unchanged; not covered by the code's MIT license. |
| Additional dependencies | Package lockfiles and pinned requirements | Dependencies retain their own licenses. |

The architecture image is an AI-assisted explanatory figure of the project's implemented capabilities. Tactical overlays are editorial illustrations, not official tracking products. Image sources and media identities are recorded in [the project gallery manifest](docs/assets/project/sources.json), the competition capture manifest, and the architecture figure manifests.


## PitchPrism

The active application uses DM Sans from [Google Fonts](https://github.com/google/fonts/tree/main/ofl/dmsans), under the SIL Open Font License. Its license is included at `product/football/watch/fonts/OFL.txt`. The football companion is an original SVG/CSS component; the active app does not mount the historical basketball sprite. System DIN fonts used for the reviewed video are not redistributed; the renderer falls back to bundled DM Sans where unavailable.

Shared interface modules and rendering primitives retain the MIT-licensed [GameBuddy](https://github.com/imhaojie/BroadcastCode-2026) source attribution, snapshot `17d74fd2a5df64a240198a7305312174de7684b0`. Its separate award history is not a PitchPrism award. The original repository is unchanged. [Source provenance](docs/football/MIGRATION.md).

### Supplied match footage

The demonstration uses the user's `match.mp4` (SHA-256 `cf1ded5ca487eff98505fa64ac2f2f790c04a33ab441d5eccdd785da847ef523`), a Manchester City × Newcastle broadcast excerpt containing broadcaster/competition marks and original audio. Broadcast, club, competition and audio rights remain with their owners. The code's MIT license does not license this footage; no endorsement is implied. Independent redistribution/competition permissions have not been verified. [Source analysis](docs/football/SOURCE-ANALYSIS.md).

The independent synthetic test fixture is original scenario data and does not describe this real broadcast. Playwright is development tooling by Microsoft under Apache-2.0. Sharp is optional development tooling under Apache-2.0, with its own dependency notices. Dependency and source licenses remain applicable.
