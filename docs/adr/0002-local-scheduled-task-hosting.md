# Local scheduled task for bot execution

We run the bot on the user's own machine via Windows Task Scheduler, once daily at 10am, rather than on an always-on cloud/free-tier host ([#6](https://github.com/JulesCinc/vinted-bot/issues/6)). The bot is a run-once script, not a persistent daemon: local execution makes the SQLite seen-set ([ADR 0001](0001-seen-listing-state-for-alert-dedup.md)) trivially persistent without needing a mounted volume or hosted database, and this is a single-user hobby bot with no uptime requirement. The scheduled task has "wake the computer to run this task" enabled, so a sleeping (not powered-off) machine still runs on time; if the machine is fully off at 10am, that day's check is silently skipped rather than caught up later.

## Considered Options

- **Cloud/free-tier hosting** (rejected): most free-tier schedulers (GitHub Actions cron, serverless functions) are ephemeral and would need extra plumbing — a mounted volume, committing the SQLite file back to the repo, or an external hosted DB — just to keep the seen-set alive between runs; not worth the complexity for a personal bot.
- **Catch-up on a missed run** (rejected): would require tracking last-run time, detecting a gap, and avoiding a double-run if the task merely ran late — real complexity for a low-stakes edge case where missing one day of listings costs nothing.

Note: settles on a once-daily cadence, a coarser interval than the "checks every few hours" framing recorded in issue #1's original charting.
