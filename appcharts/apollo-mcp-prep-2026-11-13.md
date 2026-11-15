# Apollo MCP prep — 2026-11-13

Context: Apollo REST API is closed on the Free plan (even with a master key);
the MCP server is the remaining route. Liam has not yet approved the MCP
connection (options widget sent 2026-11-13 08:45).

## Verified from live metadata (https://mcp.apollo.io/.well-known/oauth-protected-resource)
- resource: `https://mcp.apollo.io/mcp`
- authorization_servers: `["https://mcp.apollo.io"]`
- bearer_methods_supported: `["header"]`
- OpenID config (https://mcp.apollo.io/.well-known/openid-configuration, read 2026-11-13):
  - issuer: `https://mcp.apollo.io`
  - authorization_endpoint: `https://mcp.apollo.io/mcp/oauth_metadata/redirect_to_authorize`
  - token_endpoint: `https://mcp.apollo.io/api/v1/oauth/token`
  - registration_endpoint: `https://mcp.apollo.io/api/v1/oauth/applications/register_oauth_client` (dynamic client registration supported)
  - scopes include `mixed_people_api_search`, `people_match`
- Bare GET to https://mcp.apollo.io/mcp returns 405 (expected — needs MCP POST/session)

## Next steps once Liam approves
1. `credentials.request_api_access` with oauth2_code, provider `apollo`,
   resource `https://mcp.apollo.io/mcp`, issuer_domain `mcp.apollo.io`
   (get exact authorize/token URLs from the openid configuration first).
2. Scaffold connector docs, copy
   `/opt/muse/skills/custom-connector-setup/templates/mcp_client.py` to
   `~/workspace/custom-connectors/custom.apollo/bin/client.py`; set
   PROVIDER=`custom.apollo`, ENDPOINT=`https://mcp.apollo.io/mcp`.
3. `list-tools`, allowlist only the people-search tool first.
4. Test people search on 2–3 pilot companies (Kalshi kalshi.com, Vinted
   vinted.com, Whatnot whatnot.com) with titles Growth / Performance
   Marketing / User Acquisition / Paid Social. Search costs no credits.
   Do NOT run enrichment (credits) until search is proven.
5. Open questions the test settles: does Free-plan MCP search cover the
   full Apollo database, or only saved contacts? Is Liam's Apollo account
   on a work email (personal-email accounts can't search/enrich)?
