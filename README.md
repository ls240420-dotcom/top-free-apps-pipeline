# Code review pack — Top Free apps pipeline + prospecting + Play prototype
Built Nov 14, 2026. Code only (no chart data, no credentials, no API keys).

## Daily charts pipeline (appcharts/)
- charts.py — fetches Apple's public chart pages + iTunes Lookup enrichment
- build_daily.py — builds the daily US_Free_Charts_YYYY-MM-DD.xlsx (42 sheets x 200)
- upload_to_sheets.py — uploads the daily file to the "US Free Charts" Google Sheet
- build_master.py — builds the Master List tab (one row per App ID) + uploads it

## AppGoblin enrichment (appcharts/)
- appgoblin_enrich.py — enriches apps via AppGoblin get_app + get_app_sdks (2 calls/app)
- merge_enrichment.py — merges raw batches into the persistent store appgoblin-enrichment.json
- merge_top100.py / append_enriched.py — build the merged enriched CSV (dedupes by App ID, best rank)
- map_skan.py / skanlib.py — SKAdNetwork ID -> company mapping (112-network registry)
- upload_enrichments.py — uploads the Enrichments tab
- rebuild_chunk_csv.py — one-off rebuild helper

## Prospecting (appcharts/)
- strict_filter.py — the strict-buyer title classifier (growth / performance / UA / paid media only)
- clay_ranks26_50.py / clay_ranks51_75.py — Clay search drivers for ranks 26-50 and 51-75

## Google Play prototype (appcharts/play-prototype/)
- compare_play_ios.py — matches Play Top Free apps against the iOS Master List (4 tiers)

## Connector clients (custom-connectors/<name>/bin/)
- custom.appgoblin/bin/client.py — AppGoblin REST (ranks/app/sdks)
- custom.clay/bin/client.py — Clay MCP people/company search
- custom.prospeo/bin/client.py — Prospeo REST (search/enrich person + company)
- custom.apollo/bin/client.py + probe.py — Apollo MCP (Free plan: search + enrichment refused)

## Notes (appcharts/*.md)
- prospect-priority-crossref-2026-11-13.md — Tier A/B/C buyer tiers + 17-app second pass + ranks 76-100 order
- ad-library-prototype-2026-11-14.md — Meta/Google/TikTok ad-library results for Tier A
- deeper-ranks-check-2026-11-13.md — why 200/category is the cap
- apollo-mcp-prep-2026-11-13.md — Apollo MCP setup notes
