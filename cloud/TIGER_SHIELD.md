# Telegram dashboard destination

The Special Edition `/atlas` command and its English/Arabic edition buttons open:

https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/

Tiger Shield remains a private Site with its own sign-in. A Telegram login does
not grant access to the Site. This is a dashboard link, not a shared session,
a Mini App authentication integration or a trading activation.

Update an existing tgcloud deployment's private `.env`:

```dotenv
ATLAS_DASHBOARD_URL=https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/
```

Keep the other values intact. Generate the server-side configuration with
`npm run justai:configure`, then deploy from the linked project using
`npx tgcloud push`. The default and examples now use Tiger Shield, but an
existing `.env` value or generated private configuration overrides the default
until regenerated. No schema migration is needed.
