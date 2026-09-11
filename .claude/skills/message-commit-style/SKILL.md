---
name: commit-message-style
description: Use when writing or suggesting a commit message for this repository — after staging changes, right before running `git commit`, or when explicitly asked to write/review a commit message. Not for PR titles, PR descriptions, or CHANGELOG entries.
---

# Commit Message Style

This repo follows Conventional Commits. Apply this whenever you are about to write a commit message.

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Types

- `feat` – new functionality
- `fix` – bug correction
- `build` – build system or external dependency changes
- `ci` – CI/integration and configuration file changes
- `perf` – performance improvements
- `refactor` – code changes that neither add a feature nor fix a bug
- `style` – formatting changes with no functional impact
- `docs` – documentation-only changes
- `test` – adding or correcting tests
- `revert` – reverting a previous commit

## Scope

Optional, identifies the affected area of the project (e.g. `vinted-client`, `alerts`, `adr`).

## Subject

- Imperative present tense ("add", "fix", "update" — not "added" or "adds")
- No capital letter, no trailing period
- Max ~50 characters
- Says succinctly what changed

## Body

- Optional, wrap around 72 characters
- Imperative present tense
- Explains *why* the change was made and how the new state differs from the previous one — not *how* it was implemented, since that's visible in the diff

## Footer

- Optional
- References related issues/tickets (e.g. `Closes #12`)
- Used for breaking changes (`BREAKING CHANGE: ...`)

## Example

```
fix(vinted-client): retry search requests on 429

Vinted throttles rapid polling and was causing silent search
failures. Retrying with backoff keeps the bot within rate limits
instead of dropping results.

Closes #18
```