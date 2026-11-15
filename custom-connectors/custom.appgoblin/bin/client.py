#!/usr/bin/env python3
"""AppGoblin REST client for the registered custom.appgoblin connection.

Calls only appgoblin.info with the stored API key, placed in the
Authorization Bearer header by the authd surrogate exchange. Commands are
fixed; no arbitrary paths. Error responses are printed and exit non-zero.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import DynamicCredentialError, add_surrogate_to_request


PROVIDER = "custom.appgoblin"
BASE = "https://appgoblin.info"
HOST = "appgoblin.info"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class AppGoblinError(RuntimeError):
    """A transport or provider failure with no automatic replay."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AppGoblinError("AppGoblin endpoint redirected; verify the endpoint before continuing")


def call(path):
    request = urllib.request.Request(
        BASE + path, headers={"User-Agent": UA, "Accept": "application/json"}, method="GET"
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
        raise AppGoblinError(f"AppGoblin returned HTTP {error.code}: {json.dumps(payload)}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise AppGoblinError(f"AppGoblin request did not complete: {error}") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    ranks = subparsers.add_parser("ranks", help="GET /api/v1/apps/{store_id}/ranks")
    ranks.add_argument("store_id", help="Apple App ID, e.g. 906698760")
    app = subparsers.add_parser("app", help="GET /api/v1/apps/{store_id}")
    app.add_argument("store_id")
    sdks = subparsers.add_parser("sdks", help="GET /api/v1/apps/{store_id}/sdks")
    sdks.add_argument("store_id")
    subparsers.add_parser("companies", help="GET /api/v1/companies")
    args = parser.parse_args()
    if args.command == "ranks":
        result = call(f"/api/v1/apps/{args.store_id}/ranks")
    elif args.command == "sdks":
        result = call(f"/api/v1/apps/{args.store_id}/sdks")
    elif args.command == "companies":
        result = call("/api/v1/companies")
    else:
        result = call(f"/api/v1/apps/{args.store_id}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppGoblinError, DynamicCredentialError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
