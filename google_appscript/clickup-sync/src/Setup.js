/* Schema and trigger management: hourly applySync is the catch-all; the
 * Pipeline onChange trigger posts soon after an edit that fires it. */

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

// Installable onChange on the Pipeline workbook. People's edits fire it; Sheets API
// and Apps Script writes may not, which the hourly trigger covers.
function installChangeTrigger() {
  if(!SYNC_CONFIG.ENABLE_WRITES) throw Error('Enable writes only after successful preview.');
  if(!ScriptApp.getProjectTriggers().some(t=>t.getHandlerFunction()==='syncOnPipelineChange'))
    ScriptApp.newTrigger('syncOnPipelineChange').forSpreadsheet(sheetIds().PIPELINE_SHEET_ID).onChange().create();
}

function removeChangeTrigger() { removeTriggers('syncOnPipelineChange'); }

function installTriggers() { installHourlyTrigger(); installChangeTrigger(); }

function stopSync() { removeTriggers('applySync'); removeTriggers('syncOnPipelineChange'); }

function removeTriggers(handler) {
  ScriptApp.getProjectTriggers().filter(t=>t.getHandlerFunction()===handler).forEach(t=>ScriptApp.deleteTrigger(t));
}
