#!/usr/bin/env python3
"""Run strict Clay people searches for ranks 26-50, sequentially, one batch at a time.

Writes raw MCP output per batch to clay-batch-<n>-ranks51-75-2026-11-13.json
and prints a compact summary (name | title | company | linkedin) per person found.
"""
import json, subprocess, sys, time
from pathlib import Path

CLIENT = "/home/hatch/workspace/custom-connectors/custom.clay/bin/client.py"
OUT = Path("/home/hatch/workspace/appcharts")
DSL = (
    'select from people where experiences.any(is_current = true '
    'and seniority in ("VP", "Director", "Head", "Manager", "Senior") '
    'and job_title is_similar_to ("Head of Growth", "VP Growth", "Director of Growth", '
    '"Growth Marketing Manager", "Head of Performance Marketing", "Performance Marketing Manager", '
    '"Head of User Acquisition", "User Acquisition Manager", "Head of Paid Media", '
    '"Director of Performance Marketing", "Director of User Acquisition", '
    '"VP Performance Marketing", "VP User Acquisition", "App Growth Manager", '
    '"Head of App Growth", "Growth Marketing Director", "Performance Marketing Lead", '
    '"User Acquisition Lead", "Chief Growth Officer", "Director of Growth Marketing")) '
    'limit 5 by clay_company_id'
)
BATCHES = [
    ["discord.com", "thebiblechat.com", "uber.com"],
    ["ticketmaster.com", "life360.com", "onepay.com"],
    ["netflix.com", "reelshort.com", "epic.com"],
    ["mcdonalds.com", "pinterest.com", "reddit.com"],
    ["zoom.com", "venmo.com", "target.com"],
    ["snapchat.com", "codeway.co", "canva.com"],
    ["yap.app", "t-mobile.com", "duolingo.com"],
    ["airbnb.com"],
]
def extract_people(payload):
    """Pull person dicts out of an MCP tools/call result, tolerating shape differences."""
    result = payload.get("result", payload)
    texts = []
    if isinstance(result, dict) and "content" in result:
        for item in result["content"]:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
    elif isinstance(result, str):
        texts.append(result)
    people = []
    for text in texts:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            for key in ("results", "people", "contacts", "items", "data"):
                if isinstance(data.get(key), list):
                    people.extend(data[key])
                    break
            else:
                if "full_name" in data or "name" in data:
                    people.append(data)
        elif isinstance(data, list):
            people.extend(data)
    return people

def compact(person):
    name = person.get("name") or person.get("full_name") or "?"
    title = person.get("latest_experience_title") or person.get("current_job_title") or person.get("job_title") or "?"
    company = person.get("latest_experience_company") or person.get("company_name") or person.get("company") or "?"
    li = person.get("url") or person.get("linkedin_url") or ""
    return f"{name} | {title} | {company} | {li}"

all_people = []
for i, batch in enumerate(BATCHES, 1):
    args = {"companyIdentifiers": batch, "companyTenure": "current", "dslQuery": DSL}
    args_file = OUT / f"clay-args-batch{i}.json"
    args_file.write_text(json.dumps(args))
    print(f"\n=== batch {i}: {', '.join(batch)} ===", flush=True)
    proc = subprocess.run(
        ["python3", CLIENT, "call-tool", "--name", "search-contacts",
         "--arguments-file", str(args_file)],
        capture_output=True, text=True, timeout=120)
    raw_file = OUT / f"clay-batch-{i}-ranks51-75-2026-11-13.json"
    raw_file.write_text(proc.stdout)
    if proc.returncode != 0:
        print(f"ERROR rc={proc.returncode}: {proc.stderr.strip()[:500]}", flush=True)
        print("raw saved to", raw_file, flush=True)
        time.sleep(20)
        continue
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("ERROR: output was not JSON; raw saved to", raw_file, flush=True)
        time.sleep(20)
        continue
    people = extract_people(payload)
    print(f"found {len(people)} people", flush=True)
    for p in people:
        print("  " + compact(p), flush=True)
        all_people.append(p)
    if i < len(BATCHES):
        time.sleep(8)

OUT.joinpath("clay-people-ranks51-75-raw.json").write_text(json.dumps(all_people, indent=2))
print(f"\nTOTAL compact people across batches: {len(all_people)}")
