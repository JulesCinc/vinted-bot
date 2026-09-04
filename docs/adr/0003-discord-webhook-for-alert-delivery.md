# Discord Alert delivery via incoming webhook

We deliver Alerts to a single Discord channel via an Incoming Webhook (a plain HTTPS POST), not a Discord bot ([#7](https://github.com/JulesCinc/vinted-bot/issues/7)). The bot runs as a one-shot daily script with no persistent process to host a bot/gateway connection ([ADR 0002](0002-local-scheduled-task-hosting.md)), and Alerts need no interactivity or multi-channel routing that would justify a bot's extra setup (application registration, server invite, permissions). The webhook URL is stored via an env var, the same convention as the SQLite seen-set path.

Each Alert is a plain-text message, not a rich embed, showing only the Listing's GPU Model, price, Market Price Baseline, and a link — Condition and a photo are left out. If GPU Model can't be confidently parsed from the Listing's title, the Alert still fires, showing the raw title in GPU Model's place rather than staying silent.

On send failure, the script retries once — honoring Discord's `Retry-After` header if the failure was a rate limit (429), otherwise waiting a fixed ~3s — then logs the failure to a dedicated log file (path configurable via env var) and drops it. No further retry is attempted in-run: because the seen-record is only written after a successful send ([ADR 0001](0001-seen-listing-state-for-alert-dedup.md)), a dropped Alert is naturally retried on the next day's scheduled run.

## Considered Options

- **Discord bot** (rejected): would need a persistent gateway connection or at least app registration, server invite, and permission grants — none of which buys anything when delivery is one-way to a single fixed channel.
- **Rich embed with Condition and photo** (rejected): more visually useful, but adds no information the underpriced-filter hasn't already vetted, and photo hotlinking permanence against Vinted's URLs was an unconfirmed risk not worth taking on for a personal alert bot.
- **In-run retry loop until success** (rejected): redundant — ADR 0001's send-before-seen-write ordering already gives every dropped Alert a free retry on the next scheduled run.
