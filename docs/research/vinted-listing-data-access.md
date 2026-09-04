# Vinted GPU Listing Data Access: Research Findings

Researched 2026-09-03/04. Question: how should a Python bot reliably read vinted.fr GPU Listing data to compute a Market Price Baseline per GPU Model + Condition and flag Underpriced Listings?

## Summary / Recommendation

**Wrap the internal `api/v2/catalog/items` JSON endpoint via an actively-maintained open-source client, with HTML/OpenGraph scraping as a documented fallback for per-item detail — and poll on a multi-hour cadence, not real-time.**

Concretely:

- Build on **[`Giglium/vinted_scraper`](https://github.com/Giglium/vinted_scraper)** (PyPI: `vinted_scraper`), the most actively maintained of the candidates surveyed (pushed 2026-08-31, 82 stars, only 2 open issues, v4.0.0 released 2026-07-07). It calls Vinted's internal JSON search API for listing search (`search()`), handles cookie acquisition automatically, and falls back to scraping OpenGraph tags from the public item page for single-item detail when the JSON item endpoint 403s.
- Treat it as a thin, swappable adapter, not a foundation to build deep architecture on — every option surveyed is an unofficial reverse-engineered client with no stability guarantee (see Open Risks).
- Favor the **search/listing endpoint** for the bot's actual need (watching many GPU Model queries over time) rather than per-item detail calls, since the bulk `catalog/items` JSON response already carries price, title, brand, condition/status, photos and timestamps — the fields the Market Price Baseline and Underpriced Listing logic need — without hitting the more heavily-blocked single-item JSON endpoint at all.
- Lean into the stated polling cadence (every few hours, not real-time) as the main risk mitigation: low request volume with jittered, human-scale delays and no concurrency is exactly the traffic pattern that stays under Datadome's behavioral-detection radar, per both maintainers' issue threads and third-party write-ups (see ToS & Risk section). This materially changes the risk calculus versus a scraper trying to poll continuously.
- Do not build on the "Vinted Pro Integrations" API — it is a genuine official, authenticated, HMAC-signed API, but it is allowlisted to registered Pro business sellers managing their *own* inventory; it has no read/search capability over the broader marketplace and could not power a cross-seller listing watcher. Confirmed directly from Vinted's own docs: https://pro-docs.svc.vinted.com/ ("Vinted Pro Integrations is available only to a limited set of allowlisted Vinted Pro businesses").

## 1. Internal/Reverse-Engineered API vs. HTML Scraping

Vinted's web frontend calls an internal, undocumented JSON API under `https://www.vinted.fr/api/v2/...` (mirrored per-locale, e.g. `.com`, `.it`, `.de`). There is no official, publicly documented third-party listings/search API — the only *official* API is Vinted Pro Integrations, which is allowlist-gated and scoped to a seller's own catalog (see above), not general marketplace search.

Real open-source clients confirm the internal API is directly callable but fragile:

- **`Giglium/vinted_scraper`** calls `/api/v2/catalog/items` for search, but its own README/code states the equivalent single-item JSON endpoint "is blocked by the anti-bot protection and returns `403`," so its `item()` method instead parses OpenGraph `<head>` tags from the rendered HTML item page as a fallback. It ships automatic cookie fetching (a session/guest cookie is required before the JSON API accepts requests) and a raw `curl()` escape hatch for manual cookie handling. Source: https://github.com/Giglium/vinted_scraper, https://pypi.org/project/vinted-scraper/
- **`herissondev/vinted-api-wrapper`** (PyPI `pyVinted`) also calls the internal API directly (`vinted.items.search(url, ...)`), with no built-in advanced anti-bot handling documented. Its issue tracker records real breakage: [issue #25](https://github.com/herissondev/vinted-api-wrapper/issues/25) reports consistent 403s after roughly 20 requests in 4-5 minutes, recovering after several hours, then blocking again — a rate/behavior-based block, not a hard IP ban. Source: https://github.com/herissondev/vinted-api-wrapper
- **`Pawikoski/vinted-api-wrapper`** (PyPI `vinted-api-wrapper`) is likewise a wrapper around the same internal API (its own README calls it a "Simple client for Vinted Developer API," which is informal branding, not evidence of an official public API — no API key/auth flow is documented, consistent with it being an unofficial client hitting the same undocumented endpoints). Supports 21 country domains and optional proxy configuration. Source: https://github.com/Pawikoski/vinted-api-wrapper
- Pure-HTML scrapers (e.g. `Toffaa/Pynted`, a Scrapy-based scraper) exist as an alternative that avoids the JSON endpoint's anti-bot gate entirely by parsing rendered listing pages, at the cost of more fragile parsing and typically fewer structured fields per item.

**Conclusion:** the internal JSON API is usable — every maintained client surveyed uses it for bulk search — but it requires session/cookie handling, is rate/behavior gated (not simply IP-blocked outright), and single-item JSON detail calls are the most aggressively blocked, pushing maintainers toward HTML/OpenGraph fallback for per-item detail. Bulk catalog search is the more resilient of the two JSON surfaces because it's the one Vinted's own web app relies on most heavily for normal browsing traffic, so it's also the best-tested path in these libraries.

## 2. Fields Exposed

**From the internal JSON search API** (`/api/v2/catalog/items`), as surfaced by real client field lists and a third-party JSON schema writeup:

| Concept | Field(s) seen in the wild | Notes |
|---|---|---|
| Title | `title` | |
| Price | `price` (amount/currency), `currency` | Some clients also read `total_price`, `service_fee` |
| Condition | `status` (e.g. `"Très bon état"`) | This is Vinted's own condition/status attribute — maps directly to this repo's **Condition** |
| Brand | `brand_title` | Useful signal for identifying **GPU Model**, though model itself is usually only in free-text `title` — no dedicated GPU-model attribute exists (Vinted's catalog taxonomy is fashion-first; GPUs sit under "Électronique") |
| Category | `catalog_id` | Numeric catalog/category id; confirmed live that RTX 3070 searches resolve under "Électronique" |
| Images | `photo` (url, high-resolution variant) | |
| Sold/active status | `is_visible` | Listed by `Pawikoski/vinted-api-wrapper`'s field list; a delisted/sold item typically stops appearing in search rather than exposing an explicit "sold" boolean in all clients |
| Timestamps | `created_at_ts` / equivalent creation timestamp | Referenced by a third-party technical writeup (see caveat below); not independently confirmed field-by-field in a client's source in this pass |
| Seller info | `user` object (login/username), rating/review count | Present in `Pawikoski/vinted-api-wrapper`'s and third-party schema descriptions |
| Item URL | `url` | |

Sources: https://github.com/Pawikoski/vinted-api-wrapper (field list: id, title, price, is_visible, discount, brand_title, user info, url, promotion status, photo, favorite count, service fee, total price, view count); live search confirmed via https://www.vinted.fr/catalog?search_text=RTX%203070 (condition labels "Neuf sans étiquette", "Très bon état", "Bon état" observed directly, category breadcrumb "Électronique").

**From HTML/OpenGraph scraping** (the fallback path when the JSON item endpoint 403s): only what's exposed in `<meta property="og:*">` tags on the public item page — `vinted_scraper`'s own README states this is limited to **title, description, url, image**. Price, condition, brand, seller and timestamp fields are *not* reliably available via this fallback — it's meaningfully thinner than the JSON search response. This is a real constraint: don't design the Market Price Baseline pipeline to depend on OpenGraph fallback for condition/price data; keep it on the JSON search response.

**Caveat:** the third-party blog post used to corroborate timestamp/seller field names (dev.to "The Vinted Arbitrage War," https://dev.to/datakaz/the-vinted-arbitrage-war-building-a-scraper-that-doesnt-get-ip-banned-4bh3) is a secondary source of unverified authorship, not Vinted documentation or inspected client source — treat its specific field names (`condition`, `seller.rating`, `created_at`) as plausible but unconfirmed until validated against a live response captured by this project.

## 3. Open-Source Vinted Client Libraries

GitHub metadata pulled directly via the GitHub API on 2026-09-04:

| Library | PyPI package | Wraps | Stars | Last push | Open issues | Notes |
|---|---|---|---|---|---|---|
| [`Giglium/vinted_scraper`](https://github.com/Giglium/vinted_scraper) | `vinted_scraper` | Internal JSON API for search; OpenGraph HTML fallback for item detail | 82 | 2026-08-31 | 2 | Most actively maintained. v4.0.0 (2026-07-07). Sync + async, automatic cookie management, typed responses. README explicitly documents the 403-on-item-JSON-endpoint anti-bot limitation and the fallback. Its own issue tracker has an open, unresolved 403 report on the *base URL itself* ([#59](https://github.com/Giglium/vinted_scraper/issues/59)), showing anti-bot blocking can hit even the initial request. |
| [`Pawikoski/vinted-api-wrapper`](https://github.com/Pawikoski/vinted-api-wrapper) | `vinted-api-wrapper` | Internal API | 71 | 2025-07-16 | 2 | Supports 21 country domains, proxy config. Less recently pushed than `vinted_scraper`. No documented anti-bot handling or auth flow beyond "handling cookies." |
| [`herissondev/vinted-api-wrapper`](https://github.com/herissondev/vinted-api-wrapper) (PyPI `pyVinted`) | `pyVinted` | Internal API | 69 | 2025-05-11 | 11 | Simple, minimal README; item fields limited to title/id/photo/brand_title/price/url/currency. Open, unresolved issue documenting rate-based 403 blocking after ~20 requests in 4-5 minutes ([#25](https://github.com/herissondev/vinted-api-wrapper/issues/25)). Not recently pushed; higher open-issue count relative to size suggests lighter maintenance than `vinted_scraper`. |
| [`vlymar1/vinted-api-kit`](https://github.com/vlymar1/vinted-api-kit) | (see repo) | Internal API + scraping, async | 21 | 2026-06-05 | 0 | Smaller community, but recently active. Not deeply inspected in this pass. |
| [`hipsuc/Vinted-API`](https://github.com/hipsuc/Vinted-API) | — | Internal API | 7 | 2022-07-29 | 1 | Stale (no push since 2022); not recommended. |
| `giaco8020/VintedScraper` | `VintedAPIClient` | HTML scraping (image-download oriented) | 0 | — | 0 | Effectively unmaintained/early-stage; minimal feature set, no anti-bot or schema documentation. |

**Recommendation restated:** `Giglium/vinted_scraper` is the strongest starting point — it's the freshest, has the fewest open issues relative to its usage, and is the only one of the group whose own documentation is explicit about the anti-bot 403 behavior and its fallback strategy, which is exactly the kind of operational honesty you want in a dependency you plan to poll every few hours for months.

## 4. ToS Stance and Realistic Bot-Detection / Rate-Limit Risk

**Vinted's own Terms and Conditions** (fetched directly from https://www.vinted.com/old-terms-and-conditions, Vinted's own domain — note: this URL slug reads as a possibly-superseded version; the current-URL terms page at https://www.vinted.com/terms_and_conditions returned but its substantive body did not render through automated fetch, so it could not be independently re-quoted in this pass. The clause language below matches what multiple independent third-party summaries report for Vinted's *current* terms, which gives reasonable confidence it still reflects the operative wording, but this should be treated as a confirmed-historical / probably-current claim rather than a 100%-current-verbatim one):

- Section "What you must and must not do" prohibits users from:
  > "use any kind of external software tools (including but not limited to: bots, scraping programs, crawling programs, spiders) when registering on the Site and/or when using the Site and/or Services" — unless "authorised, offered or in any other way allowed by" Vinted.
  > "data mine, screen scrape, crawl, disassemble, decompile or reverse engineer any part of the Site."
  > "use any external software tool that could disrupt the normal operation of the Site or Services or infect or damage another User's computer."
- Section "Our rights to handle concerns" gives Vinted latitude to apply corrective measures up to **account blocking**, including without prior notice for safety-relevant or software-tool-misuse violations; a blocked account has its listings delisted and may be barred from creating a new one.

**Plain reading:** running this bot against vinted.fr is a ToS violation regardless of technical approach (internal API or HTML scraping) — Vinted's terms don't distinguish by method, they prohibit "external software tools" broadly. The realistic enforcement path described both by Vinted's own terms and corroborated by third-party accounts is **account-level action** (block/delisting), not legal action against an individual — this bot doesn't need a Vinted account to read public listings, so the practical exposure is more about IP/session blocking than account termination, but should be flagged as a real, acknowledged policy risk to the project owner, not waved away.

**Operational/anti-bot risk, from direct evidence in these libraries' issue trackers and READMEs:**

- Vinted's site (and by extension its internal API surface) sits behind **Datadome**-class bot detection. This isn't from Vinted's own disclosure — it's the maintainers' and third-party analysts' consistent, converging characterization of the 403 behavior these clients hit and had to build around (cookie warming, HTML fallback, VPN sensitivity).
- Concrete breakage evidence: `pyVinted` issue #25 (https://github.com/herissondev/vinted-api-wrapper/issues/25) — 403s after ~20 requests in 4-5 minutes, recovering after several hours; `vinted_scraper` issue #59 (https://github.com/Giglium/vinted_scraper/issues/59) — 403 on the very first request in some conditions, unresolved. `vinted_scraper`'s own README notes "some VPN are banned."
- The blocking pattern described (temporary, request-rate/behavior-triggered, recoverable after a cooldown) is materially different from a permanent hard IP ban — consistent with rate-based bot-scoring rather than a blocklist.

**Why the "every few hours" polling cadence matters:** every piece of direct evidence gathered here points to *request rate and concurrency* as the trigger, not the mere existence of automated traffic — the pyVinted issue's ~20-requests-in-5-minutes threshold, the recovery-after-hours pattern, and `vinted_scraper`'s HTML fallback (needed only because the *heavily-hit* single-item endpoint gets blocked, not the search endpoint generally) all point the same direction. A bot issuing a handful of catalog-search requests every few hours — one request per tracked GPU Model, not per item, with no concurrency — sits far below every observed blocking threshold in this research. This is a genuinely favorable constraint for this project and should inform the eventual polling-interval decision (batch all tracked GPU Model queries into a single slow, jittered pass every few hours rather than any tighter loop).

## Open Questions / Risks for Follow-Up

1. **No confirmed, currently-live JSON field schema captured by this project.** All field names above come from third-party client source/READMEs and one blog post, not a response this project has actually captured and inspected. Before building the Market Price Baseline pipeline, a downstream ticket should make one or a few real requests (via `vinted_scraper`) against a live GPU search and record the actual JSON shape — field names for condition/status, timestamps, and sold/visibility can then be locked down with certainty.
2. **No auth/session strategy has been implemented or verified end-to-end.** All candidate libraries require *some* cookie/session bootstrap against Vinted before the JSON API accepts requests; this project has not yet exercised that flow. Treat "does `vinted_scraper`'s automatic cookie handling actually work reliably from this network/environment" as an open, unverified assumption.
3. **Breakage risk is real and open-ended.** Every client surveyed is an unofficial reverse-engineered wrapper against an undocumented, versionless internal API that Vinted can change without notice; two of the five actively-maintained candidates have open, unresolved 403 issues right now. A downstream ticket should decide a concrete fallback plan (e.g., pin the dependency, monitor for breakage, have an HTML-scrape fallback ready) rather than assuming `vinted_scraper` will keep working unattended.
4. **ToS violation is acknowledged, not resolved.** This document surfaces the risk per the task's request; it does not make a legal/policy judgment call about whether to proceed. That's a decision for the project owner, informed by the low-frequency-polling risk mitigation described above.
5. **GPU Model extraction from free text is unsolved.** There is no dedicated "GPU model" attribute in Vinted's catalog taxonomy — `brand_title` gives the card vendor (e.g. "NVIDIA", "MSI", "Zotac") but the actual model (e.g. "RTX 3070") lives only in the free-text `title`. A downstream ticket will need a title-parsing/matching strategy (e.g. regex/keyword match against a known GPU Model list) to reliably bucket Listings by GPU Model.
6. **Current, verbatim ToS text at the live `terms_and_conditions` URL was not independently re-confirmed** (see caveat in section 4) — worth a follow-up direct check (e.g., viewing the rendered page in a browser rather than an automated fetch) before treating the quoted clauses as certainly-current wording.

## References

- Vinted Pro Integrations API docs (official, allowlisted, seller-scoped — not usable for this bot): https://pro-docs.svc.vinted.com/
- Vinted Terms and Conditions (quoted clauses on automated tools/scraping/bots): https://www.vinted.com/old-terms-and-conditions
- Vinted Terms and Conditions (current URL, body did not render via automated fetch): https://www.vinted.com/terms_and_conditions
- Live Vinted search confirming Électronique category + condition labels for GPUs: https://www.vinted.fr/catalog?search_text=RTX%203070
- `Giglium/vinted_scraper` (recommended library): https://github.com/Giglium/vinted_scraper ; PyPI: https://pypi.org/project/vinted-scraper/
- `Giglium/vinted_scraper` issue #59 (403 on base URL, unresolved): https://github.com/Giglium/vinted_scraper/issues/59
- `herissondev/vinted-api-wrapper` (pyVinted): https://github.com/herissondev/vinted-api-wrapper
- `herissondev/vinted-api-wrapper` issue #25 (rate-based 403 blocking): https://github.com/herissondev/vinted-api-wrapper/issues/25
- `Pawikoski/vinted-api-wrapper`: https://github.com/Pawikoski/vinted-api-wrapper ; PyPI: https://pypi.org/project/vinted-api-wrapper/
- `vlymar1/vinted-api-kit`: https://github.com/vlymar1/vinted-api-kit
- `hipsuc/Vinted-API` (stale, not recommended): https://github.com/hipsuc/Vinted-API
- `giaco8020/VintedScraper` (early-stage, not recommended): https://github.com/giaco8020/VintedScraper
- Secondary/corroborating source on Datadome anti-bot behavior and operational workarounds (blog post, unverified authorship — used only as corroboration, not as a primary claim source): https://dev.to/datakaz/the-vinted-arbitrage-war-building-a-scraper-that-doesnt-get-ip-banned-4bh3
- GitHub API metadata (stars/last-push/open-issues), pulled directly 2026-09-04: `api.github.com/repos/{owner}/{repo}` for each library above.
