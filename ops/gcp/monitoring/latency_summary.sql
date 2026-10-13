-- Horology tool latency summary per tool (Log Analytics, last 7 days).
-- Server time comes from Cloud Run's request log; caller-to-Iowa network time is not visible here.
WITH tools AS (
  SELECT
    JSON_VALUE(resource.labels.service_name) AS service,
    JSON_VALUE(json_payload.tool) AS tool,
    JSON_VALUE(json_payload.outcome) AS outcome,
    SAFE_CAST(JSON_VALUE(json_payload.duration_ms) AS FLOAT64) AS tool_ms,
    JSON_VALUE(json_payload.trace_id) AS trace_id
  FROM `horology-dev.global._Default._AllLogs`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND resource.type = 'cloud_run_revision'
    AND JSON_VALUE(json_payload.event) = 'runtime_operation'
),
requests AS (
  SELECT
    REGEXP_EXTRACT(trace, r'/traces/([0-9a-f]{32})$') AS trace_id,
    IFNULL(http_request.latency.seconds, 0) * 1000 + IFNULL(http_request.latency.nanos, 0) / 1e6 AS server_ms
  FROM `horology-dev.global._Default._AllLogs`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND log_id = 'run.googleapis.com/requests'
)
SELECT
  service,
  tool,
  COUNT(*) AS calls,
  COUNTIF(outcome = 'error') AS errors,
  ROUND(APPROX_QUANTILES(r.server_ms, 100)[OFFSET(50)]) AS typical_total_ms,
  ROUND(APPROX_QUANTILES(r.server_ms, 100)[OFFSET(95)]) AS slow_total_ms_p95,
  ROUND(MAX(r.server_ms)) AS slowest_total_ms,
  ROUND(APPROX_QUANTILES(t.tool_ms, 100)[OFFSET(50)]) AS typical_in_our_code_ms
FROM tools t
LEFT JOIN requests r USING (trace_id)
GROUP BY service, tool
ORDER BY calls DESC
