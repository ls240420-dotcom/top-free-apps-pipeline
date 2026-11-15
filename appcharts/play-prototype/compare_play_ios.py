#!/usr/bin/env python3
"""Compare a Google Play Top Free CSV (from AppBrain) against the iOS
Master List snapshot, and write the Play apps that are NOT in the iOS
Top 200 (Nov 12-14 universe) to a CSV.

"Not on iOS" means: not in the iOS Top 200 charts in the Master List
snapshot — NOT "doesn't exist on the App Store". Apple TV, for example,
exists on iOS but didn't chart in the top 200 on those days, so it
correctly lands on the list.

Matching tiers (name + developer, because the two stores title the same
app differently — "Vinted: Pre-loved marketplace" on iOS vs
"Vinted: Shop & sell pre-loved" on Play):
  A exact: normalized full names equal.
  B core+dev: same core name (before : / - / dash) + developer overlap.
  B2 subset+dev: Play core tokens are a subset of the iOS full-name
     tokens (e.g. "prime video" in "amazon prime video") + developer
     overlap.
  C first-token: same first significant token + a Lite/Pro-style
     qualifier guard (a Play-only "Lite"/"Pro" blocks the match, so
     TikTok Lite never matches TikTok) + developer overlap, or a
     distinctive token (>= 7 chars). Generic first tokens (pdf, bible,
     google, apple, ...) never fire tier C.
Developer matching is token overlap after stripping legal suffixes and
generic words (media, studio, labs, ...), plus a prefix rule
(macy ~ macys) and an alias map (amzn -> amazon).

Usage: compare_play_ios.py <play.csv> <master-list.xlsx> <out.csv>
Writes only the NOT-on-iOS rows (plus any rows whose status is not
"on iOS"); prints counts and the tier-C/B2 matches for eyeballing.
"""
import csv
import re
import sys

import openpyxl

STOPWORDS = {'by', 'the', 'a', 'an', 'and', 'for', 'with', 'app', 'free', 'official'}
LEGAL = {'inc', 'llc', 'ltd', 'corp', 'corporation', 'co', 'pte', 'gmbh', 'sas',
         'aps', 'ab', 'ag', 'bv', 'srl', 'pty', 'ltda'}
DEV_GENERIC = LEGAL | {'media', 'studio', 'studios', 'apps', 'mobile', 'digital',
                       'interactive', 'labs', 'lab', 'software', 'games', 'game',
                       'tech', 'technologies', 'technology', 'network', 'networks',
                       'group', 'global', 'international', 'publishing', 'works',
                       'dev', 'team', 'company', 'holdings', 'entertainment',
                       'solutions', 'systems', 'innovations', 'creations',
                       'productions', 'health', 'healthcare', 'care', 'for',
                       'and', 'the', 'of', 'a', 'an', 'to', 'in', 'on'}
GENERIC = {'pdf', 'bible', 'cleaner', 'photo', 'video', 'music', 'browser',
           'scanner', 'reader', 'calendar', 'weather', 'maps', 'mail', 'chat',
           'tv', 'radio', 'news', 'sports', 'fitness', 'notes', 'files',
           'camera', 'keyboard', 'launcher', 'widget', 'clock', 'compass',
           'google', 'apple', 'microsoft', 'meta', 'amazon', 'samsung', 'free',
           'best', 'top', 'pro', 'lite', 'plus', 'hd', 'go', 'mini', 'smart',
           'easy', 'fast', 'super', 'my', 'all', 'qr', 'daily', 'health', 'phone'}
QUALIFIERS = {'lite', 'pro', 'plus', 'go', 'mini', 'hd', 'kids', 'beta',
              'business', 'premium', 'max', 'ultra'}
DEV_ALIASES = {'amzn': 'amazon'}


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def core(s):
    return norm(re.split(r'[:|\-–—]', (s or ''), maxsplit=1)[0])


def first_sig_token(s):
    for t in norm(s).split():
        if t not in STOPWORDS:
            return t
    return ''


def dev_tokens(d):
    return {DEV_ALIASES.get(t, t) for t in norm(d).split() if t not in DEV_GENERIC}


def dev_match(d1, d2):
    t1, t2 = dev_tokens(d1), dev_tokens(d2)
    if not t1 or not t2:
        return False
    if t1 & t2:
        return True
    for a in t1:
        for b in t2:
            if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
                return True
    return False


def main():
    play_csv, master_xlsx, out_csv = sys.argv[1:4]
    wb = openpyxl.load_workbook(master_xlsx, read_only=True, data_only=True)
    ws = wb['Master List']
    rows = list(ws.iter_rows(values_only=True))
    hdr = [h for h in rows[0]]
    ai, di = hdr.index('App'), hdr.index('Developer')
    ios = [(norm(r[ai]), core(r[ai]), r[ai], r[di] or '')
           for r in rows[1:] if r[ai]]
    ios_full = {n: (a, d) for n, c, a, d in ios}
    ios_core = {}
    for n, c, a, d in ios:
        ios_core.setdefault(c, []).append((a, d, n))

    play = list(csv.DictReader(open(play_csv)))
    out = []
    for p in play:
        n, c, dev = norm(p['app']), core(p['app']), p['developer']
        ptoks = set(n.split())
        if n in ios_full:
            status, cand, tier = 'on iOS', ios_full[n][0], 'A exact'
        else:
            hit = [x for x in ios_core.get(c, []) if dev_match(dev, x[1])]
            if hit:
                status, cand, tier = 'on iOS', hit[0][0], 'B core+dev'
            else:
                ct = set(c.split())
                hit2 = None
                for n2, c2, a2, d2 in ios:
                    if ct and ct <= set(n2.split()) and dev_match(dev, d2):
                        hit2 = a2
                        break
                if hit2:
                    status, cand, tier = 'on iOS', hit2, 'B2 subset+dev'
                else:
                    ft = first_sig_token(p['app'])
                    q = ptoks & QUALIFIERS
                    hit3 = None
                    if ft and ft not in GENERIC:
                        for n2, c2, a2, d2 in ios:
                            if first_sig_token(a2) == ft:
                                if q and not (q <= set(n2.split())):
                                    continue
                                if dev_match(dev, d2) or len(ft) >= 7:
                                    hit3 = a2
                                    break
                    if hit3:
                        status, cand, tier = 'on iOS', hit3, 'C first-token'
                    else:
                        status, cand, tier = 'NOT on iOS', '', ''
        out.append({**p, 'ios_status': status, 'ios_candidate': cand, 'tier': tier})

    from collections import Counter
    print(Counter((o['ios_status'], o['tier']) for o in out))
    for o in out:
        if o['tier'] in ('B2 subset+dev', 'C first-token'):
            print(f"  {o['tier']}: Play #{o['rank']:>3} {o['app']} -> iOS: {o['ios_candidate']}")
    not_on = [o for o in out if o['ios_status'] == 'NOT on iOS']
    print(f"NOT on iOS: {len(not_on)} of {len(out)}")
    fields = ['rank', 'app', 'developer', 'package', 'rating', 'installs',
              'recent_installs', 'ios_status', 'ios_candidate']
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for o in out:
            if o['ios_status'] != 'on iOS':
                w.writerow({k: o[k] for k in fields})
    print(f"wrote {out_csv}")


if __name__ == '__main__':
    main()
