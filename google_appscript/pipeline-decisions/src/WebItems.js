/* Add Pipeline items from the private review web page. Uses the same field and
 * validation rules as the older workbook dialog.
 */

function getPipelineFormData() {
  const book = SpreadsheetApp.openById(DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID);
  const domains = book.getSheetByName('Domains');
  const master = book.getSheetByName('Master');
  if (!domains || !master) throw Error('The Pipeline needs Domains and Master tabs.');
  return {
    domains: domainMap(domains.getDataRange().getDisplayValues()),
    options: webMasterOptions(master)
  };
}

// Read-only overview for the workspace's Pipeline tab. Every non-empty Master
// ID is included; browsing an item does not change its stage or agent status.
function getPipelineOverview() {
  const id = DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID;
  const table = readMaster(id, ['ID', 'Title', 'Domain', 'Entity', 'Type', 'Status', 'Stage',
    'Agent status', 'Agent type', 'Run location', 'Summary / Why',
    'Next step / Research question', 'Revisit trigger']);
  const sheetId = table.sheet.getSheetId();
  const stepRows = readTab(id, 'Steps', ['Pipeline ID', 'Step', 'Task']);
  const fields = ['ID', 'Title', 'Domain', 'Entity', 'Type', 'Status', 'Stage',
    'Review stage', 'Agent status', 'Agent type', 'Run location',
    'Summary / Why', 'Next step / Research question', 'Revisit trigger',
    'Current decision ID', 'Link type', 'URL', 'GitHub branch',
    'ClickUp Pipeline URL', 'Created', 'Updated'];
  return table.rows.map(row => {
    const item = {route: itemRoute(row.data.Type), readyStatuses: readyStatuses(row.data.Type), sheetUrl: 'https://docs.google.com/spreadsheets/d/' + id +
      '/edit#gid=' + sheetId + '&range=A' + row.row};
    fields.forEach(field => { item[field] = String(row.data[field] || ''); });
    item.version = pipelineEditVersion(row.data);
    // Steps-tab rows only: an older numbered Next step is already shown as the Next step text.
    item.steps = plannedSteps(row.data.ID, stepRows, '');
    return item;
  });
}

const PIPELINE_EDIT_FIELDS = ['Title', 'Type', 'Summary / Why',
  'Next step / Research question', 'Revisit trigger', 'Agent status',
  'Agent type', 'Run location'];
const PIPELINE_VERSION_FIELDS = ['ID', 'Domain', 'Entity', 'Status', 'Stage',
  'Updated', ...PIPELINE_EDIT_FIELDS];

function pipelineEditVersion(data) {
  return JSON.stringify(PIPELINE_VERSION_FIELDS.map(key => String(data[key] || '')));
}

