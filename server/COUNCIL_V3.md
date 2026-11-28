# Council v3 research status

The Special Edition shared core supports `/council_v3`, `/v3`, `/مجلس_٣` and `/مجلس_3`, plus a Council v3 edition button. Private-chat login remains required. Arabic responses use Lebanese wording.

This evidence viewer cannot activate trading, change Council weights or place orders. The separate `imsamtaha/Trading-ai` research evaluator must establish out-of-sample edge after costs; no model is promoted by this change.

## Configure and deploy

This branch extends `codex/aws-continuous-reminders` and targets the JavaScript Special Edition cloud/native runtime, not the independent Python main branch.

Optionally set `ATLAS_EDGE_V3_STATUS_URL` in the private deployment `.env` to the sanitized HTTPS `/agent/v3/status` endpoint of your Trading-ai API. That API needs `ATLAS_EDGE_V3_REPORT` pointing to a fresh offline research report. Credentials, query strings and fragments are rejected in the status URL. Never expose owner credentials or raw private reports.

For tgcloud: copy the updated shared libraries `core.js`, `arabic.js`, `edition.js` and new `council_v3.js` into the existing project's `tgcloud/lib/`; update its `scripts/configure.mjs` from this cloud directory. Preserve `.env`, `.tgcloud` and generated private configuration. Run `npm run justai:configure` and `npx tgcloud push` in your existing project. No schema migration is needed.

For the AWS/Azure native service: update the checkout and rebuild/restart using the existing server deployment guide. The Dockerfile includes the new module. Preserve the persistent SQLite volume and private environment. Only one Telegram delivery runtime should own updates; polling and cloud webhooks must not compete.

Sign into the bot and send `/council_v3`. With no status service/report it should say UNAVAILABLE. Accepted responses must remain RESEARCH_ONLY/ABSTAIN with both execution flags false. Research R per decision is not live equity performance. STC-04/STC-09 reviews and worker operation require independent verification.

Publishing this branch does not deploy the Telegram cloud app or restart a VM. Those steps require access to the actual runtime, which is not stored in this repository.
