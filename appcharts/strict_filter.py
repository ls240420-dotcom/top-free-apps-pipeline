#!/usr/bin/env python3
"""Shared strict-buyer classifier for the prospecting pipeline.

Rule (set by Liam 2026-11-13): only people who actually buy performance CTV
ads. That means growth / performance marketing / user acquisition / paid media
titles. Everything else is out: B2B marketing, brand, content, product
marketing, partnerships, comms, analytics, generic marketing leadership
(CMO, VP Marketing, Head of Marketing), seller/supply-side growth, and
sell-side ads roles.
"""
import re

HARD_EXCLUDE = [
    r'\bpartner\b', r'engineer', r'data scien', r'\bdata\b', r'design', r'content',
    r'executive assistant', r'administrative assistant', r'\bassistant to\b',
    r'chief of staff',
    r'\bbrand\b', r'product marketing', r'product growth', r'growth product',
    r'growth analyt', r'communications', r'\bpr\b',
    r'public relations', r'demand generation', r'demand gen', r'lifecycle', r'\bcrm\b',
    r'retention', r'\bseo\b', r'\baso\b', r'field marketing', r'events', r'social media',
    r'organic', r'creator', r'affiliate', r'influencer', r'\bb2b\b', r'business marketing',
    r'business development', r'business growth', r'\bsmb\b', r'seller', r'operations',
    r'finance', r'legal',
    r'\bsales\b',
    # \bstrategy\b uses a word boundary so "Head of Growth Strategy" is not
    # excluded before the BUYER_RES patterns can fire (fix: was unanchored r'strategy').
    r'\bstrategy\b',
    r'\bcorporate\b', r'\benterprise\b', r'\bcloud\b', r'\bgtm\b',
    r'\bcampus\b', r'\bclient\b',
]
BUYER_RES = [
    r'growth marketing', r'head of growth', r'\bvp\b.{0,12}\bgrowth\b',
    r'\bsvp\b.{0,12}\bgrowth\b', r'senior vice president.{0,12}\bgrowth\b',
    r'\bevp\b.{0,12}\bgrowth\b', r'director.{0,10}\bgrowth\b',
    r'growth manager', r'growth lead', r'growth director', r'chief growth officer',
    r'chief growth', r'performance marketing', r'performance media', r'user acquisition',
    r'user aquisition',
    r'\bua manager\b', r'\bua lead\b', r'head of ua\b',
    r'paid media', r'paid acquisition', r'paid advertis', r'app growth', r'mobile growth',
]
GENERIC_EXCLUDE = [
    r'\bchief marketing officer\b', r'\bcmo\b', r'\bvp\b.{0,2}\bmarketing\b',
    r'\bhead of marketing\b', r'\bdirector of marketing\b', r'\bmarketing director\b',
    r'\bglobal marketing\b', r'\bregional marketing\b', r'\bmarketing manager\b',
    r'\bmarketing lead\b', r'\bmarketing head\b',
]


def classify(title):
    """Return ('include'|'exclude', reason)."""
    t = (title or '').lower()
    for pat in HARD_EXCLUDE:
        if re.search(pat, t):
            return ('exclude', 'non-buyer: ' + pat)
    for pat in BUYER_RES:
        if re.search(pat, t):
            return ('include', 'buyer: ' + pat)
    for pat in GENERIC_EXCLUDE:
        if re.search(pat, t):
            return ('exclude', 'generic mktg: ' + pat)
    return ('exclude', 'no buyer keyword')
