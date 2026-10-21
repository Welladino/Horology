/* Schema and hourly trigger management. */

function initializeSheets() {
  // Run once manually. No ClickUp access. Existing rows stay intact.
  const p=sheetIds();
  addFields(SpreadsheetApp.openById(p.PIPELINE_SHEET_ID),['Stage','Review stage','Current decision ID','ClickUp Pipeline URL','Document count']);
}

function addFields(book,fields) {
  const s=book.getSheetByName('Master');let h=s.getRange(1,1,1,s.getLastColumn()).getDisplayValues()[0];
  fields.forEach(f=>{if(!h.includes(f)) {
    if(s.getMaxColumns()<=h.length) s.insertColumnAfter(s.getMaxColumns());
    const col=h.length+1;s.getRange(1,col).setValue(f).setFontWeight('bold');
    s.getRange(1,col,s.getMaxRows(),1).setWrap(true).setVerticalAlignment('top');
    s.setColumnWidth(col,180);h.push(f);
  }});
  console.log(book.getName()+': added missing Pipeline fields.');
}

function installHourlyTrigger() {
  if(!SYNC_CONFIG.ENABLE_WRITES) throw Error('Enable writes only after successful preview.');
  if(!ScriptApp.getProjectTriggers().some(t=>t.getHandlerFunction()==='applySync'))
    ScriptApp.newTrigger('applySync').timeBased().everyHours(1).create();
}

function stopSync() { ScriptApp.getProjectTriggers().filter(t=>t.getHandlerFunction()==='applySync').forEach(t=>ScriptApp.deleteTrigger(t)); }
