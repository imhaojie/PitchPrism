# Azure / Foundry setup

The user chose a **free trial**, not automatic pay-as-you-go. Identity/card checks require the account owner. Azure CLI is installed; first login found no subscriptions. No resource was created.

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

This creates a Foundry resource/project/model, assigns the user Cognitive Services OpenAI User and writes an ignored keyless `.env` without overwriting existing config. RBAC propagation may take time. A real verification receipt is written only after successful inference and validation.

For a public dynamic app, build the Dockerfile and pass a pullable public image:

```bash
.venv/bin/python infra/azure/deploy.py --subscription YOUR_SUBSCRIPTION_ID --image YOUR_PUBLIC_IMAGE --apply
```

The image includes only active/shared modules, generates the footage and runs as a non-root user. Local Docker daemon was unavailable, so no local image build is claimed. Optional Bicep resources use Container Apps Consumption, HTTPS, managed identity, 0–1 replicas, 0.25 vCPU/0.5 GiB, no Log Analytics workspace. Fixed media needs no Blob/queue/training service.

```bash
az bicep build --file infra/azure/main.bicep --outfile /tmp/pitchprism-azure.json
```

Compilation checks syntax/types, not quota, permissions or deployed operation. The free Pages LOCAL demo stays available while Azure remains unconfigured.
