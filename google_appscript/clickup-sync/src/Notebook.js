/* Compare saved Pipeline milestones with the last successful ClickUp update. */
function notebookSnapshot(row,dt,docs) {
  const id=String(row.data.ID),decisions={},documents={};
  dt.rows.filter(r=>String(r.data['Pipeline ID'])===id)
    .sort((a,b)=>comparePipelineIds(a.data['Decision ID'],b.data['Decision ID']))
    .forEach(r=>{
      const d=r.data,key=String(d['Decision ID']);
      decisions[key]={
        fingerprint:hash(JSON.stringify([d.Status,d['Review stage'],d.Question,d.Decision,d.Reason])),
        status:String(d.Status||''),stage:String(d['Review stage']||''),
        question:String(d.Question||''),decision:String(d.Decision||''),
        reason:String(d.Reason||'')
      };
    });
  docs.slice().sort((a,b)=>String(a.key).localeCompare(String(b.key))).forEach(d=>{
    documents[d.key]={title:d.title,url:d.url};
  });
  return {status:String(row.data.Status||''),stage:String(row.data.Stage||''),
    decisions,documents};
}

function compact(text,max) {
  const value=String(text||'').replace(/\s+/g,' ').trim();
  return value.length>max ? value.slice(0,max-1).trimEnd()+'…' : value;
}

function notebookUpdate(c,pt,dt,row,prior,now) {
  // Items with no sync record yet get one short intro. A record without a
  // notebook (an older baseline) stays silent: that item was already linked.
  if(!prior.notebook) return prior.taskId ? '' : notebookIntro(c,pt,dt,row,now);
  const before=prior.notebook,lines=[];
  if(before.status!==now.status || before.stage!==now.stage)
    lines.push('Pipeline: '+(now.stage||'No stage')+' · '+now.status);
  const changedDecisions=Object.keys(now.decisions).filter(id=>
    !before.decisions || !before.decisions[id] ||
    before.decisions[id].fingerprint!==now.decisions[id].fingerprint);
  changedDecisions.slice(0,8).forEach(id=>lines.push(decisionLine(id,now.decisions[id])));
  if(changedDecisions.length>8) lines.push('And '+(changedDecisions.length-8)+' more decision updates in the Decision Register.');
  if(changedDecisions.length)
    lines.push('Decision Register: https://docs.google.com/spreadsheets/d/'+c.DECISIONS_SHEET_ID+'/edit');
  const changedDocs=Object.keys(now.documents).filter(key=>
    !before.documents || !before.documents[key] ||
    JSON.stringify(before.documents[key])!==JSON.stringify(now.documents[key]));
  changedDocs.slice(0,15).forEach(key=>{
    const d=now.documents[key];lines.push('Document: '+compact(d.title||'Untitled',140)+' — '+d.url);
  });
  if(changedDocs.length>15) lines.push('And '+(changedDocs.length-15)+' more document updates in the Document Index.');
  if(changedDocs.length)
    lines.push('Document Index: https://docs.google.com/spreadsheets/d/'+c.DOCUMENT_INDEX_SHEET_ID+'/edit');
  if(!lines.length) return '';
  return notebookComment(c,pt,row,lines);
}

// First comment for an item: where it stands now and its latest decision, not its history.
function notebookIntro(c,pt,dt,row,now) {
  const lines=['Linked to Horology. Now: '+(now.stage||'No stage')+' · '+now.status];
  const ids=Object.keys(now.decisions).sort(comparePipelineIds);
  const current=String(row.data['Current decision ID']||'').trim();
  const latest=now.decisions[current]?current:ids[ids.length-1];
  if(latest) {
    const register=dt.rows.find(r=>String(r.data['Decision ID'])===latest);
    lines.push('Latest '+decisionLine(latest,now.decisions[latest],true)+
      '\nhttps://docs.google.com/spreadsheets/d/'+c.DECISIONS_SHEET_ID+'/edit'+
      (register?'#gid='+dt.sheet.getSheetId()+'&range=A'+register.row:''));
  } else lines.push('No decision yet.');
  return notebookComment(c,pt,row,lines);
}

// The intro is brief: no reason, and a shorter decision text.
function decisionLine(id,d,brief) {
  return 'Decision '+id+' · '+d.status+
    (d.stage?' ('+d.stage+')':'')+
    (d.question?' — '+compact(d.question,180):'')+
    (d.decision?'\n'+compact(d.decision,brief?200:320):'')+
    (d.reason&&!brief?'\nReason: '+compact(d.reason,220):'');
}

// Every comment names its item, because several Pipeline items can share one task.
function notebookComment(c,pt,row,lines) {
  const pipeline='https://docs.google.com/spreadsheets/d/'+c.PIPELINE_SHEET_ID+
    '/edit#gid='+pt.sheet.getSheetId()+'&range=A'+row.row;
  return 'Pipeline '+row.data.ID+' · '+compact(row.data.Title||'Untitled',120)+'\n\n'+lines.join('\n\n')+
    '\n\nHorology workspace: '+c.WORKSPACE_URL+'\nPipeline sheet: '+pipeline;
}
