/* One-way updates to manually linked ClickUp tasks. */
const SYNC_CONFIG = {
  PILOT_PIPELINE_IDS: [], // Optional temporary scope, e.g. ['37'].
  MAX_ITEMS_PER_RUN: 50,
  ENABLE_WRITES: true,
  SYNC_ALL: true // true + empty pilot IDs considers every linked Pipeline row.
};
const STATUS_MAP = {inbox:'backlogs', park:'blocked', parked:'blocked', researching:'open',
  'awaiting decision':'review', approved:'open', rework:'backlogs',
  'hand off':'closed', 'handed off':'closed', reject:'rejected', rejected:'rejected'};

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
