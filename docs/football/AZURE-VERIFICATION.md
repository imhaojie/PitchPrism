# Microsoft platform verification

PitchPrism implements seven Microsoft platform connections. The featured v1.1.0 tactical film and interactive demo remain unchanged. Implementation, offline validation and live operation are recorded separately.

| Connection | Implemented | Verification in this update |
| --- | --- | --- |
| Microsoft Foundry / Azure OpenAI | Bounded read → inspect → validate agent | Offline protocol tests; generative cloud run not verified |
| Azure AI Content Safety | Optional generated-text analysis | **Actual F0 text analysis passed**, 26 October 2026 |
| Azure Blob Storage | Private minimized JSON receipts | Offline transport and privacy tests; live storage not run |
| Azure Key Vault | Named server-secret resolution | Offline identity/secret tests; live secret retrieval not run |
| Application Insights | Minimized explanation metrics | Offline transport/acceptance tests; live ingestion not run |
| Azure Container Apps | HTTPS Consumption deployment template | Bicep compilation; hosting not deployed |
| Microsoft Entra ID | CLI and managed identity authentication | **Actual CLI identity authentication succeeded** for the Content Safety call; hosted managed identity not run |

## Minimal live Microsoft AI check

The Content Safety adapter sent the first English reading step from `data/tactical-story.json`, build scene, to Azure AI Content Safety. The API returned category analysis, and the adapter's severity/completeness checks passed.

- Verified at: 26 October 2026, 03:53:23 UTC.
- Tier: **F0 / Free**; key-based local authentication disabled.
- Authentication: Microsoft Entra ID through the locally authenticated Azure CLI identity.
- Text SHA-256: `bf670fcb30eca802e98cf1025037a403dc04140253ce9c2b3670ae1d5666637d`.
- Category severities: Hate 0; SelfHarm 0; Sexual 0; Violence 1.
- Blocking threshold in this adapter: any category at severity 4 or above, or missing/invalid analysis.
- Scope: one existing caption. This does not verify generation of match explanations by Foundry or moderation of the full video.

Reproduce explicitly after configuring an eligible F0 resource and identity:

```bash
python product/football/scripts/verify_content_safety.py --run
```

Without `--run`, the script sends no request. The private receipt is written to ignored `artifacts/content-safety-live.json` with owner-only permissions. No account IDs, endpoint or credentials are published here.

## Credit and deployment scope

The enabled student subscription showed US$100 available credit, zero displayed current cost and spending limit On during preflight. Azure OpenAI deployment validation returned `CannotDeployDueToLocalRegulations`; the account was not eligible for that deployment. No successful generative model deployment or inference is claimed. Supporting services other than Content Safety were not deployed. No paid upgrade or AWS change was made.

The code passes 589 offline behavioral tests with no skips, including 14 adapter tests. All Azure templates compile. These checks verify contracts and configuration, not the unexecuted cloud services. See [integration configuration](../../infra/azure/README.md) and [overall validation](VALIDATION.md).
