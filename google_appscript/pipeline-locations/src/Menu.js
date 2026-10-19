/* Entry points: the Extensions menu, the Add Pipeline item form (Items.js), the
 * folder view and the Drive check. Reads Drive and the workbook; writes new Master
 * rows, and Name and Parent cells in Locations. It never creates, moves or renames
 * anything in Drive.
 */

function onOpen() {
  SpreadsheetApp.getUi().createAddonMenu()
    .addItem('Add Pipeline item', 'showItemForm')
    .addSeparator()
    .addItem('Show folder structure', 'showFolders')
    .addItem('Check folders against Drive', 'checkFolders')
    .addToUi();
}

function showFolders() {
  const page = HtmlService.createTemplateFromFile('View');
  page.data = safeJson(buildTree(readLocations().rows.map(r => r.data)));
  SpreadsheetApp.getUi().showSidebar(page.evaluate().setTitle('Folder structure'));
}

// Opens the report at once; the report then calls runFolderCheck, so the dialog shows it's working.
function checkFolders() {
  const page = HtmlService.createTemplateFromFile('Report');
  page.count = readLocations().rows.length;
  SpreadsheetApp.getUi().showModalDialog(page.evaluate().setWidth(640).setHeight(520), 'Folders checked against Drive');
}

function runFolderCheck() {
  const table = readLocations();
  const rows = table.rows.map(r => r.data);
  const result = compareWithDrive(rows, driveAdapter(rows.map(r => folderId(r.Location)).filter(Boolean)));
  result.updates.forEach(u => {
    const row = table.rows[u.row];
    table.sheet.getRange(row.row, table.headers.indexOf(u.field) + 1).setValue(u.to);
  });
  return JSON.parse(JSON.stringify(result));
}

function readLocations() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Locations');
  if (!sheet) throw Error('There is no Locations tab.');
  const values = sheet.getDataRange().getDisplayValues();
  const headers = values[0].map(h => String(h).trim());
  LOCATION_HEADERS.forEach(h => { if (!headers.includes(h)) throw Error('Locations is missing the ' + h + ' column.'); });
  const rows = values.slice(1).map((v, i) => ({row: i + 2, data: Object.fromEntries(headers.map((h, j) => [h, v[j] || '']))}))
    .filter(r => String(r.data.Domain).trim());
  return {sheet, headers, rows};
}

/* Reads all listed folders and their subfolders in a few Drive API calls: one
 * query per batch of parents, then a lookup for any listed folder the queries
 * didn't return (root folders, and anything moved out).
 */
function driveAdapter(ids, api) {
  api = api || Drive;
  const opts = {supportsAllDrives: true, includeItemsFromAllDrives: true, corpora: 'allDrives', pageSize: 1000,
    fields: 'nextPageToken, files(id, name, parents, trashed)'};
  const info = {}, children = {};
  const add = f => {
    info[f.id] = {name: f.name, trashed: !!f.trashed, parentIds: f.parents || []};
    (f.parents || []).forEach(p => { if (!f.trashed) (children[p] = children[p] || []).push({id: f.id, name: f.name}); });
  };
  for (let i = 0; i < ids.length; i += 20) {
    const q = '(' + ids.slice(i, i + 20).map(id => "'" + id + "' in parents").join(' or ') + ") and mimeType = 'application/vnd.google-apps.folder'";
    let token;
    do {
      const page = api.Files.list(Object.assign({}, opts, {q: q, pageToken: token}));
      (page.files || []).forEach(add);
      token = page.nextPageToken;
    } while (token);
  }
  ids.filter(id => !info[id]).forEach(id => {
    try { add(api.Files.get(id, {supportsAllDrives: true, fields: 'id, name, parents, trashed'})); } catch (e) { info[id] = null; }
  });
  return {get: id => info[id] || null, children: id => children[id] || []};
}

// JSON for a <script> block in a template: escape '<' so data can't close the tag.
function safeJson(value) { return JSON.stringify(value).replace(/</g, '\\u003c'); }
