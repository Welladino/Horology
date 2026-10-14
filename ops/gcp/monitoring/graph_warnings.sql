-- Document graph warnings and errors over 7 days (Log Analytics): failed rows and documents,
-- topic placement, AI retries. The message carries a safe error category, never document text.
SELECT
  FORMAT_TIMESTAMP('%F %T', timestamp, 'Asia/Singapore') AS time_sgt,
  IFNULL(JSON_VALUE(resource.labels.job_name), JSON_VALUE(resource.labels.service_name)) AS source,
  severity,
  JSON_VALUE(json_payload.logger) AS logger,
  JSON_VALUE(json_payload.message) AS message
FROM `horology-dev.global._Default._Default`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND resource.type IN ('cloud_run_job', 'cloud_run_revision')
  AND severity IN ('WARNING', 'ERROR')
  AND JSON_VALUE(json_payload.logger) IS NOT NULL
ORDER BY timestamp DESC
LIMIT 500
