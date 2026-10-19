/* Where the two workbooks are: the Pipeline this script is bound to, and the
 * Decision Register named on the Pipeline's Registers tab.
 */

function registerIds() {
  const pipeline = SpreadsheetApp.getActiveSpreadsheet();
  const tab = pipeline.getSheetByName('Registers');
  if (!tab) throw Error('The Pipeline has no Registers tab.');
  return {PIPELINE_ID: pipeline.getId(), DECISIONS_ID: registerIdFrom(tab.getDataRange().getDisplayValues(), /decision register/i)};
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
