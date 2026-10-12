# Public HTTPS scraping and JSON permission ownership

Date: 2026-10-13

The operator authorized Firecrawl single-page scraping of any public HTTPS URL rather than an exact allowlist. Added reusable URL/address validation to `shared-runtime/horology_runtime/urls.py`, independent of gateway policy. The gateway wraps its UnsafeURL exception as Denied. Localhost/internal names, non-global and multicast IPs, IPv4/IPv6 private/link-local targets, embedded private IPv4, invalid ports, userinfo, whitespace and fragments are denied. Every locally resolved address must be public. Legitimate public 172.x and 169.x addresses are not blocked just because of their first octet; private 172.16/12 and link-local 169.254/16 are denied.

Firecrawl now checks JSON `firecrawl.url_policy=public_https`, then URL validity, credential availability, quotas and cache. It retains one-page markdown/basic-proxy execution, output limits and no automatic retries. Tavily's exact URL policy remains. No paid call was made. Local DNS checking does not control Firecrawl's own DNS/redirect behavior.

JSON remains the source of permissions and resource scopes. Agent Register access IDs are documentation/status metadata, not authorization inputs. No spreadsheet-to-code mapping was introduced. Identity expiry and session boundaries were discussed but not changed; quotas still count across the persistent assignment.

Cloud Build/deployment/commit remain deferred by operator instruction.
