# Azure / Foundry setup

The user selected **Azure for Students with a personal Microsoft account and university email for academic verification** on 2026-10-22; no pay-as-you-go upgrade is authorized. Student eligibility, identity checks and final account terms require the account owner. A subscription and actual model quota must be confirmed before deployment. No successful live inference is claimed yet.

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
