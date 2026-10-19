/* Settings. No secrets and no sheet IDs: the Pipeline is the workbook this script is
 * bound to, and the Decision Register link is read from its Registers tab, so a copy
 * of the workbook uses its own registers.
 */

const DECISIONS_CONFIG = {
  ENABLE_WRITES: true, // false makes applyDecisions behave like previewDecisions.
  CHECK_EVERY_MINUTES: 10 // Time trigger interval: 1, 5, 10, 15 or 30.
};
