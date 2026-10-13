/* Task identification, presentation and per-row coordination. */

function taskId(url) { const m=String(url||'').match(/^https:\/\/app\.clickup\.com\/t\/([a-zA-Z0-9]+)(?:[/?#]|$)/);return m?m[1]:''; }

function marker(c,id) {return '[Welladino Pipeline '+c.PIPELINE_SHEET_ID+':'+id+']';}

function description(c,pt,row) {
  const d=row.data;
  const lines=[marker(c,d.ID),
    'Pipeline: https://docs.google.com/spreadsheets/d/'+c.PIPELINE_SHEET_ID+'/edit#gid='+pt.sheet.getSheetId()+'&range=A'+row.row,
    'Domain: '+d.Domain,'Entity: '+(d.Entity||'—'),'Stage: '+d.Stage,
    'Pipeline status: '+d.Status,'Agent: '+d['Agent type'],
    'Summary / Why: '+(d['Summary / Why']||''),
    'Next step: '+(d['Next step / Research question']||''),
    'Document count: '+(row.documents||[]).length,
    'Document Index: https://docs.google.com/spreadsheets/d/'+c.DOCUMENT_INDEX_SHEET_ID+'/edit#gid=91352542',
    ...(row.documents||[]).map(doc=>doc.title+': '+doc.url),
    'Current decision ID: '+(d['Current decision ID']||'—'),
    'Target: '+(d.URL||''),'Branch: '+(d['GitHub branch']||''),
    '', 'Sheets owns this description. Personal notes belong in comments.',
    'While in review: open = approve current proposal; blocked = park; rejected = reject.',
    'For rework, edit the current proposed Decision Register row and its Rework instructions.',
    'ClickUp approval is enabled only for trusted editors; the task API does not identify the status-change actor.'];
  return lines.join('\n');
}

function syncRow(c,pt,dt,row,st,cache,live,out) {
  const d=row.data,key='task:'+d.ID,s=st.get(key);
  const listId=validateSyncRow(c,dt,row,s);
  const desired=STATUS_MAP[norm(d.Status)];
  let id=s.taskId||taskId(d['ClickUp Pipeline URL']),task;
  if(id) task=api(c,'task/'+id);
  else {
    if(!cache[listId]) cache[listId]=listTasks(c,listId);
    const matches=cache[listId].filter(t=>String(t.description||t.text_content||'').includes(marker(c,d.ID)));
    if(matches.length>1) throw Error('Duplicate managed tasks found.');
    task=matches[0];if(task) id=task.id;
  }
  if(task && String(task.list.id)!==String(listId)) throw Error('Linked task belongs to a different list.');
  if(task && !String(task.description||task.text_content||'').includes(marker(c,d.ID)) && c.ALLOW_ADOPT_EXISTING!=='true')
    throw Error('Linked task is not a managed mirror. Use a new task or explicitly opt in to adopting its description.');
  let remote=task?norm(task.status.status):'',desc=description(c,pt,row);
  if(!task) {
    out.push({pipelineId:d.ID,action:'create task',listId,status:desired});
    if(!live) return;
    s.pending='create task';st.save(key,s);
    task=api(c,'list/'+listId+'/task','post',{name:d.Title,description:desc,status:desired,notify_all:false});
    id=task.id;remote=norm(task.status.status);delete s.pending;s.taskId=id;s.listId=listId;st.save(key,s);
  }
  if(live && d['ClickUp Pipeline URL']!==task.url) put(pt,row,'ClickUp Pipeline URL',task.url||'https://app.clickup.com/t/'+id);
  ingestClickUpReview(c,pt,dt,row,s,task,remote,live,out);
  applySheetDecision(c,pt,dt,row,s,live,out);
  const status=STATUS_MAP[norm(d.Status)];desc=description(c,pt,row);
  if(task.name!==d.Title || String(task.description||task.text_content||'')!==desc || remote!==status) {
    out.push({pipelineId:d.ID,action:'update task',taskId:id,status});
    if(live) api(c,'task/'+id,'put',{name:d.Title,description:desc,status});
  }
  s.taskId=id;s.listId=listId;s.remote=status;s.sheetStatus=d.Status;s.stage=d.Stage;s.reviewStage=d['Review stage'];
  if(norm(d.Status)==='awaiting decision') s.reviewHash=snapshot(row,pendingDecision(dt,d.ID,d['Review stage']));
  else delete s.reviewHash;
  st.save(key,s);
  syncDecisionComments(c,dt,row,id,st,live,out);
  s.taskId=id;s.listId=listId;s.remote=status;s.sheetStatus=d.Status;s.stage=d.Stage;s.reviewStage=d['Review stage'];
  if(norm(d.Status)==='awaiting decision') {
    const dr=pendingDecision(dt,d.ID,d['Review stage']);s.reviewHash=snapshot(row,dr);
  } else delete s.reviewHash;
  st.save(key,s);
}
