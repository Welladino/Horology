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

function notebookUpdate(c,pt,row,prior,now) {
  // First run establishes a baseline. Historical decisions and documents are
  // already available in Sheets; publishing all of them would flood ClickUp.
  if(!prior) return '';
  const lines=[];
  if(prior.status!==now.status || prior.stage!==now.stage)
    lines.push('Pipeline: '+(now.stage||'No stage')+' · '+now.status);
  const changedDecisions=Object.keys(now.decisions).filter(id=>
    !prior.decisions || !prior.decisions[id] ||
    prior.decisions[id].fingerprint!==now.decisions[id].fingerprint);
  changedDecisions.slice(0,8).forEach(id=>{
    const d=now.decisions[id];
    lines.push('Decision '+id+' · '+d.status+
      (d.stage?' ('+d.stage+')':'')+
      (d.question?' — '+compact(d.question,180):'')+
      (d.decision?'\n'+compact(d.decision,320):'')+
      (d.reason?'\nReason: '+compact(d.reason,220):''));
  });
  if(changedDecisions.length>8) lines.push('And '+(changedDecisions.length-8)+' more decision updates in the Decision Register.');
  if(changedDecisions.length)
    lines.push('Decision Register: https://docs.google.com/spreadsheets/d/'+c.DECISIONS_SHEET_ID+'/edit');
  const changedDocs=Object.keys(now.documents).filter(key=>
    !prior.documents || !prior.documents[key] ||
    JSON.stringify(prior.documents[key])!==JSON.stringify(now.documents[key]));
  changedDocs.slice(0,15).forEach(key=>{
    const d=now.documents[key];lines.push('Document: '+compact(d.title||'Untitled',140)+' — '+d.url);
  });
  if(changedDocs.length>15) lines.push('And '+(changedDocs.length-15)+' more document updates in the Document Index.');
  if(changedDocs.length)
    lines.push('Document Index: https://docs.google.com/spreadsheets/d/'+c.DOCUMENT_INDEX_SHEET_ID+'/edit');
  if(!lines.length) return '';
  const pipeline='https://docs.google.com/spreadsheets/d/'+c.PIPELINE_SHEET_ID+
    '/edit#gid='+pt.sheet.getSheetId()+'&range=A'+row.row;
  return 'Horology update · Pipeline '+row.data.ID+'\n\n'+lines.join('\n\n')+
    '\n\nPipeline: '+pipeline;
}
