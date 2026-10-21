/* Resolve the Pipeline's linked registers. Each row's ClickUp task URL is the
 * task mapping; no domain-to-list mapping is needed. */

function sheetIds() {
  const id = PropertiesService.getScriptProperties().getProperty('PIPELINE_SHEET_ID');
  if (!id) throw Error('Set PIPELINE_SHEET_ID in Script Properties to the Pipeline workbook ID.');
  const tab = SpreadsheetApp.openById(id).getSheetByName('Registers');
  if (!tab) throw Error('The Pipeline has no Registers tab.');
  const values = tab.getDataRange().getDisplayValues();
  return {PIPELINE_SHEET_ID: id, DECISIONS_SHEET_ID: registerIdFrom(values, /decision register/i),
    DOCUMENT_INDEX_SHEET_ID: registerIdFrom(values, /document index/i)};
}

// The spreadsheet ID in the Location of the one Registers row whose Register name matches.
function registerIdFrom(values, pattern) {
  const headers = (values[0] || []).map(h => String(h).trim());
  const name = headers.indexOf('Register'), link = headers.indexOf('Location');
  if (name < 0 || link < 0) throw Error('The Registers tab needs Register and Location columns.');
  const hits = values.slice(1).filter(r => pattern.test(String(r[name])));
  if (hits.length !== 1) throw Error('The Registers tab needs exactly one row matching ' + pattern + '; found ' + hits.length + '.');
  const m = String(hits[0][link]).match(/\/spreadsheets\/d\/([\w-]+)/);
  if (!m) throw Error('The ' + hits[0][name] + ' row has no Google Sheets link.');
  return m[1];
}
