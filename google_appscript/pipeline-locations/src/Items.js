/* The Add Pipeline item sidebar: reads the Domains tab and Master's dropdowns, and
 * writes one new row to Master below the last item.
 */

function showItemForm() {
  const page = HtmlService.createTemplateFromFile('ItemForm');
  page.data = safeJson(itemFormData());
  SpreadsheetApp.getUi().showSidebar(page.evaluate().setTitle('Add Pipeline item'));
}

function itemFormData() {
  const book = SpreadsheetApp.getActiveSpreadsheet();
  const domains = book.getSheetByName('Domains');
  if (!domains) throw Error('There is no Domains tab.');
  return {domains: domainMap(domains.getDataRange().getDisplayValues()), options: masterOptions(masterSheet())};
}

function addPipelineItem(form) {
  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(10000)) throw Error('Another change to the Pipeline is in progress. Try again in a moment.');
  try {
    const sheet = masterSheet(), data = itemFormData();
    const values = sheet.getDataRange().getValues();
    const headers = values[0].map(h => String(h).trim());
    const idCol = headers.indexOf('ID');
    if (idCol < 0) throw Error('Master has no ID column.');
    const result = itemValues(form, data.domains, data.options, values.slice(1).map(r => r[idCol]), today());
    if (result.errors.length) throw Error(result.errors.join(' '));
    let last = values.length;
    while (last > 1 && !String(values[last - 1][idCol]).trim()) last--;
    sheet.getRange(last + 1, 1, 1, headers.length).setValues([itemRow(headers, result.values)]);
    return {id: result.values.ID, row: last + 1};
  } finally { lock.releaseLock(); }
}

function masterSheet() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Master');
  if (!sheet) throw Error('There is no Master tab.');
  return sheet;
}

// Each dropdown field's choices from Master's own validation, falling back to the defaults.
function masterOptions(sheet) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getDisplayValues()[0].map(h => String(h).trim());
  const out = {};
  Object.keys(ITEM_OPTIONS).forEach(k => {
    const col = headers.indexOf(k);
    let list = [];
    if (col >= 0) {
      const rule = sheet.getRange(2, col + 1).getDataValidation();
      if (rule && rule.getCriteriaType() === SpreadsheetApp.DataValidationCriteria.VALUE_IN_LIST) list = rule.getCriteriaValues()[0];
    }
    out[k] = list.length ? list.map(String) : ITEM_OPTIONS[k];
  });
  return out;
}

function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}
