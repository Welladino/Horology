/* Preview and apply one-way changes to linked ClickUp tasks. */
function previewSync() { return runSync(false); }
function applySync() {
  if(!SYNC_CONFIG.ENABLE_WRITES) throw Error('Writes disabled. Preview first.');
  return runSync(true);
}

// Pipeline workbook onChange trigger. Waits for edits to settle so a burst of
// cell changes gives one comment, then runs the same sync as the hourly trigger.
function syncOnPipelineChange(e) {
  if(!SYNC_CONFIG.ENABLE_WRITES) return;
  if(e && e.changeType==='FORMAT') return;
  const props=PropertiesService.getScriptProperties(),mark=String(Date.now())+':'+Math.random();
  props.setProperty('LAST_PIPELINE_CHANGE',mark);
  Utilities.sleep(SYNC_CONFIG.CHANGE_SETTLE_SECONDS*1000);
  if(props.getProperty('LAST_PIPELINE_CHANGE')!==mark) return; // a later change runs instead
  try {runSync(true,SYNC_CONFIG.CHANGE_LOCK_WAIT_SECONDS*1000);}
  catch(err) {
    // The running sync, or the next hourly run, picks this change up.
    if(err.message==='Sync already running.') {console.log('Sync already running; change left for the next run.');return;}
    throw err;
  }
}

function runSync(live,waitMs) {
  // One script lock covers both triggers and manual runs, so overlapping runs cannot double-post.
  const lock=LockService.getScriptLock();if(!lock.tryLock(waitMs||1000)) throw Error('Sync already running.');
  const started=Date.now(),output=[];
  try {
    const c=config(),pb=SpreadsheetApp.openById(c.PIPELINE_SHEET_ID);
    const pt=readTable(pb,PIPE_FIELDS),dt=readTable(SpreadsheetApp.openById(c.DECISIONS_SHEET_ID),DEC_FIELDS);
    unique(pt.rows,'ID');unique(dt.rows,'Decision ID');
    const documents=readDocumentIndex(SpreadsheetApp.openById(c.DOCUMENT_INDEX_SHEET_ID));
    const st=stateStore(pb,live),selection=linkedSyncRows(c,pt.rows,st,output);
    const pending=selection.rows.map(item=>{
      item.snapshot=notebookSnapshot(item.row,dt,documents[item.row.data.ID]||[]);
      return item;
    }).filter(item=>!item.prior.notebook || !!item.prior.shared!==item.shared ||
      JSON.stringify(item.prior.notebook)!==JSON.stringify(item.snapshot));
    const offset=syncBatchStart(pending,st.get('cursor'));
    let count=0,succeeded=0,failed=0,lastPipelineId;
    while(count<Math.min(c.max,pending.length) && Date.now()-started<240000) {
      const item=pending[(offset+count)%pending.length];count++;
      lastPipelineId=String(item.row.data.ID);
      try {syncRow(c,pt,dt,item,st,live,output);succeeded++;}
      catch(e) {failed++;output.push({pipelineId:lastPipelineId,status:'failed',error:e.message});}
    }
    if(live && count) st.save('cursor',{lastPipelineId});
    output.push({action:'summary',selected:selection.selected,linked:selection.rows.length,
      pending:pending.length,skipped:selection.skipped,blocked:selection.blocked,
      attempted:count,succeeded,failed});
    console.log(JSON.stringify(output));return output;
  } finally {lock.releaseLock();}
}
