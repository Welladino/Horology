/* One-way updates to manually linked ClickUp tasks. */
const SYNC_CONFIG = {
  PILOT_PIPELINE_IDS: [], // Optional temporary scope, e.g. ['37'].
  MAX_ITEMS_PER_RUN: 50,
  ENABLE_WRITES: true,
  SYNC_ALL: true, // true + empty pilot IDs considers every linked Pipeline row.
  CHANGE_SETTLE_SECONDS: 30, // onChange waits this long for further edits before syncing.
  CHANGE_LOCK_WAIT_SECONDS: 120, // and up to this long for a running sync to finish.
  WORKSPACE_URL: 'https://script.google.com/a/macros/welladino.com/s/AKfycbxNK7mEVHiTBH-X_Upl8dOYA5sD6ATfEWCnyHrw8u5_fZzxyQuCMm4maiHUn1qJGD4Z2A/exec'
};
const STATUS_MAP = {inbox:'backlogs', parked:'blocked', researching:'open',
  'awaiting decision':'review', approved:'open', rework:'backlogs',
  rejected:'rejected'};
// Completed still posts notebook updates; the founder closes the ClickUp task.
const COMMENT_ONLY_STATUSES = {completed:true};

function config() {
  const p = Object.assign({}, SYNC_CONFIG);
  p.CLICKUP_TOKEN = PropertiesService.getScriptProperties().getProperty('CLICKUP_TOKEN');
  if (!p.CLICKUP_TOKEN) throw Error('Set CLICKUP_TOKEN in Script Properties.');
  p.ids = SYNC_CONFIG.PILOT_PIPELINE_IDS.map(x=>String(x).trim()).filter(Boolean);
  if (!p.ids.length && !SYNC_CONFIG.SYNC_ALL) throw Error('Set PILOT_PIPELINE_IDS in Config.js first.');
  Object.assign(p, sheetIds());
  p.max = Math.min(50, Math.max(1, Number(SYNC_CONFIG.MAX_ITEMS_PER_RUN)));
  if (!Number.isInteger(p.max)) throw Error('Invalid MAX_ITEMS_PER_RUN.');
  return p;
}
