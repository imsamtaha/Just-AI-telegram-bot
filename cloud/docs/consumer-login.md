# Consumer private login in Telegram

The bot at https://t.me/JustAI_chatbot now offers an explicit self-service login
step inside its private chat. This is a Telegram-identity session, **not** a
Google/ATLAS account link, password login, subscription check, or paid-access
entitlement. Any real Telegram user can log in. No new identity provider or
broker integration is added.

## Customer flow

1. Open `@JustAI_chatbot` and send `/start` (or `/ابدأ`).
2. Read the privacy information and tap **Log in with Telegram** / **سجّل دخول بتلغرام**.
3. Send messages or use the skills/tools in this private chat.
4. Use `/logout` or `/خروج` to end the bot session. It expires after 30 days
   unless the user explicitly logs in again.

`/login` / `/دخول` also establishes the session. `/privacy` / `/خصوصية` works
before login. The bot never asks customers to send a phone number, password,
provider key or Telegram token. Login is authorized only from the sender identity
and matching private-chat ID on an update delivered by tgcloud; command arguments,
display names, and usernames cannot select another user's account.

AI, tools, notes, context and follow-ups require an active session. Pending
follow-ups are checked only during authenticated incoming messages. Logged-out
or expired users receive the login card first; no private memory is read and no
AI request is made. Group chats get a private-chat link instead of AI responses,
even for logged-in users. Login buttons in groups cannot create sessions.
The cloud SDK supplies update identity; there is no anonymous public login endpoint.

## Data and privacy

Private means a one-to-one bot conversation with account-separated memory. It is
not end-to-end encryption and does not prevent the bot operator from reading
cloud storage. The selected AI provider receives messages and context. This is
explained to the customer before login and in `/privacy`.

Logout revokes the session without deleting notes, history or reminders. A user
can log in again and use `/forget` to clear notes/history and `/cancel <id>` for
reminders. One-time migration does not import Python memory. Existing bot customers
must log in explicitly after the update; no sessions are silently grandfathered.

This change uses tgcloud SQLite. The existing website/Supabase login is untouched.
Linking Google/ATLAS accounts or enforcing paid subscriptions would require a
separate verified account-link flow; no email or user metadata is treated as proof.

## Deployment on the owner's phone

The branch includes previous Arabic commands, Trader modes, Lebanese replies and
current ATLAS URL. The existing login credential stays in the local cloud project.
Stop any old Python polling instance, then copy the modules and schema:

```bash
cd ~/Just-AI-telegram-bot
git fetch origin
git switch codex/consumer-private-login
cp cloud/tgcloud/lib/{access,ai,arabic,core,skills,store,tools,trader_skills}.js ~/JustAI_chatbot/tgcloud/lib/
cp cloud/tgcloud/handlers/*.js ~/JustAI_chatbot/tgcloud/handlers/
cp cloud/tgcloud/schema.js ~/JustAI_chatbot/tgcloud/schema.js
cd ~/JustAI_chatbot
npx tgcloud push
npx tgcloud migrate
npx tgcloud webhook
```

The explicit library list excludes `private_config.js`. Your existing deployed
AI credentials stay in the destination project; no configuration regeneration
is needed for this change.

Review migration output: one new `justai_sessions` table is expected, not drops
or changes to existing memory tables. The handler needs that migration before
login succeeds. The webhook should include **message** and **callback_query**.
Run `npx tgcloud webhook sync` if the CLI reports a mismatch.

Test from two separate Telegram accounts: login on one must not log in the other,
notes/history must stay separate, logout must block subsequent AI access, and
group messages must open the private-chat flow. Test Arabic `/دخول`, `/خروج`, and
`/خصوصية`. Automated tests cover these flows with mocked Telegram/AI calls and
real local SQLite session queries, but do not establish live deployment success.

If rolling back, restore the previous handler/core and remove the new callback
handler from the local manifest before pushing. Leave justai_sessions in place;
no destructive table migration is needed. Never bypass the gate as a workaround
for a missing migration or failed session query.

## Entry language selector

The login, privacy and logout cards display **العربية** and **English** buttons.
Customers can switch the entry screen before they log in. An initial `/start`
from a Telegram account with an Arabic interface opens the Arabic login card;
explicitly choosing English overrides that initial detection. Arabic uses
Lebanese wording, including the login button, privacy copy and login confirmation.
Choosing a language does not authenticate the user: they must still press the
login button or send `/login` / `/دخول`. The choice controls the displayed entry
card; it is not a stored account-language preference. Normal AI replies still
follow the user's message language and explicit language requests.

For an already deployed private-login version, copy just
`cloud/tgcloud/lib/access.js` to the corresponding cloud library folder and run
`npx tgcloud push`. No schema migration or credential update is needed.
