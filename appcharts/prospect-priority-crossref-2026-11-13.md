# Prospect priority cross-reference — Nov 13, 2026

Join of the 92 strict buyers (ranks 1–75, `top75-strict-buyers-2026-11-13.csv`)
against today's top-100 AppGoblin enrichment (`top100-enriched-2026-11-13.csv`,
Nov 13 chart). Built 2026-11-13 ~13:35 ET. All installs/MAU/revenue are
AppGoblin modelled estimates, not Apple's numbers.

## Headline

- 92 strict buyers sit across **46 apps** in ranks 1–75.
- **Tier A — 11 apps**: a strict buyer AND an attribution SDK AND at least one
  SKAdNetwork network. Strongest corroboration on both sides.
- **Tier B — 21 apps**: a strict buyer plus one of the two app signals.
- **Tier C — 14 apps**: a strict buyer but no attribution SDK and no SKAN
  detected. Do NOT deprioritise on this alone — AppGoblin detection is
  incomplete (Kalshi runs AppsFlyer yet shows 0 SKAN IDs; Google's own apps
  return zero SDK vendors). The people signal is primary here.
- **17 apps in ranks 1–75** show a strong buying signal (attribution SDK
  and/or SKAN ≥ 10) but have **no strict buyer yet** — the second-pass list.
- **Moloco**: listed by 19 of the top 100; only 5 of those 19 already have a
  strict buyer. The other 14 are the clearest second-pass / next-batch filter.

## Tier A — buyer + attribution SDK + SKAN (11 apps)

| Rank | App | Buyers | Attribution SDK | SKAN (n) | Moloco | MAU (est) |
|---|---|---|---|---|---|---|
| 1 | TikTok Pro | 5 | AppsFlyer | 2 | — | 0.8M |
| 3 | Vinted | 2 | Adjust | 187 | yes | 67.2M |
| 7 | PineDrama | 5 | AppsFlyer | 1 | — | 2.0M |
| 22 | TikTok | 5 | AppsFlyer | 1 | — | 83.1M |
| 26 | Microsoft Outlook | 1 | Singular | 2 | — | 71.8M |
| 31 | Amazon Shopping | 1 | AppsFlyer | 1 | — | 32.4M |
| 44 | Spotify | 5 | Branch | 1 | — | 326.6M |
| 64 | Pinterest | 3 | Branch | 51 | yes | 33.0M |
| 65 | Reddit | 5 | AppsFlyer | 1 | — | 12.8M |
| 70 | Cleanup | 2 | Adjust | 160 | yes | 4.9M |
| 74 | Duolingo | 4 | Adjust | 167 | yes | 18.7M |

## Tier B — buyer + one app signal (21 apps)

ChatGPT (4, SKAN 6, Moloco, 125.3M MAU), GoWish (9, AppsFlyer),
Kalshi (10, AppsFlyer), Walmart (11, AppsFlyer), Capital One Mobile (12,
Kochava), Whatnot (19, AppsFlyer), Google (20, SKAN 1), Facebook (33, SKAN 2),
Rips by Triumph (34, AppsFlyer), Instagram (36, SKAN 2), Partiful (43,
Branch), YouTube (47, SKAN 1), Cash App (49, AppsFlyer), Indeed (50,
AppsFlyer), Ticketmaster (54, AppsFlyer), McDonald's (63, Kochava),
Venmo (67, Branch + Kochava), Snapchat (69, SKAN 1), Canva (71, AppsFlyer +
Branch), T-Life (73, Branch), Airbnb (75, Branch).

## Tier C — buyer only, no app signal detected (14 apps)

BigFuture School (5), Claude (6), Google Gemini (8), Gmail (18), Shop (23),
Google Maps (29), Microsoft Authenticator (32), DoorDash (35), Google Chrome
(37), Microsoft Teams (40), Uber (53), Netflix Game Controller (57), Zoom
(66), Target (68). Includes obvious big advertisers (DoorDash, Uber, Target)
— treat as a detection gap, not a negative signal.

## Second pass — ranks 1–75, strong app signal, no strict buyer yet (17 apps)

- CapCut (15) — AppsFlyer, SKAN 157, Moloco; Clay found people (Brand
  Marketing Lead, Head of CapCut) but none passed the strict filter.
- BlinkDrama (24) — Adjust + AppsFlyer, SKAN 256, Moloco; Clay returned
  nothing. Small (374K MAU) but the strongest app-side signal in the list.
- X (25) — SKAN 57, Moloco; Clay found 6 people, none strict (growth
  strategy/analytics, senior marketing).
- Depop (17) — Branch; Clay found 5 people, none strict (product/seller
  growth).
- Freecash (42) — Adjust, SKAN 171, Moloco.
- ReelShort (59) — AppsFlyer, SKAN 164, Moloco.
- Life360 (55) — AppsFlyer + Branch, SKAN 162, Moloco.
- Bible Chat (52) — Branch + Singular, SKAN 49, Moloco.
- VIZIO Remote (27) — AppsFlyer.
- DealSeek (30) — AppsFlyer, SKAN 2.
- Grok (38) — AppsFlyer.
- Capital One Shopping (39) — Kochava (parent Capital One already covered).
- Koupon (41) — AppsFlyer.
- PayPal (45) — Adjust.
- Trust Wallet (48) — Adjust.
- Discord (51) — AppsFlyer.
- OnePay (56) — AppsFlyer + Branch, SKAN 1.

Note: most of these returned no Clay contacts at all in the earlier batches;
a second pass needs a different angle (parent company / domain), not a
repeat of the same search. CapCut, X and Depop are the exceptions — people
exist, they just don't pass the strict buyer rule.

## Ranks 76–100 — priority order for the next Clay batch (not yet prospected)

1. NetShort (76) — AppsFlyer, SKAN 262, Moloco, 3.2M MAU
2. DramaBox (85) — AppsFlyer, SKAN 258, Moloco, 5.6M MAU
3. FreeDrama (83) — AppsFlyer, SKAN 176, Moloco
4. DramaWave (98) — AppsFlyer, SKAN 158, Moloco
5. CrimeRadar (93) — Adjust, SKAN 161, Moloco
6. SHEIN (96) — AppsFlyer + Branch, 50.1M MAU
7. Klarna (86) — AppsFlyer, 48.4M MAU
8. Best Buy (77) — Branch, SKAN 2
9. Walgreens (90) — Branch
10. Waymo (91) — Kochava
11. Roku Remote (84) — SKAN 49, Moloco — flag: Roku is sell-side (Fox/Roku
    ad sales), so the strict filter will likely exclude its people; check
    before spending a batch on it.
12. Giftful (78) — AppsFlyer; Taco Bell (99) — AppsFlyer; Grok Bot (94) —
    AppsFlyer. No SKAN signal; lower priority.
No-signal remainder (79 Disney+, 80 Google Sheets, 81 Costco, 82 Uber Eats,
87 Lyft, 88 Suno, 89 Netflix, 92 LinkedIn, 95 eBay, 97 Instants, 100
Microsoft Copilot) — people-first prospecting only; Uber Eats/Netflix/eBay
are covered via parents/sibling apps in some cases.

## Caveats

- SKAN IDs can linger in a build after a campaign ends — read as "configured
  to buy through that network", not proof of a live campaign this week.
- SKAN zeros are unreliable (Kalshi, Google apps); big counts are the
  trustworthy direction.
- Ranks are the Nov 13 chart; the next daily digest (Nov 14, 7:12am ET) will
  move some ranks. Buyer names/LinkedIn URLs are in the top-75 file; this
  file adds the priority layer only.
