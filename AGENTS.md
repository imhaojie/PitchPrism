# PitchPrism repository guidance

Read README.md, docs/football/MIGRATION.md and AI接手说明.md first.

- Product: **PitchPrism**. Description: **An AI-powered football companion that turns match data into visual stories and personalized insights.**
- Active runtime: `product/football/`. Reuse shared modules under `product/watch/`. Basketball/AWS code is preserved for provenance and regression, not the default application.
- Keep the original GameBuddy repository unchanged. Its award is not a PitchPrism award. Preserve license and source attribution.
- All football data, xG inputs and footage are explicitly synthetic. Never call them official data or optical tracking. Keep excerpt scope and missing values; do not invent speed, possession, offside or tactical causality.
- Source time and enhanced output time differ. Future events cannot support a live insight. Explicit full recaps are labelled.
- Local templates and cloud results are separate. Fake transport tests and Bicep compilation do not prove real Azure deployment/inference. A real Foundry receipt requires successful API output and validated tool trace.
- Keep credentials, generated media, build outputs and account receipts out of Git. Serve only explicit paths; preserve video Range support.
- Run `python3 product/scripts/check.py --full`. Browser QA, media decode, Bicep and cloud verification are separate.
- User chose free Azure trial. Never upgrade to pay-as-you-go or accept paid offers. Before deploying, verify the user's explicit subscription, trial credit and model quota. No AWS resource changes are authorized.
- New-work eligibility requires organizer confirmation. Submission video must be English and under two minutes, with a public supported video-platform URL separate from a GitHub release.
- Use relative documentation links. Historical guidance: GAMEBUDDY-AGENTS.md.
