# Competition submission notes

Software publication and competition submission are separate. The repository does not claim that release publication establishes eligibility or that Azure adapter tests prove live deployment.

Before submitting to Inside the Game, resolve:

- Retain organizer confirmation of new-work eligibility, including disclosure of prior open-source code and its separate award history. See [source provenance](MIGRATION.md).
- Retain permission for the underlying broadcast footage, audio and third-party marks. Code licensing does not supply these rights.
- A successful real Azure/Foundry run with validated evidence/tool trace if claimed in the entry. The public demo is local editorial mode.
- An English video strictly under two minutes on an officially supported public video platform. A GitHub Release MP4 is a download, not that platform URL.

## Status — v1.1.0 (2026-10-26)

- Demo video: the v1.1.0 movie, 118.4 s, English, 1920×1080. The submission kit (video, thumbnail, stills, platform metadata and project text) is generated outside Git under `product/football/build/submission/v1.1.0/`.
- Accepted video platforms per the rules: YouTube, Vimeo, Facebook Video or Youku. The previous YouTube upload of v1.0.0 was blocked worldwide by an FA Premier League visual claim. The owner reports confirmation of footage permission and organizer confirmation of new-work eligibility; supporting records are retained privately and have not been independently reviewed. The earlier YouTube block remains separate from the selected v1.1.0 video, now public on Vimeo as linked below.
- Deadline per the rules: 27 October 2026, 11:59 pm Pacific Time.

## Integration-only update — 26 October 2026

The selected English v1.1.0 video is now public on [Vimeo](https://vimeo.com/1239357832), and its link is saved at the top of the competition project description. Public-page 1080p playback was checked at publication. The selected film and its bytes remain unchanged.

Microsoft Foundry, Content Safety, Blob Storage, Key Vault, Application Insights, Container Apps and Entra ID have implemented adapter/configuration paths. Supporting adapters are opt-in and disabled by default. A minimal live Microsoft AI check successfully authenticated through Entra ID and analyzed one existing English caption using Content Safety F0. Foundry generative inference remains separate and unverified after an account eligibility restriction at deployment preflight. See [per-service verification](AZURE-VERIFICATION.md) and the [integration guide](../../infra/azure/README.md). Competition acceptance is determined by the organizer.

Consult the [official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md) and organizer confirmation for the actual submission. No entry is submitted automatically by the repository workflows.

## Submitted project materials

- [Competition project](https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon/project/127054): English title, tagline, description, challenge selection, public repository and video links.
- [Public Vimeo video](https://vimeo.com/1239357832): selected v1.1.0 film, 118.4 seconds, 1080p, English explanatory text.
- [Public source](https://github.com/imhaojie/PitchPrism) and [versioned movie release](https://github.com/imhaojie/PitchPrism/releases/tag/v1.1.0).
- [Interactive demo](https://imhaojie.github.io/PitchPrism/) and [Microsoft integration overview](https://imhaojie.github.io/PitchPrism/azure.html).
- [Install and reproduce](../../README.md#quick-start), including the independent synthetic event API.

Section 4 of the official rules defines entering the required Projects-page fields as the submission process. The project UI exposes Save for individual sections; its management menu contains Change log, Clone project and Delete project. No separate final-submit control was visible during the review. The gallery upload controls were disabled, so public release images can be embedded in the Markdown description. Saving the page is not an organizer acceptance decision.

The mandatory synthetic-data requirement is supported by the independent original fixture, time-bounded state/statistics, personalized explanation API and explicit excerpt recap. The featured film uses separately reviewed real footage. The two data sources must remain separate. Optional examples in the rules, such as optical auto-eventing and speed tracking, are not implemented claims.
