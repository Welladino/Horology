# Implementation Note

## Topic
- cloud-build-global-free-tier

## Context
- The October billing report for `horology-dev` showed $0.47 for Cloud Build after about 62 build-minutes, far below the 2,500 free minutes. No other project on the billing account ran builds.
- The two Cloud Build lines were "E2 cpu utilization per minute in us-central1" (`0355-DA9A-4819`) and "E2 ram utilization per minute in us-central1" (`8A12-AC87-3E70`), with no free-tier savings applied. Cloud Run's free tier did appear as a saving on the same bill.

## Decision
- Submit Cloud Build releases to the global endpoint (no `--region`). `cloudbuild.yaml` is unchanged: it keeps `machineType: E2_STANDARD_2` and `logging: CLOUD_LOGGING_ONLY` (required with the custom `mcp-build` service account).

## Rationale
- The Cloud Billing catalog for Cloud Build (service `8B5D-EF7D-EB12`, read 2026-10-13) has exactly one SKU with a free first tier: "Build time e2-standard-2" (`A464-9020-6404`), region `global`, $0 for the first 2,500 minutes and $0.006 after.
- Regional us-central1 builds use the CPU/RAM SKUs ($0.0016 per vCPU-minute and $0.00035 per GiB-minute from minute 0, which equals $0.006 a minute for 2 vCPUs and 8 GiB).
- The explicit machine type is not the cause. Mapping the global e2-standard-2 build to the free SKU is inferred from the catalog and to be confirmed on the bill.

## Impact
- Cost: same per-minute price above the free tier; up to 2,500 minutes a month at $0.
- The image registry, source bucket and identity are unchanged. An organisation policy restricting build locations could refuse global builds; if so, restore `--region=us-central1`.

## Follow-Ups
- After the first global build, confirm in Billing → Reports (one-day lag) that it appears as "Build time e2-standard-2" with the free tier applied.
