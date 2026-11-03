/* Entry points: apply decided Decision Register rows to their Pipeline items. */

function previewDecisions() { return run(false); }

function applyDecisions(onlyDecisionId) { return run(DECISIONS_CONFIG.ENABLE_WRITES, onlyDecisionId); }

function run(live, onlyDecisionId) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) { console.log('Another run is in progress.'); return []; }
  try {
    const ids = registerIds();
    const pipeline = readMaster(ids.PIPELINE_ID, ['ID', 'Status', 'Stage', 'Review stage', 'Agent status', 'Agent type', 'Current decision ID']);
    const register = readMaster(ids.DECISIONS_ID, ['Decision ID', 'Pipeline ID', 'Status', 'Review stage', 'Rework instructions']);
    const decisions = register.rows.map(r => r.data);
    const out = [];
    pipeline.rows.forEach(row => {
      if (onlyDecisionId && String(row.data['Current decision ID']).trim() !== String(onlyDecisionId).trim()) return;
      const result = decide(row.data, decisions);
      // A decision saved from the web page that changes nothing (accepting a Completed Stage 4
      // deliverable) is reported as applied, so the page doesn't call it pending.
      if (result.skip && onlyDecisionId && result.decision)
        out.push({pipelineId: row.data['ID'], decision: result.decision, transition: result.transition, set: {}, applied: live});
      if (result.skip) return;
      if (result.error) { out.push({pipelineId: row.data['ID'], error: result.error}); return; }
      out.push({pipelineId: row.data['ID'], decision: result.decision, transition: result.transition, set: result.set, applied: live});
      if (!live) return;
      Object.keys(result.set).forEach(h => write(pipeline, row, h, result.set[h]));
      if (pipeline.headers.includes('Updated')) write(pipeline, row, 'Updated', today());
      const dr = register.rows.find(r => String(r.data['Decision ID']).trim() === result.decision);
      if (dr && register.headers.includes('Decision Date') && !String(dr.data['Decision Date'] || '').trim())
        write(register, dr, 'Decision Date', today());
    });
    console.log(JSON.stringify(out.length ? out : [{note: 'nothing to apply'}]));
    return out;
  } finally { lock.releaseLock(); }
}

function readMaster(spreadsheetId, required) {
  const sheet = openBook(spreadsheetId).getSheetByName('Master');
  if (!sheet) throw Error('Missing Master tab in ' + spreadsheetId);
  const values = sheet.getDataRange().getDisplayValues();
  const headers = values[0].map(h => String(h).trim());
  required.forEach(h => { if (!headers.includes(h)) throw Error('Missing column ' + h + ' in ' + spreadsheetId); });
  const rows = values.slice(1).map((v, i) => ({row: i + 2, data: Object.fromEntries(headers.map((h, j) => [h, v[j] || '']))}))
    .filter(r => String(r.data[headers[0]]).trim());
  // key: the permanent ID column (ID or Decision ID) that writes use to find their row.
  return {sheet, headers, rows, key: required[0]};
}

// Writes find their row by permanent ID immediately before writing, never by the position read
// earlier: a sort, insert or another writer may have moved rows since. Stops if the ID is gone or
// appears twice rather than writing into whichever row is now at the old position.
function write(table, row, header, value) {
  const col = table.headers.indexOf(header);
  if (col < 0) throw Error('Missing column ' + header);
  table.sheet.getRange(currentRow(table, row), col + 1).setValue(value);
  row.data[header] = String(value);
}

function currentRow(table, row) {
  const key = table.key || table.headers[0], col = table.headers.indexOf(key);
  const id = String(row.data[key]).trim();
  if (col < 0 || !id) throw Error('Rows are written by ' + key + '; this row has none.');
  const found = [];
  table.sheet.getDataRange().getDisplayValues().forEach((cells, i) => {
    if (i > 0 && String(cells[col]).trim() === id) found.push(i + 1);
  });
  if (found.length !== 1)
    throw Error(key + ' ' + id + (found.length ? ' appears ' + found.length + ' times' : ' is no longer in the sheet') +
      '; nothing was written. Fix the sheet and try again.');
  row.row = found[0];
  return row.row;
}

function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}
