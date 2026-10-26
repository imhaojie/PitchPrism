# Competition submission notes

Software publication and competition submission are separate. The repository does not claim that release publication establishes eligibility or that Azure adapter tests prove live deployment.

Before submitting to Inside the Game, resolve:

- Retain organizer confirmation of new-work eligibility, including disclosure of prior open-source code and its separate award history. See [source provenance](MIGRATION.md).
- Retain permission for the underlying broadcast footage, audio and third-party marks. Code licensing does not supply these rights.
- A successful real Azure/Foundry run with validated evidence/tool trace if claimed in the entry. The public demo is local editorial mode.
- An English video strictly under two minutes on an officially supported public video platform. A GitHub Release MP4 is a download, not that platform URL.

## Status — v1.1.0 (2026-10-26)

- Demo video: the v1.1.0 movie, 118.4 s, English, 1920×1080. The submission kit (video, thumbnail, stills, platform metadata and project text) is generated outside Git under `product/football/build/submission/v1.1.0/`.
- Accepted video platforms per the rules: YouTube, Vimeo, Facebook Video or Youku. The previous YouTube upload of v1.0.0 was blocked worldwide by an FA Premier League visual claim. The owner reports confirmation of footage permission and organizer confirmation of new-work eligibility; supporting records are retained privately and have not been independently reviewed. The prior platform block has not been resolved, and a working public video-platform URL is still required.
- Deadline per the rules: 27 October 2026, 11:59 pm Pacific Time.

## Integration-only update — 26 October 2026

The selected English v1.1.0 video is now public on [Vimeo](https://vimeo.com/1239357832), and its link is saved at the top of the competition project description. Public-page 1080p playback was checked at publication. The selected film and its bytes remain unchanged.

Microsoft Foundry, Content Safety, Blob Storage, Key Vault, Application Insights, Container Apps and Entra ID have implemented adapter/configuration paths. Supporting adapters are opt-in and disabled by default. A minimal live Microsoft AI check successfully authenticated through Entra ID and analyzed one existing English caption using Content Safety F0. Foundry generative inference remains separate and unverified after an account eligibility restriction at deployment preflight. See [per-service verification](AZURE-VERIFICATION.md) and the [integration guide](../../infra/azure/README.md). Competition acceptance is determined by the organizer.

Consult the [official rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md) and organizer confirmation for the actual submission. No entry is submitted automatically by the repository workflows.
