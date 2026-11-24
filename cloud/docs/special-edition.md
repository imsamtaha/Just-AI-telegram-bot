# JUST AI · ATLAS Special Edition

A guided bilingual private workspace built on the existing consumer login.
This is a product edition name, not a paid subscription entitlement.

## What customers see

After `/login` or the Telegram login button, the confirmation carries a branded
inline action menu. `/start`, `/home`, `/edition` and `/الرئيسية` open the personal
home screen for authenticated users. The user's Telegram first name is shown as
plain text; it is not used for authorization.

- **Market desk · BTC**: one-tap BTC-USD/1h quote plus closed-candle indicators.
- **AI briefing · BTC**: fetches both data sources, then asks the configured model
  to explain only the supplied snapshot, missing inputs and risk considerations.
- **Trading skills**: the existing Trader analysis-mode directory.
- **Creative studio**: writing, design, translation and planning selectors.
- **My workspace**: counts only the current user's saved notes and pending
  follow-ups, with buttons to view them, inspect privacy, or log out.
- **ATLAS dashboard**, Arabic/English home buttons, and full command help.

The creative selectors now return a local input hint when no brief is supplied,
without spending an AI request. Supply the command plus your brief to use AI.

## Commands

| English | Arabic | Purpose |
| --- | --- | --- |
| `/home`, `/edition` | `/الرئيسية`, `/نسخة_خاصة` | Personal home and action buttons. |
| `/studio` | `/استوديو` | Creative skill selectors. |
| `/workspace` | `/مساحتي` | Own notes/follow-up counts and shortcuts. |
| `/desk BTC-USD 1h` | `/مكتب_السوق BTC-USD ١س` | Sourced quote + closed-candle snapshot, no AI request. |
| `/brief ETH-USD 15m` | `/موجز ETH-USD ١٥د` | Snapshot plus grounded AI interpretation. |

`/desk` and `/brief` default to BTC-USD/1h; a symbol alone defaults to 1h.
Market data remains public Coinbase crypto data, with source/last-trade and
last-closed-candle timestamps. It is not a stock/forex feed or licensed real-time
execution quote. SMA20 uses 20 continuous closed candles; RSI14 uses simple
averages, not Wilder smoothing. Existing stale-data labels are retained.

A complete quote and indicator result are required before a briefing calls AI.
Incomplete/malformed/API-error data produces an explicit unavailable message,
not invented prices. AI failures preserve the successful sourced snapshot.
The model is instructed to distinguish observation, interpretation, unknowns and
next steps; stale data must not be turned into an actionable setup. Model output
is not deterministic or guaranteed; verify important numbers independently.

AI briefing uses the current user's saved preferences and saves the completed
snapshot + interpretation as a normal bounded conversation turn. `/desk` remains
a stateless utility. Private data is never put in callback payloads; buttons use
fixed enumerated commands and the existing Telegram callback/identity checks.
No new orders, background monitoring, subscription verification, or secret entry
points are added. Cloud reminders still require the next incoming message.

## Deployment

For a deployed consumer-login bot, update the runtime modules:

```bash
cd ~/Just-AI-telegram-bot
git fetch origin
git switch codex/atlas-special-edition
cp cloud/tgcloud/lib/{access,ai,arabic,core,edition,skills,store,tools,trader_skills}.js ~/JustAI_chatbot/tgcloud/lib/
cd ~/JustAI_chatbot
npx tgcloud push
```

This copies no API credentials and adds no schema columns. If the private-login
update has not yet been deployed, also copy `handlers/message.js`,
`handlers/callback_query.js` and `schema.js` from this branch, then run
`npx tgcloud push`, `npx tgcloud migrate`, and `npx tgcloud webhook`. The login
session table and callback delivery are prerequisites, not optional.

Test `/start` while logged out, log in, then try `/الرئيسية`, the Creative studio,
`/workspace`, `/desk BTC-USD 1h`, and `/brief BTC-USD 1h`. AI briefings send the
snapshot/preferences to the configured provider and use API credits. No live
Telegram/provider/market test was performed during development; automated tests
mock outbound requests and exercise the gate, routing and failure behavior.