function updatePipelineItemFromWeb(request) {
  if (!DECISIONS_CONFIG.ENABLE_WRITES) throw Error('Pipeline writes are disabled.');
  const input = request && typeof request === 'object' ? request : {};
  const id = String(input.pipelineId || '').trim();
  const fields = input.fields && typeof input.fields === 'object' ? input.fields : {};
  if (!id) throw Error('Choose a Pipeline item.');
  const extra = Object.keys(fields).filter(key => !PIPELINE_EDIT_FIELDS.includes(key));
  if (extra.length) throw Error('These fields cannot be edited here: ' + extra.join(', '));
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw Error('Another Pipeline change is in progress. Try again in a moment.');
  try {
    const table = readMaster(DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID,
      ['ID', 'Title', 'Domain', 'Entity', 'Type', 'Status', 'Stage', 'Agent status',
        'Agent type', 'Run location', 'Summary / Why', 'Next step / Research question',
        'Revisit trigger', 'Updated']);
    const row = uniqueRow(table, 'ID', id);
    if (input.version !== pipelineEditVersion(row.data))
      throw Error('This Pipeline item changed since you opened it. Refresh before saving.');
    const next = {};
    PIPELINE_EDIT_FIELDS.forEach(key => {
      const value = fields[key];
      next[key] = String(value == null ? row.data[key] || '' : value).trim();
    });
    const errors = [];
    for (const pair of [['Title',240],['Summary / Why',4000],
      ['Next step / Research question',4000],['Revisit trigger',2000]]) {
      if (next[pair[0]].length > pair[1]) errors.push(pair[0] + ' is too long.');
    }
    if (!next.Title) errors.push('Give the item a title.');
    if (!next['Agent status']) errors.push('Choose an Agent status.');
    if (!next['Agent type']) errors.push('Choose an Agent type.');
    const options = webMasterOptions(table.sheet);
    for (const key of ['Type', 'Agent status', 'Agent type', 'Run location']) {
      if (next[key] && options[key].length && !options[key].includes(next[key]))
        errors.push(key + ' must be one of: ' + options[key].join(', ') + '.');
    }
    const before = String(row.data['Agent status'] || 'No action').trim();
    const after = next['Agent status'] || 'No action';
    const status = String(row.data.Status || '').trim();
    if (before !== after) {
      const eligible = readyStatuses(next.Type).includes(status);
      const allowed = eligible && ((before === 'No action' && ['Plan', 'Ready'].includes(after)) ||
        (before === 'Plan' && after === 'Ready'));
      if (!allowed) errors.push('This Agent status change is not allowed from the item’s current state.');
    }
    if (after === 'Ready') {
      if (!['Claude Code', 'Codex'].includes(next['Agent type']))
        errors.push('A Ready item needs Agent type Claude Code or Codex.');
      if (!next['Next step / Research question'])
        errors.push('A Ready item needs a Next step / Research question.');
      if (!next['Run location']) errors.push('A Ready item needs a Run location.');
      if (!['Stage 1', 'Stage 3'].includes(String(row.data.Stage)) &&
          !(status === 'Inbox' && String(row.data.Stage) === 'Stage 0'))
        errors.push('This item cannot be made Ready at its current Stage.');
    }
    if (errors.length) throw Error(errors.join(' '));
    const stage = after === 'Ready' && before !== 'Ready' && status === 'Inbox' &&
      String(row.data.Stage) === 'Stage 0' ? 'Stage 1' : String(row.data.Stage);
    let changed = false;
    PIPELINE_EDIT_FIELDS.forEach(key => {
      if (next[key] !== String(row.data[key] || '')) {
        write(table, row, key, next[key]); changed = true;
      }
    });
    if (stage !== String(row.data.Stage)) {
      write(table, row, 'Stage', stage); changed = true;
    }
    if (changed) write(table, row, 'Updated', today());
    return {saved: true, changed, id, stage};
  } finally {
    lock.releaseLock();
  }
}

function webMasterOptions(sheet) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn())
    .getDisplayValues()[0].map(h => String(h).trim());
  const out = {};
  Object.keys(ITEM_OPTIONS).forEach(key => {
    const col = headers.indexOf(key);
    let list = [];
    if (col >= 0) {
      const rule = sheet.getRange(2, col + 1).getDataValidation();
      if (rule && rule.getCriteriaType() === SpreadsheetApp.DataValidationCriteria.VALUE_IN_LIST)
        list = rule.getCriteriaValues()[0];
    }
    out[key] = list.length ? list.map(String) : ITEM_OPTIONS[key];
  });
  return out;
}

function addPipelineItemFromWeb(form) {
  if (!DECISIONS_CONFIG.ENABLE_WRITES) throw Error('Pipeline writes are disabled.');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw Error('Another Pipeline change is in progress. Try again in a moment.');
  try {
    const book = SpreadsheetApp.openById(DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID);
    const sheet = book.getSheetByName('Master');
    if (!sheet) throw Error('The Pipeline has no Master tab.');
    const data = getPipelineFormData();
    const rows = sheet.getDataRange().getValues();
    const headers = rows[0].map(h => String(h).trim());
    const idCol = headers.indexOf('ID');
    if (idCol < 0) throw Error('Master has no ID column.');
    const input = form && typeof form === 'object' ? form : {};
    const result = itemValues(input, data.domains, data.options,
      rows.slice(1).map(row => row[idCol]), today());
    if (result.errors.length) throw Error(result.errors.join(' '));
    let last = rows.length;
    while (last > 1 && !String(rows[last - 1][idCol]).trim()) last--;
    sheet.getRange(last + 1, 1, 1, headers.length)
      .setValues([itemRow(headers, result.values)]);
    return {id: result.values.ID, row: last + 1, title: result.values.Title,
      stage: result.values.Stage, status: result.values.Status};
  } finally {
    lock.releaseLock();
  }
}
