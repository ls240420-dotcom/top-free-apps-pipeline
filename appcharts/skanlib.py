"""Shared SKAdNetwork registry + company normalisation for the enrichment
pipeline. Several IDs can belong to one company (Meta has two), and the
registries spell one company several ways (brand vs legal name, case,
rebrands), so names are folded to a canonical company before counting.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(_HERE, "skan-registry-2026-11-13.json")

# Known variants that rule-based stripping does not fold.
ALIASES = {
    "amazon advertising": "Amazon",
    "centro": "Basis",
    "applovin": "AppLovin",
    "liftoff monetize": "Liftoff",
    "mintegral / mobvista": "Mintegral",
    "ironsource ads": "ironSource",
    "unity ads": "Unity Ads",
    "yahoo japan ads": "Yahoo Japan",
    "adcolony": "AdColony",
    "adtiming technology": "AdTiming",
    "performcb": "Perform[cb]",
    "smn": "SMN",
    "bns": "BNS",
    "maas": "MaaS",
    "nend": "nend",
    "ai4see": "AI4See",
    "adspeq": "AdSpeq",
    "adtheorent": "AdTheorent",
    "applift": "AppLift",
}

_SUFFIXES = {
    "inc", "llc", "ltd", "gmbh", "pte", "s.l", "sl", "ag", "co", "corp",
    "corporation", "company", "limited", "s.a", "sa", "bv", "pty", "plc",
    "inc.", "llc.", "ltd.", "gmbh.", "cn",
}


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {}
    with open(REGISTRY_PATH) as f:
        return {k.lower(): v for k, v in json.load(f).items()}


def canonical_company(name):
    """Fold a registry name to one canonical company label."""
    n = name.strip().lower()
    n = re.sub(r"\.(io|com|net|ai|co)$", "", n)
    n = n.replace("-", " ")
    n = re.sub(r"[.,;:()\[\]]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    if n in ALIASES:
        return ALIASES[n]
    # Strip trailing legal suffixes, repeatedly.
    parts = n.split(" ")
    while len(parts) > 1 and parts[-1].rstrip(".") in _SUFFIXES:
        parts = parts[:-1]
    n = " ".join(parts)
    if n in ALIASES:
        return ALIASES[n]
    # Title-case, keeping known camelCase brands.
    return n.title()


def resolve(skadnetwork_ids, registry=None):
    """Return (names, companies, unresolved_n) for a list of SKAN IDs."""
    registry = registry if registry is not None else load_registry()
    names, unresolved = [], 0
    for s in skadnetwork_ids or []:
        name = registry.get(s.lower())
        if name:
            names.append(name)
        else:
            unresolved += 1
    companies = sorted({canonical_company(n) for n in names})
    return sorted(set(names)), companies, unresolved
