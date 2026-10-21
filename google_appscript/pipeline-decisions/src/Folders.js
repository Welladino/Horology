/* Folder tree and explicit Drive check for the Horology web workspace.
 * Locations remains the source of record. The check updates only Name and Parent.
 */

function readFolderLocations() {
  const book = SpreadsheetApp.openById(DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID);
  const sheet = book.getSheetByName('Locations');
  if (!sheet) throw Error('The Pipeline has no Locations tab.');
  const values = sheet.getDataRange().getDisplayValues();
  const headers = (values[0] || []).map(h => String(h).trim());
  LOCATION_HEADERS.forEach(h => {
    if (!headers.includes(h)) throw Error('Locations is missing the ' + h + ' column.');
  });
  const rows = values.slice(1).map((cells, i) => ({row: i + 2,
    data: Object.fromEntries(headers.map((h, j) => [h, cells[j] || '']))}))
    .filter(record => String(record.data.Domain).trim());
  return {sheet, headers, rows};
}

function getFolderOverview() {
  const table = readFolderLocations();
  return {count: table.rows.length, tree: buildTree(table.rows.map(row => row.data))};
}

function checkFoldersAgainstDrive() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw Error('Another folder check is running. Try again shortly.');
  try {
    const table = readFolderLocations();
    const rows = table.rows.map(row => row.data);
    const ids = rows.map(row => folderId(row.Location)).filter(Boolean);
    const result = compareWithDrive(rows, folderDriveAdapter(ids));
    result.updates.forEach(update => {
      const record = table.rows[update.row];
      table.sheet.getRange(record.row, table.headers.indexOf(update.field) + 1).setValue(update.to);
      record.data[update.field] = update.to;
    });
    return {count: rows.length, ...result, tree: buildTree(rows)};
  } finally {
    lock.releaseLock();
  }
}

/* Batch listed parents and fetch any roots or moved folders the parent queries miss. */
function folderDriveAdapter(ids, api) {
  api = api || Drive;
  const options = {supportsAllDrives:true, includeItemsFromAllDrives:true,
    corpora:'allDrives', pageSize:1000,
    fields:'nextPageToken, files(id, name, parents, trashed)'};
  const info = {}, children = {};
  const add = file => {
    info[file.id] = {name:file.name, trashed:!!file.trashed, parentIds:file.parents || []};
    (file.parents || []).forEach(parent => {
      if (!file.trashed) (children[parent] = children[parent] || []).push({id:file.id, name:file.name});
    });
  };
  for (let i = 0; i < ids.length; i += 20) {
    const q = '(' + ids.slice(i, i + 20).map(id => "'" + id + "' in parents").join(' or ') +
      ") and mimeType = 'application/vnd.google-apps.folder'";
    let token;
    do {
      const page = api.Files.list(Object.assign({}, options, {q, pageToken:token}));
      (page.files || []).forEach(add);
      token = page.nextPageToken;
    } while (token);
  }
  ids.filter(id => !info[id]).forEach(id => {
    try { add(api.Files.get(id, {supportsAllDrives:true,
      fields:'id, name, parents, trashed'})); }
    catch (error) { info[id] = null; }
  });
  return {get:id => info[id] || null, children:id => children[id] || []};
}
