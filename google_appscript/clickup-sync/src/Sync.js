/* Preview and apply entry points; bounded execution. */

function previewSync() { return runSync(false); }

function applySync() {
  if(!SYNC_CONFIG.ENABLE_WRITES) throw Error('Writes disabled. Preview first.');
  return runSync(true);
}

function runSync(live) {
  const lock=LockService.getScriptLock();if(!lock.tryLock(1000)) throw Error('Sync already running.');
  const started=Date.now(),output=[];
  try {
    const c=config(),pb=SpreadsheetApp.openById(c.PIPELINE_SHEET_ID),db=SpreadsheetApp.openById(c.DECISIONS_SHEET_ID);
    const pt=readTable(pb,PIPE_FIELDS.concat(['Review stage'])),dt=readTable(db,DEC_FIELDS);
    unique(pt.rows,'ID');unique(dt.rows,'Decision ID');
    const documents=readDocumentIndex(SpreadsheetApp.openById(c.DOCUMENT_INDEX_SHEET_ID));
    const st=stateStore(pb,live),cache={};
    const selection=eligibleSyncRows(c,dt,pt.rows,st,output);
    const eligible=selection.rows,offset=syncBatchStart(eligible,st.get('cursor'));
    let count=0,succeeded=0,failed=0,lastPipelineId;
    while(count<Math.min(c.max,eligible.length) && Date.now()-started<240000) {
      const row=eligible[(offset+count)%eligible.length];count++;
      lastPipelineId=row.data.ID;
      try {
        row.documents=documents[row.data.ID]||[];
        if(live && row.data['Document count']!==String(row.documents.length)) put(pt,row,'Document count',row.documents.length);
        syncRow(c,pt,dt,row,st,cache,live,output);
        succeeded++;
      } catch(e) {
        failed++;
        output.push({pipelineId:row.data.ID,status:'failed',error:e.message});
      }
    }
    // Persist last attempted identity; failures count toward bounded API work.
    if(live && count) st.save('cursor',{lastPipelineId});
    output.push({action:'summary',selected:selection.selected,eligible:eligible.length,
      skipped:selection.skipped,blocked:selection.blocked,attempted:count,succeeded,failed});
    console.log(JSON.stringify(output));return output;
  } finally {lock.releaseLock();}
}
