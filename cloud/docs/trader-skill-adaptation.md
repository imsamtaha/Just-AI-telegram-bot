# Trader skill pack adaptation

Source: https://github.com/Jakeschincariol/trader-skill

Pinned source commit: `5189e79b9a480755a3733ac9713f5353981dbe18`.
Reviewed: 2026-11-23. Author: Jake Schincariol. License: MIT, included verbatim
in [trader-skill-LICENSE.txt](trader-skill-LICENSE.txt). The runtime adapter
also carries the author/source attribution.

All eleven upstream SKILL.md methods were reviewed. Runtime instructions are
adapted summaries, not verbatim installations or claims that the Python scripts
were ported. Historical upstream examples are deliberately excluded from prompts;
they are not independently verified current facts. Neither the upstream Python
programs nor their data/example files are downloaded or executed by the bot.

| Telegram command | Adapted scope |
| --- | --- |
| `/trader_copycat` | Analyze supplied 13F holdings, dates, weights and changes. |
| `/trader_news` | Review pasted articles/filings and portfolio relevance. |
| `/trader_budget` | Propose allocations within supplied reserve/cap/order limits. |
| `/trader_pelosi` | Interpret pasted congressional disclosures and reporting delays. |
| `/trader_analyst` | Compare supplied earnings, margins, EPS and compatible periods. |
| `/trader_screener` | Review supplied candidates against explicit screening criteria. |
| `/trader_risk` | Conversational proposed-order review; not a machine-enforced gate. |
| `/trader_broker` | Draft hypothetical tickets; no brokerage connector or execution. |
| `/trader_tax` | Supplied tax-lot scenario arithmetic; asks for jurisdiction. |
| `/trader_alerts` | Design price-condition rules; no unattended alert monitoring. |
| `/trader_rebalance` | Review supplied portfolio drift and hypothetical adjustments. |

`/trader` shows the pack; `/skills` includes these alongside existing modes.
Underscores are the canonical Telegram command names. Original hyphen spellings
(e.g. `/trader-risk`) also work as typed text commands, with optional `@BotName`.
The bot retains existing `/risk`, `/trading` and other commands.

Skills require the configured AI provider and user-supplied text. They do not
fetch links, analyze file attachments, register a portfolio or access local
`trader/*.json` files. They cannot call the bot's tools automatically. Paste tool
output or source text into the request. Quotes remain limited to Coinbase crypto
pairs. No SEC User-Agent identity is requested because there is no SEC client.
No brokerage keys are needed or accepted for these analysis modes.

The original pack's fingerprinted risk gate, per-order approvals and Claude
permission-card workflow are not available in Telegram; the adaptation explicitly
avoids representing an LLM response as a verified risk pass or order approval.
Original desktop installation/connector instructions are not injected into prompts.
The bot has no execution code path; a user typing yes cannot place an order.

## Update an already deployed tgcloud bot

Do not rerun the starter installer on your customized cloud handler. Instead:

```bash
cd ~/Just-AI-telegram-bot
git fetch origin
git switch codex/trader-skill-pack
cp cloud/tgcloud/lib/trader_skills.js ~/JustAI_chatbot/tgcloud/lib/
cp cloud/tgcloud/lib/skills.js ~/JustAI_chatbot/tgcloud/lib/
cp cloud/tgcloud/lib/core.js ~/JustAI_chatbot/tgcloud/lib/
cp cloud/tgcloud/lib/ai.js ~/JustAI_chatbot/tgcloud/lib/
cd ~/JustAI_chatbot
npx tgcloud push
```

`ai.js` preserves the Lebanese Arabic update; private_config.js, credentials,
cloud tables and existing memory are untouched. No schema migration is required.
Then send `/trader` and `/trader_budget` with your budget, target weights and
constraints. Sending a ticker alone will prompt for missing data, not produce
invented live analysis. Test with paper scenarios first.
