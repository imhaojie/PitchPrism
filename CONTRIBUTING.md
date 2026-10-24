# Contributing to PitchPrism

Start with the [quick start](README.md#quick-start) and [architecture](docs/football/ARCHITECTURE.md). Open an issue for a bug or a proposed feature; keep pull requests focused on a concrete user outcome.

## Development

Python 3.11+ runs the server. Node.js 22+ runs JavaScript checks and the complete regression gate. Install the locked tooling with `npm ci --prefix product --ignore-scripts`.

```bash
python product/scripts/check.py --full
```

Add behavior tests when changing time mapping, evidence boundaries, request validation or other consequential logic. For interface changes, check actual playback, keyboard use, desktop and narrow-screen layouts. For media changes, also perform full video/audio decode and verify duration, dimensions and frame count; passing offline tests alone does not verify media.

## Evidence and media contracts

- Keep the supplied real clip separate from `product/football/data/match.json`, the synthetic test fixture.
- Do not invent identities, official events, xG or full-match statistics. Respect source time when selecting observations, including after seeking backwards.
- Manually reviewed foot anchors belong to specific stills. Board positions and option arrows remain editorial schematics.
- Publish a new media release whenever video bytes or its source/output mapping change. Update the lock and manifest together; follow the [media guide](docs/football/MEDIA.md).
- Keep keys, `.env`, generated media, build outputs, screenshots used only for QA and account receipts out of commits.
- Preserve license and third-party notices. Archived infrastructure is retained for regression and is not a default deployment target.

Use `codex/` for agent-created branches. Explain the problem, resulting behavior and relevant validation in the pull request. Run the full gate before requesting review. Documentation links should be relative.

The public demo is local editorial mode. Do not describe fake transport tests as cloud inference or deploy resources as part of routine contribution checks.
