/* Review transitions and sheet decision application. */

function decisionRows(dt,id) {return dt.rows.filter(r=>String(r.data['Pipeline ID']).trim()===String(id));}

function pendingDecision(dt,id,stage) {
  const rows=decisionRows(dt,id).filter(r=>norm(r.data.Status)==='proposed');
  if(rows.length!==1) throw Error('Review needs exactly one proposed decision for Pipeline '+id);
  if(norm(rows[0].data['Review stage'])!==norm(stage)) throw Error('Decision review stage mismatch.');
  return rows[0];
}

function snapshot(row,decision) {
  return hash(JSON.stringify([row.data['Review stage'],decision.data]));
}

function decisionFingerprint(dr) {
  return hash(JSON.stringify([dr.data['Decision ID'],dr.data.Status,dr.data['Review stage'],dr.data['Rework instructions']]));
}

function reviewOutcome(remote,reviewStage) {
  if(remote==='open') return {decision:'accepted',status:reviewStage==='Investigation proposal'?'Approved':'Handed off',
    stage:reviewStage==='Investigation proposal'?'Stage 3':'Stage 4',agent:reviewStage==='Investigation proposal'?'Ready':'No action'};
  if(remote==='blocked') return {decision:'parked',status:'Parked',stage:reviewStage==='Investigation proposal'?'Stage 2':'Stage 4',agent:'No action'};
  if(remote==='rejected') return {decision:'rejected',status:'Rejected',stage:reviewStage==='Investigation proposal'?'Stage 2':'Stage 4',agent:'No action'};
  throw Error('Unsupported review status '+remote+'; use Decision Register for rework.');
}

function ingestClickUpReview(c,pt,dt,row,s,task,remote,live,out) {
  const d=row.data;
  // First attachment imports no status or approval. Establish an explicit baseline.
  if(s.remote && remote!==s.remote) {
    if(s.sheetStatus!==d.Status || s.stage!==d.Stage || s.reviewStage!==d['Review stage']) throw Error('Both sides changed; reconcile before sync.');
    if(s.remote!=='review' || norm(d.Status)!=='awaiting decision') throw Error('ClickUp changes only accepted during an established review.');
    const dr=pendingDecision(dt,d.ID,d['Review stage']);
    if(s.reviewHash!==snapshot(row,dr)) throw Error('Review contents changed since publishing; review again.');
    if(c.ALLOW_CLICKUP_REVIEW!=='true') throw Error('ClickUp review ingestion disabled. Confirm in Sheets or enable ALLOW_CLICKUP_REVIEW for a trusted-editor list.');
    // Task read exposes status, not a reliable status-change actor. Never invent one.
    const outcome=reviewOutcome(remote,d['Review stage']);
    out.push({pipelineId:d.ID,action:'ingest ClickUp review',decision:dr.data['Decision ID'],outcome,actor:'not exposed by task API'});
    if(live) {
      put(dt,dr,'Status',outcome.decision);
      if(dt.headers.includes('Decision Date')) put(dt,dr,'Decision Date',new Date());
      if(dt.headers.includes('Review source')) put(dt,dr,'Review source','ClickUp status '+remote+'; actor not exposed by task API; '+new Date().toISOString());
      put(pt,row,'Status',outcome.status);put(pt,row,'Stage',outcome.stage);
      // Only agent rows become Ready; Manual and Unassigned stay No action (as in pipeline-decisions).
      put(pt,row,'Agent status',['claude code','codex'].includes(norm(d['Agent type']))?outcome.agent:'No action');
      s.appliedDecision=decisionFingerprint(dr);
    } else {dr.data.Status=outcome.decision;d.Status=outcome.status;d.Stage=outcome.stage;}
  }
}
