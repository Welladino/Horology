/* Settings. The web page needs an explicit Pipeline ID because there is no active
 * spreadsheet UI in a web-app request. A copied workbook needs this ID updated
 * before its own web-app deployment. The Decision Register still comes from Registers.
 */

const DECISIONS_CONFIG = {
  ENABLE_WRITES: true, // false makes applyDecisions behave like previewDecisions.
  CHECK_EVERY_MINUTES: 10, // Time trigger interval: 1, 5, 10, 15 or 30.
  // The bound workbook is not active when this project serves a web page.
  WEB_PIPELINE_SHEET_ID: '1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI',
  WEB_APP_URL: 'https://script.google.com/a/macros/welladino.com/s/AKfycbz3M-ONEZF3ox378oBdoecMb0wV7WdJNZX0jQgrq7NAEDqRZbs0OVCuYPgob7qrPWrr2Q/exec'
};
