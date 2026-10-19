/* Where the registers and ClickUp lists are, so nothing about a workspace is in the code.
 * PIPELINE_SHEET_ID (Script Properties) names the Pipeline workbook; its Registers tab
 * links the Decision Register and Document Index, and its Domains tab lists the domains.
 * A domain is mirrored to ClickUp when Script Properties has LIST_<Domain> set to a list
 * ID, e.g. LIST_Horology = 901820246905. Several domains may point at the same list.
 */

function sheetIds() {
  const id = PropertiesService.getScriptProperties().getProperty('PIPELINE_SHEET_ID');
  if (!id) throw Error('Set PIPELINE_SHEET_ID in Script Properties to the Pipeline workbook ID.');
  const tab = SpreadsheetApp.openById(id).getSheetByName('Registers');
  if (!tab) throw Error('The Pipeline has no Registers tab.');
  const values = tab.getDataRange().getDisplayValues();
  return {PIPELINE_SHEET_ID: id, DECISIONS_SHEET_ID: registerIdFrom(values, /decision register/i),
    DOCUMENT_INDEX_SHEET_ID: registerIdFrom(values, /document index/i)};
}

// Domain -> ClickUp list ID, for the domains on the Domains tab that have a LIST_ property.
function domainLists(pipelineId) {
  const tab = SpreadsheetApp.openById(pipelineId).getSheetByName('Domains');
  if (!tab) throw Error('The Pipeline has no Domains tab.');
  const values = tab.getDataRange().getDisplayValues(), col = values[0].map(h => String(h).trim()).indexOf('Domain');
  if (col < 0) throw Error('The Domains tab has no Domain column.');
  const props = PropertiesService.getScriptProperties(), lists = {};
  values.slice(1).map(r => String(r[col]).trim()).filter(Boolean).forEach(d => {
    const list = String(props.getProperty('LIST_' + d) || '').trim();
    if (list) lists[d] = list;
  });
  return lists;
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
