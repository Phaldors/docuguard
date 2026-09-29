# Public reviewer demo boundary

The Render deployment is a portfolio demo, not a multi-tenant production
service. It publishes one deterministic, synthetic bundle and deliberately
does not accept arbitrary customer data.

Set these environment variables on the public service:

```text
DOCUGUARD_PUBLIC_DEMO=true
DOCUGUARD_DEMO_REVIEW_TOKEN=<long random value stored outside Git>
```

With public-demo mode enabled:

- `GET /bundles` returns only the fixed synthetic demo bundle.
- Reads for every other bundle return `404`.
- Creating bundles, uploading documents, and reconciliation are disabled.
- The policy-assistant and LLM observability endpoints are disabled, so public
  visitors cannot consume model credits or inspect operational metrics.
- Review corrections and decisions need the `X-DocuGuard-Review-Token` header.
  The reviewer console asks a tester for this code and holds it only in that
  browser tab's session storage.

Share the review code separately from the URL and rotate it after a feedback
round. The deployed dataset is synthetic; never enable this mode as a shortcut
for exposing customer documents.
