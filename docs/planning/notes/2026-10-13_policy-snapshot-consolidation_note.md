# Consolidate working policy and refresh deployed snapshot

Kept `policy.local.json` as the single working policy and removed `policy.expansion.local.json`. The expansion copy differed only by adding https://example.com/ to Tavily extraction URLs at global/shared scope; the current working permissions were preserved without widening them.

Read the Cloud Run service and its traffic: all traffic goes to mcp-gateway-00008-kqw. Its /config mount uses horology-gateway-policy:4 (an unused version-3 volume also remains in revision metadata). Downloaded version 4 directly from Secret Manager into ignored mode-0600 policy.cloud.json without modifying its contents. Recorded version, revision and SHA-256 in ignored policy.cloud.snapshot.local.json.

The deployed snapshot intentionally retains old assignment/disabled-access fields. Those describe the existing deployed code, while the working policy describes pending local changes. Previously the local cloud copy was stale because deployments and hand-maintained copies were not synchronized. Refresh the exact deployed snapshot after releases; do not treat working policy as deployed state.

No cloud mutation, build, deployment, migration or commit performed.
