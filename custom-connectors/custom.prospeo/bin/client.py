#!/usr/bin/env python3
"""Prospeo REST client for the registered custom.prospeo connection.

Calls only api.prospeo.io with the stored API key, placed in the X-KEY
header by the authd surrogate exchange. Commands are fixed; no arbitrary
paths. Error responses are printed with their error_code and exit non-zero.
"""

import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import DynamicCredentialError, add_surrogate_to_request


PROVIDER = "custom.prospeo"
BASE = "https://api.prospeo.io"
HOST = "api.prospeo.io"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class ProspeoError(RuntimeError):
    """A transport or provider failure with no automatic replay."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProspeoError("Prospeo endpoint redirected; verify the endpoint before continuing")


def call(path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    add_surrogate_to_request(request, PROVIDER, allowed_hosts=[HOST])
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        raise ProspeoError(f"Prospeo returned HTTP {error.code}: {json.dumps(payload)}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ProspeoError(f"Prospeo request did not complete: {error}") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("account", help="GET /account-information (free read)")

    search = subparsers.add_parser("search-person", help="POST /search-person, 1 credit per page of up to 25")
    search.add_argument("--website", required=True, help="company website, e.g. kalshi.com")
    search.add_argument("--page", type=int, default=1)

    enrich = subparsers.add_parser("enrich-person", help="POST /enrich-person, 1 credit per verified email")
    enrich.add_argument("--full-name", required=True)
    enrich.add_argument("--company-website", required=True)
    enrich.add_argument("--linkedin-url")
    enrich.add_argument("--no-verified-only", action="store_true", help="allow unverified emails")

    enrich_company = subparsers.add_parser("enrich-company", help="POST /enrich-company")
    enrich_company.add_argument("--company-website", required=True)

    search_company = subparsers.add_parser("search-company", help="POST /search-company, 1 credit per page of up to 25")
    search_company.add_argument("--name", required=True)
    search_company.add_argument("--page", type=int, default=1)

    args = parser.parse_args()
    if args.command == "account":
        result = call("/account-information")
    elif args.command == "search-person":
        result = call("/search-person", {
            "filters": {"company": {"websites": {"include": [args.website]}}},
            "page": args.page,
        })
    elif args.command == "enrich-person":
        data = {"full_name": args.full_name, "company_website": args.company_website}
        if args.linkedin_url:
            data["linkedin_url"] = args.linkedin_url
        result = call("/enrich-person", {
            "only_verified_email": not args.no_verified_only,
            "data": data,
        })
    elif args.command == "enrich-company":
        result = call("/enrich-company", {"data": {"company_website": args.company_website}})
    elif args.command == "search-company":
        result = call("/search-company", {
            "filters": {"name": args.name},
            "page": args.page,
        })
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ProspeoError, DynamicCredentialError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
