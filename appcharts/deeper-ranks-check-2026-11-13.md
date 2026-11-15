# Deeper ranks check — can any free third-party API go past 200 per category?

Checked 2026-11-13 (live tests, no sign-in, no payment, no accounts created).
Context: Apple's public chart pages are verified capped at 200 per category
(25 hydrated apps + 175 remaining IDs, no pagination pointer in the page JSON).
Question: does any free third-party API give US iOS Top Free ranks 201+?

## Verdict

**No. None of the free sources goes deeper than 200.** The 200 cap is Apple's
own publication limit, and every free service that republishes Apple charts
inherits it. The only routes to ranks 201+ would be paid ASO tools with
modelled/estimated ranks (Sensor Tower, data.ai, AppTweak paid) — or
per-app rank-history lookups for apps you already know, which can't
enumerate a 201–400 list. Any deeper source would be modelled data, not
Apple's published chart, so it would not be directly comparable to ranks 1–200.

No pipeline change is needed — and none is available for free.

## 1. App Store Tracker — cap is 200, key required

- MCP: https://www.appstoretracker.com/api/mcp (Streamable HTTP). Free: 750 tool
  calls/month with an account; 100/min per key.
- `get_rankings` input schema, read live from `tools/list` (keyless):
  inputs are `country`, `category_id`, `chart` (only `top_free`), `limit`.
  **limit: integer, minimum 1, maximum 200, default 100. No offset
  parameter.** There is no way to page past 200.
- Live test: `tools/call` without a key returns
  `{"error":{"code":-32000,"message":"Missing API key"}}` (docs confirm
  `initialize`/`tools/list` answer keyless, `tools/call` needs a key).
  So a live accuracy test was not possible without signing up — not done,
  per instructions.
- Accuracy (indirect): the service republishes Apple's charts; its own
  Nov 10 example shows Kalshi #1 in US Finance, matching Apple's verified
  Nov 13 Finance chart (1 Kalshi, 2 Capital One Mobile). Ranks should
  track Apple's closely, but snapshot timing differs (daily capture).
- Free-tier math kills it for the daily run anyway: 42 categories × 1 call
  a day × 30 days = 1,260 calls/month, over the 750 free calls — before
  any deeper-rank work.
- Plain-GET form exists for scripts ("the same key works for every tool as
  a plain GET") but needs the account key, so it was not tested.

## 2. AppGoblin — no chart-list endpoint at all

- Public v1 API (https://appgoblin.info/api-docs) exposes exactly 5 tools:
  `get_app` (metadata), `get_app_ranks` (one app's 90-day best ranks across
  countries), `get_app_sdks`, `list_companies`, `get_company` (paid tier).
  There is **no endpoint that returns a top chart list at any depth**.
- Keyless test: `GET /api/v1/apps/1632713844/ranks` (Kalshi) returns
  HTTP 401 `{"status_code":401,"detail":"Missing API key — send it as the
  Authorization: Bearer <redacted>"}`.
- Free keys exist (30 req/min, 1,000 req/day) but need an account signup
  at appgoblin.info/account/api-keys — not created. Even with a key, the
  API can only tell you where a known app ranks; it cannot enumerate
  ranks 201–400.

## 3. AppWinners — no API, republishes Apple's charts, cap 200

- Free web charts only, no API (per Nov 12 audit).
- The site records the public iOS charts once a day (~06:00 UTC) and keeps
  every snapshot. Its own FAQ states: "How many apps does the chart show?
  200 apps today. The iOS App Store publishes up to 200 positions for this
  chart; we show every position the store published."
- No direct US Finance chart URL surfaced via search, so no per-page count
  was done; the FAQ statement is the evidence, and it follows from the
  source (Apple's public charts) that the cap is 200.

## Bonus checks (not in the Nov 12 audit, quick look)

- mwm.ai US Finance free page (https://mwm.ai/rankings/countries/US/devices/iphone/categories/6015):
  web list is explicitly "Top 25"; its top ranks match Apple (1 Kalshi,
  2 Capital One Mobile) but it is a proprietary modelled pipeline, not
  Apple's chart, and the page shows far fewer than 200.
- storelift.net: top 100 only ("Apple's own top free chart ... with
  100 apps").
- m-s-y.com: "Top Free Finance Apps – US App Store Top 200" — also 200.

## What a deeper-rank pipeline would need (if Liam ever paid for one)

- A paid ASO vendor (Sensor Tower / data.ai / AppTweak) whose ranks are
  modelled estimates, not Apple's published order.
- A new fetch step for ranks 201+ only, kept in separate sheets/columns
  clearly marked as modelled data — never merged into the 1–200 Apple
  columns, or the Prev Rank / Change / New comparisons would mix two
  different measurements.
- Re-verification of that vendor's top 200 against Apple's before trusting
  its 201+.

## Sources

- App Store Tracker MCP docs: https://www.appstoretracker.com/mcp
  (tools/list schema read live 2026-11-13; get_rankings limit max 200)
- AppGoblin API docs: https://appgoblin.info/api-docs; MCP tool list:
  https://github.com/max-crab/appgoblin-mcp
- AppWinners: https://appwinners.eu/ (FAQ: 200 apps, "we show every
  position the store published")
- mwm.ai Finance chart: https://mwm.ai/rankings/countries/US/devices/iphone/categories/6015
