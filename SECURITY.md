# Security

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** flow when available. If private reporting is unavailable, open an issue requesting a private reporting channel without publishing exploit details, credentials or personal data.

Include the affected version, a minimal reproduction and the security impact. Do not include model keys, subscription details, private match footage or account receipts.

## Deployment boundaries

Keep Azure credentials on the server. The static demo has no model credentials and makes no cloud model calls. The local server binds to loopback by default, serves explicit application/media paths and supports byte-range video requests. Public server deployments need their own authentication, traffic limits and operational review.

Use the latest published release. This project does not promise maintenance of older preview versions.
