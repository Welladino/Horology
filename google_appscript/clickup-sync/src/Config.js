/* Settings and status mapping. */

/* Settings that aren't per workspace live here. Apps Script files share one global
 * scope; create every supplied .gs file in the same project. No imports are needed.
 * Per workspace, in Script Properties: CLICKUP_TOKEN, PIPELINE_SHEET_ID, and one
 * LIST_<Domain> per domain mirrored to ClickUp (see Registers.js).
 */
const SYNC_CONFIG = {
  PILOT_PIPELINE_IDS: [], // Fill e.g. ['18']; start with one or two rows.
  MAX_ITEMS_PER_RUN: 5,
  ENABLE_WRITES: true, // Enable only after preview and schema setup.
  ALLOW_CLICKUP_REVIEW: true, // Review decisions from ClickUp; only for lists with trusted editors.
  ALLOW_ADOPT_EXISTING: false,
  SYNC_ALL: true // true + empty pilot IDs selects all rows.
};
const STATUS_MAP = {inbox:'backlogs', park:'blocked', parked:'blocked', researching:'open',
  'awaiting decision':'review', approved:'open', rework:'backlogs',
  'hand off':'closed', 'handed off':'closed', reject:'rejected', rejected:'rejected'};

function config() {
  const p = Object.assign({}, SYNC_CONFIG);
  p.CLICKUP_TOKEN = PropertiesService.getScriptProperties().getProperty('CLICKUP_TOKEN');
  if (!p.CLICKUP_TOKEN) throw Error('Set CLICKUP_TOKEN in Script Properties.');
  p.ids = SYNC_CONFIG.PILOT_PIPELINE_IDS.map(x=>String(x).trim()).filter(Boolean);
  if (!p.ids.length && !SYNC_CONFIG.SYNC_ALL) throw Error('Set PILOT_PIPELINE_IDS in Config.gs first.');
  Object.assign(p, sheetIds());
  p.lists = domainLists(p.PIPELINE_SHEET_ID);
  p.max = Math.min(20, Math.max(1, Number(SYNC_CONFIG.MAX_ITEMS_PER_RUN)));
  if (!Number.isInteger(p.max)) throw Error('Invalid MAX_ITEMS_PER_RUN.');
  p.ALLOW_CLICKUP_REVIEW = String(SYNC_CONFIG.ALLOW_CLICKUP_REVIEW);
  p.ALLOW_ADOPT_EXISTING = String(SYNC_CONFIG.ALLOW_ADOPT_EXISTING);
  return p;
}
