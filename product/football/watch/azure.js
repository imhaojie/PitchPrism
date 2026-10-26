import { api } from './transport.js';
const label = document.getElementById('runtime-status');
try {
  const health = await api('/api/health');
  const active = Object.values(health.azureServices || {}).filter(service => service.enabled).length;
  label.textContent = health.staticDemo ? 'This public static demo runs locally authored editorial explanations. Cloud adapters are not executed here.' :
    `${health.foundryConfigured ? 'Foundry credentials configured' : 'Local editorial runtime'} · ${active} supporting adapters enabled. Per-service verification is documented in the integration guide.`;
} catch {
  label.textContent = 'Runtime configuration is unavailable. This page describes implemented adapters; it does not certify cloud operation.';
}
