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
    const selectedRows=pt.rows.filter(r=>!c.ids.length||c.ids.includes(r.data.ID));
    const offset=Number(st.get('cursor').offset||0)%Math.max(1,selectedRows.length);
    let count=0;
    while(count<Math.min(c.max,selectedRows.length) && Date.now()-started<240000) {
      const row=selectedRows[(offset+count)%selectedRows.length];count++;
      try {
        row.documents=documents[row.data.ID]||[];
        if(live && row.data['Document count']!==String(row.documents.length)) put(pt,row,'Document count',row.documents.length);
        syncRow(c,pt,dt,row,st,cache,live,output);
      } catch(e) {
        output.push({pipelineId:row.data.ID,error:e.message});
      }
    }
    if(live) st.save('cursor',{offset:(offset+count)%Math.max(1,selectedRows.length)});
    console.log(JSON.stringify(output));return output;
  } finally {lock.releaseLock();}
}
