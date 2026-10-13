-- Horology tool latency, one row per tool call (Log Analytics, last 24 hours).
-- Server time comes from Cloud Run's request log; caller-to-Iowa network time is not visible here.
WITH tools AS (
  SELECT
    timestamp,
    JSON_VALUE(resource.labels.service_name) AS service,
    JSON_VALUE(labels.instanceId) AS instance,
    JSON_VALUE(json_payload.tool) AS tool,
    JSON_VALUE(json_payload.outcome) AS outcome,
    JSON_VALUE(json_payload.error_category) AS error_category,
    SAFE_CAST(JSON_VALUE(json_payload.duration_ms) AS FLOAT64) AS tool_ms,
    JSON_VALUE(json_payload.trace_id) AS trace_id
  FROM `horology-dev.global._Default._Default`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND resource.type = 'cloud_run_revision'
    AND JSON_VALUE(json_payload.event) = 'runtime_operation'
),
requests AS (
  SELECT
    REGEXP_EXTRACT(trace, r'/traces/([0-9a-f]{32})$') AS trace_id,
    IFNULL(http_request.latency.seconds, 0) * 1000 + IFNULL(http_request.latency.nanos, 0) / 1e6 AS server_ms
  FROM `horology-dev.global._Default._Default`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 25 HOUR)
    AND log_id = 'run.googleapis.com/requests'
),
starts AS (
  SELECT JSON_VALUE(resource.labels.service_name) AS service, timestamp AS started
  FROM `horology-dev.global._Default._Default`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 25 HOUR)
    AND resource.type = 'cloud_run_revision'
    AND text_payload LIKE 'Starting new instance%'
),
joined AS (
  SELECT
    t.*,
    r.server_ms,
    ROW_NUMBER() OVER (PARTITION BY t.instance ORDER BY t.timestamp) = 1 AS first_on_instance,
    EXISTS (
      SELECT 1 FROM starts s
      WHERE s.service = t.service
        AND s.started BETWEEN TIMESTAMP_SUB(t.timestamp, INTERVAL 60 SECOND) AND t.timestamp
    ) AS cold_start
  FROM tools t
  LEFT JOIN requests r USING (trace_id)
)
SELECT
  FORMAT_TIMESTAMP('%F %T', timestamp, 'Asia/Singapore') AS time_sgt,
  service,
  tool,
  ROUND(server_ms) AS total_ms,
  ROUND(tool_ms) AS in_our_code_ms,
  ROUND(server_ms - tool_ms) AS other_ms,
  CASE
    WHEN outcome = 'error' THEN CONCAT('Error: ', IFNULL(error_category, 'unknown'))
    WHEN server_ms IS NULL THEN 'No matching request log (no trace id on this call)'
    WHEN cold_start AND first_on_instance THEN 'Cold start: new instance and new database connections'
    WHEN first_on_instance THEN 'First call on this instance: may open new connections'
    WHEN tool_ms >= 0.7 * server_ms THEN 'Mostly our code: database or provider calls'
    ELSE 'Mostly outside our code: sign-in check and MCP handling'
  END AS why
FROM joined
ORDER BY timestamp DESC
LIMIT 200
