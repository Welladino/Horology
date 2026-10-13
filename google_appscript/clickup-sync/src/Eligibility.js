/* Local preflight rules shared by batch selection and per-item sync. */

function validateSyncRow(c,dt,row,s) {
  const d=row.data;
  if(!/^[1-9]\d*$/.test(String(d.ID||''))) throw Error('Pipeline ID must be a permanent positive integer.');
  if(!String(d.Title||'').trim()) throw Error('Set a Pipeline title.');
  const domainKeys=Object.keys(c.lists).filter(k=>norm(k)===norm(d.Domain));
  if(domainKeys.length!==1) throw Error('Missing or duplicate domain mapping: '+d.Domain);
  const listId=c.lists[domainKeys[0]];
  if(!/^\d+$/.test(String(listId||''))) throw Error('Configure list ID for domain '+d.Domain);
  if(s.pending) throw Error('Uncertain previous write: inspect _ClickUp Sync and reconcile before retry.');
  if(s.listId && String(s.listId)!==String(listId)) throw Error('Domain/list changed; reconcile task manually.');
  if(!/^Stage [0-3]$/.test(d.Stage)) throw Error('Set Stage explicitly: Stage 0, Stage 1, Stage 2, Stage 3.');
  if(!Object.prototype.hasOwnProperty.call(STATUS_MAP,norm(d.Status))) throw Error('Unknown Pipeline status '+d.Status);
  if(norm(d.Status)==='awaiting decision') {
    if(d.Stage!=='Stage 2' || !['Stage 1','Stage 3'].includes(d['Review stage'])) throw Error('Set Stage 2 and the originating Review stage.');
    const reviews=decisionRows(dt,d.ID).filter(r=>r.data['Decision ID']===d['Current decision ID']);
    if(reviews.length!==1 || reviews[0].data['Review stage']!==d['Review stage']) throw Error('Current decision ID must identify this item and review stage.');
    if(norm(reviews[0].data.Status)==='proposed') pendingDecision(dt,d.ID,d['Review stage']);
    else if(!['accepted','rework','parked','rejected'].includes(norm(reviews[0].data.Status))) throw Error('Unsupported decision status.');
  }
  if(d['ClickUp Pipeline URL'] && !taskId(d['ClickUp Pipeline URL'])) throw Error('Invalid ClickUp Pipeline URL.');
  if(s.taskId && taskId(d['ClickUp Pipeline URL']) && s.taskId!==taskId(d['ClickUp Pipeline URL'])) throw Error('Task link conflicts with sync state.');
  return listId;
}

function syncEligibility(c,dt,row,s) {
  if(!/^[1-9]\d*$/.test(String(row.data.ID||'')))
    return {status:'blocked',reason:'Pipeline ID must be a permanent positive integer.'};
  // Pending/managed items must report lost stages as blocked, not disappear.
  if(!String(row.data.Stage||'').trim() && !s.pending && !s.taskId && !row.data['ClickUp Pipeline URL'])
    return {status:'skipped',reason:'Stage not set; item is not ready for ClickUp sync.'};
  try {
    validateSyncRow(c,dt,row,s);
    return {status:'eligible'};
  } catch(e) {
    return {status:'blocked',reason:e.message};
  }
}

function comparePipelineIds(a,b) {
  // Positive canonical decimal IDs, ordered without floating-point rounding.
  a=String(a);b=String(b);
  return a.length-b.length || (a===b?0:a<b?-1:1);
}

function eligibleSyncRows(c,dt,rows,st,out) {
  const selected=rows.filter(r=>!c.ids.length||c.ids.includes(r.data.ID));
  const eligible=[];
  let skipped=0,blocked=0;
  selected.forEach(row=>{
    const result=syncEligibility(c,dt,row,st.get('task:'+row.data.ID));
    if(result.status==='eligible') eligible.push(row);
    else {
      if(result.status==='skipped') skipped++;else blocked++;
      out.push({pipelineId:row.data.ID,status:result.status,reason:result.reason});
    }
  });
  eligible.sort((a,b)=>comparePipelineIds(a.data.ID,b.data.ID));
  return {rows:eligible,selected:selected.length,skipped,blocked};
}

function syncBatchStart(rows,cursor) {
  // Historical positional offsets are deliberately ignored after this upgrade.
  if(!rows.length || !cursor.lastPipelineId) return 0;
  const next=rows.findIndex(row=>comparePipelineIds(row.data.ID,cursor.lastPipelineId)>0);
  return next<0?0:next;
}
