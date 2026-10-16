/* Settings. No secrets: the script only touches the two workbooks below. */

const DECISIONS_CONFIG = {
  PIPELINE_SHEET_ID: '1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI',
  DECISIONS_SHEET_ID: '1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE',
  ENABLE_WRITES: true, // false makes applyDecisions behave like previewDecisions.
  CHECK_EVERY_MINUTES: 10 // Time trigger interval: 1, 5, 10, 15 or 30.
};
