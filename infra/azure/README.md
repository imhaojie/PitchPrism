# Azure / Foundry setup

The user selected **Azure for Students with a personal Microsoft account and university email for academic verification** on 2026-10-22; no pay-as-you-go upgrade is authorized. Student eligibility, identity checks and final account terms require the account owner. A subscription and actual model quota must be confirmed before deployment. No successful live inference is claimed yet.

## Integration-only configuration

The reviewed v1.1.0 film and Tactical Studio remain the featured demonstration. Seven Microsoft platform connections are implemented; they are not presented as seven deployed or verified services.

| Service | Implemented application path | Default |
| --- | --- | --- |
| Microsoft Foundry / Azure OpenAI | Bounded read-state, inspect-evidence and validate-story tool loop | Requires endpoint, deployment and identity |
| Azure AI Content Safety | Analyze generated English headline and explanation before returning a cloud answer; fail closed on unavailable/incomplete analysis or severity 4+ | Off |
| Azure Blob Storage | Write a minimized operational JSON receipt to a private container | Off |
| Azure Key Vault | Resolve one explicitly named Foundry key at startup as an optional alternative to keyless auth | Off |
| Application Insights | Send a validated-explanation metric and audience mode, without prose or viewer identity | Off |
| Azure Container Apps | HTTPS, non-root Python runtime, Consumption profile and 0–1 replicas | Template only |
| Microsoft Entra ID | Azure CLI identity locally and managed identity in hosting; resource-scoped model, safety and blob roles | Used only by explicitly enabled calls |

Copy the optional settings in the root [environment example](../../.env.example) to an ignored `.env`. `PITCHPRISM_ENABLE_CONTENT_SAFETY`, `PITCHPRISM_ENABLE_BLOB_RECEIPTS` and `PITCHPRISM_ENABLE_TELEMETRY` must each be `1` to execute their adapters. Setting a flag alone does not provision a resource or establish that it works. `/api/health` reports adapter configuration with `verified: false`; only actual successful results report execution outcomes.

Content Safety is in the answer path when enabled. Storage and monitoring failures are returned as separate adapter statuses and do not suppress a validated answer. Neither operational adapter receives footage, model prompts or explanation prose. Blob receipts include only time, provider, audience, token count, source time, evidence IDs and tool names/statuses. Keep the container private. The optional template expires receipts after 30 days; blob soft deletion can retain deleted objects for another seven days.

`AZURE_OPENAI_API_KEY_SECRET` enables Key Vault lookup at startup. Set `AZURE_KEY_VAULT_ENDPOINT` and grant the runtime identity access to that specific secret through your normal access review. The template deliberately creates no secret and grants no automatic secret-reading access. Prefer managed identity directly for Foundry where supported.

`--support-services` includes the optional [supporting service module](services.bicep). It is off by default. The module uses Content Safety F0, private Standard LRS storage, a Key Vault and workspace-based Application Insights with 30-day retention and a 0.1 GB daily workspace ingestion setting. These settings are not a monetary spending cap or a guarantee of free use; use only an eligible credit subscription with spending protection. Service/region availability and quota must be checked separately. The combined module was not deployed in this update; a standalone Content Safety F0 resource was used for the minimal verification below.

## Verification status — 26 October 2026

An enabled Azure for Students subscription, US$100 available credit, zero current displayed cost and spending limit **On** were checked. The subscription's allowed region policy and model catalog/quota were inspected. An Azure OpenAI deployment attempt was rejected during provider preflight by `CannotDeployDueToLocalRegulations`; no successful model deployment or inference resulted. Account-specific records stay private and outside Git.

The featured delivery keeps the selected film and demo, with seven implemented Microsoft platform connections. A minimal live check successfully authenticated through Microsoft Entra ID and analyzed one existing English tactical caption using **Azure AI Content Safety F0**. The returned severities were Hate 0, SelfHarm 0, Sexual 0 and Violence 1, below the adapter's blocking threshold. This is a real Content Safety check, separate from generative Foundry inference. See [verification scope](../../docs/football/AZURE-VERIFICATION.md).

Offline adapter tests and Bicep compilation verify code contracts and template syntax. Blob, Key Vault, Application Insights and Container Apps were not deployed for this update. No paid subscription upgrade or paid service tier was accepted. The Content Safety resource uses F0; the student subscription spending limit remains on.

[Azure for Students](https://azure.microsoft.com/free/students/) offers eligible students $100 credit for 12 months without a credit card. School email verification is separate from Microsoft account sign-in; confirm both identities in the registration UI.

Eligible new customers can receive $200 credit for 30 days. Trial availability, model access and regional quota vary; a trial does not guarantee the chosen model. Never upgrade or accept paid offers automatically. Check remaining credit before deployment. Budget alerts and the app's in-memory call limit are not spending caps.

References: [free account](https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account), [Container Apps grants](https://learn.microsoft.com/en-us/azure/container-apps/billing), [model deployment](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/how-to/create-model-deployments), [OpenAI v1](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle).

```bash
az login --use-device-code
az account list --all --output table
python3 -m venv .venv
.venv/bin/pip install -r product/football/requirements.txt
# Read-only target/model availability plan:
.venv/bin/python infra/azure/deploy.py --subscription YOUR_SUBSCRIPTION_ID
```

The helper queries the regional catalog for a GlobalStandard version. It creates no subscription, paid marketplace offer, throughput commitment, GPU, VM, database or training job. Quotas can still reject deployment.

After checking the explicit trial subscription/credit:

```bash
.venv/bin/python infra/azure/deploy.py --subscription YOUR_SUBSCRIPTION_ID --apply
.venv/bin/python product/football/scripts/verify_foundry.py
.venv/bin/python -m product.football.server --port 4180
```

The apply path rejects paid offers or subscriptions without the spending limit set to On. GlobalStandard capacity 10 is an on-demand rate quota, not provisioned throughput. This creates a Foundry resource/project/model, assigns the user Cognitive Services OpenAI User and writes an ignored keyless `.env` without overwriting existing config. RBAC propagation may take time. A real verification receipt is written only after successful inference and read/inspect/validate tool steps. The default verification now uses the active real clip at source 37.8s; `--scenario synthetic` explicitly tests the separate fictional fixture. Receipts include source/data SHA-256 and are saved with owner-only permissions.

For a public dynamic app, build the Dockerfile and pass a pullable public image:

```bash
.venv/bin/python infra/azure/deploy.py --subscription YOUR_SUBSCRIPTION_ID --image YOUR_PUBLIC_IMAGE --apply
```

The image includes only active/shared modules, fetches the hash-verified frozen demo media and runs as a non-root user. The public GitHub Actions build succeeded for commit `635fd0f`, and its GHCR manifest was anonymously reachable. The image reference is `ghcr.io/imhaojie/pitchprism:635fd0f12e85382b3192d2df7cc8f2c03ad91df8` (verify the current commit tag before use). Optional Bicep resources use Container Apps Consumption, HTTPS, managed identity, 0–1 replicas, 0.25 vCPU/0.5 GiB, no Log Analytics workspace. Fixed media needs no Blob/queue/training service.

```bash
az bicep build --file infra/azure/main.bicep --outfile /tmp/pitchprism-azure.json
```

Compilation checks syntax/types, not quota, permissions or deployed operation. The free Pages LOCAL demo stays available while Azure remains unconfigured.
