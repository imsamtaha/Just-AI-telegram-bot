FROM node:24-bookworm-slim@sha256:873f586f3794f52281bd039bf02c048a0be08fde619338f9941bad1eb6b34530
WORKDIR /app
COPY --chown=node:node cloud/package.json ./cloud/package.json
COPY --chown=node:node cloud/tgcloud/lib/access.js cloud/tgcloud/lib/ai.js cloud/tgcloud/lib/arabic.js cloud/tgcloud/lib/core.js cloud/tgcloud/lib/edition.js cloud/tgcloud/lib/skills.js cloud/tgcloud/lib/store.js cloud/tgcloud/lib/tools.js cloud/tgcloud/lib/trader_skills.js ./cloud/tgcloud/lib/
COPY --chown=node:node server/*.mjs ./server/
RUN mkdir -p /data && chown node:node /data
USER node
ENV BOT_MEMORY_PATH=/data/bot.sqlite3
STOPSIGNAL SIGTERM
CMD ["node","server/bot.mjs"]
