"""Probe the Apollo MCP endpoint with the stored OAuth credential and print
the full error body, so a 403 can be diagnosed (insufficient_scope vs
API_INACCESSIBLE vs account restriction). Read-only: sends one initialize
request, no tool calls, no credits."""
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


body = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "probe", "version": "0"},
    },
}).encode()

request = urllib.request.Request(
    "https://mcp.apollo.io/mcp",
    data=body,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    },
    method="POST",
)
add_surrogate_to_request(request, "custom.apollo", allowed_hosts=["mcp.apollo.io"])
try:
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as resp:
        print("STATUS", resp.status)
        print(resp.read().decode()[:2000])
except urllib.error.HTTPError as e:
    print("STATUS", e.code)
    print(e.read().decode()[:2000])
