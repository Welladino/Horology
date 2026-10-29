/* Only explicitly linked rows are eligible. Several Pipeline items can share one
 * ClickUp task; each keeps its own sync state and comments. */
function linkedSyncRows(c,rows,st,out) {
  const selected=rows.filter(r=>!c.ids.length||c.ids.includes(String(r.data.ID)));
  const linked=[],taskOwners={},counts={skipped:0,blocked:0};
  // Owners come from every row, so a pilot scope cannot hide a task's other items.
  rows.forEach(row=>{
    const task=taskId(row.data['ClickUp Pipeline URL']);
    if(task) (taskOwners[task]=taskOwners[task]||[]).push(String(row.data.ID));
  });
  selected.forEach(row=>{
    const d=row.data,id=String(d.ID||''),url=String(d['ClickUp Pipeline URL']||'').trim();
    if(!/^\d+$/.test(id) || id==='0') {
      out.push({pipelineId:id,status:'blocked',reason:'Pipeline ID must be a positive integer.'});counts.blocked++;return;
    }
    if(!url) {counts.skipped++;return;}
    const task=taskId(url),prior=st.get('task:'+id);
    let reason='';
    if(!task) reason='Invalid ClickUp task URL.';
    else if(prior.pending) reason='Uncertain previous ClickUp write; reconcile _ClickUp Sync first.';
    else if(prior.taskId && prior.taskId!==task) reason='Task link conflicts with existing sync state.';
    else if(!Object.prototype.hasOwnProperty.call(STATUS_MAP,norm(d.Status)) &&
        !Object.prototype.hasOwnProperty.call(COMMENT_ONLY_STATUSES,norm(d.Status)))
      reason='Unknown Pipeline status '+d.Status+'.';
    if(reason) {out.push({pipelineId:id,status:'blocked',reason});counts.blocked++;return;}
    linked.push({row,task,prior,shared:taskOwners[task].length>1});
  });
  linked.sort((a,b)=>comparePipelineIds(a.row.data.ID,b.row.data.ID));
  return {rows:linked,selected:selected.length,skipped:counts.skipped,blocked:counts.blocked};
}

function comparePipelineIds(a,b) {
  a=String(a);b=String(b);
  return a.length-b.length || (a===b?0:a<b?-1:1);
}

function syncBatchStart(rows,cursor) {
  if(!rows.length || !cursor.lastPipelineId) return 0;
  const next=rows.findIndex(item=>comparePipelineIds(item.row.data.ID,cursor.lastPipelineId)>0);
  return next<0?0:next;
}
