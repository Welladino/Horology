/* Entry points: apply decided Decision Register rows to their Pipeline items. */

function previewDecisions() { return run(false); }

function applyDecisions() { return run(DECISIONS_CONFIG.ENABLE_WRITES); }

function run(live) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) { console.log('Another run is in progress.'); return []; }
  try {
    const ids = registerIds();
    const pipeline = readMaster(ids.PIPELINE_ID, ['ID', 'Status', 'Stage', 'Review stage', 'Agent status', 'Agent type', 'Current decision ID']);
    const register = readMaster(ids.DECISIONS_ID, ['Decision ID', 'Pipeline ID', 'Status', 'Review stage', 'Rework instructions']);
    const decisions = register.rows.map(r => r.data);
    const out = [];
    pipeline.rows.forEach(row => {
      const result = decide(row.data, decisions);
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
  const sheet = SpreadsheetApp.openById(spreadsheetId).getSheetByName('Master');
  if (!sheet) throw Error('Missing Master tab in ' + spreadsheetId);
  const values = sheet.getDataRange().getDisplayValues();
  const headers = values[0].map(h => String(h).trim());
  required.forEach(h => { if (!headers.includes(h)) throw Error('Missing column ' + h + ' in ' + spreadsheetId); });
  const rows = values.slice(1).map((v, i) => ({row: i + 2, data: Object.fromEntries(headers.map((h, j) => [h, v[j] || '']))}))
    .filter(r => String(r.data[headers[0]]).trim());
  return {sheet, headers, rows};
}

function write(table, row, header, value) {
  table.sheet.getRange(row.row, table.headers.indexOf(header) + 1).setValue(value);
  row.data[header] = String(value);
}

function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}
