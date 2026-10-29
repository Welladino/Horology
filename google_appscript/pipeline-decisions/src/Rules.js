/* What each founder decision does to its Pipeline item.
 * Mirrors the decision transitions in workflow.yaml (horology-capture-triage
 * references); a Python test checks the two agree. "REVIEW" means the Pipeline
 * stage corresponding to Review stage. Agent status Ready applies only to agent rows.
 */

const OUTCOMES = {
  "accepted|Investigation proposal": {"transition": "accept-stage-1", "Status": "Approved", "Stage": "Stage 3", "Agent status": "Ready"},
  "accepted|Specialist deliverable": {"transition": "accept-stage-3", "Status": "Completed", "Stage": "Stage 4", "Agent status": "No action"},
  "rework|Investigation proposal": {"transition": "rework", "Status": "Rework", "Stage": "REVIEW", "Agent status": "Ready"},
  "rework|Specialist deliverable": {"transition": "rework", "Status": "Rework", "Stage": "REVIEW", "Agent status": "Ready"},
  "parked|Investigation proposal": {"transition": "decide-park", "Status": "Parked", "Stage": "Stage 2", "Agent status": "No action"},
  "parked|Specialist deliverable": {"transition": "decide-park", "Status": "Parked", "Stage": "Stage 4", "Agent status": "No action"},
  "rejected|Investigation proposal": {"transition": "decide-reject", "Status": "Rejected", "Stage": "Stage 2", "Agent status": "No action"},
  "rejected|Specialist deliverable": {"transition": "decide-reject", "Status": "Rejected", "Stage": "Stage 4", "Agent status": "No action"}
};

// Revising a decided decision (workflow.yaml revise): which recorded outcomes and item statuses allow it.
const REVISE = {"transition": "revise", "decision_statuses": ["accepted", "rework", "parked", "rejected"],
  "item_statuses": ["Approved", "Rework", "Parked", "Rejected", "Completed"]};

// Only these Agent types can be made Ready; Manual and Unassigned never are.
const AGENT_TYPES = ['claude code', 'codex'];

function norm(x) { return String(x == null ? '' : x).trim().toLowerCase(); }

/* The change one Pipeline item needs, or {skip} / {error} with the reason.
 * item and decisions are {header: display text} maps. Pure: no sheet access.
 */
function decide(item, decisions) {
  if (norm(item['Status']) !== 'awaiting decision') return {skip: 'not awaiting decision'};
  const id = String(item['Current decision ID'] || '').trim();
  if (!id) return {error: 'Awaiting decision but no Current decision ID'};
  const matches = decisions.filter(d => String(d['Decision ID']).trim() === id);
  if (matches.length !== 1) return {error: (matches.length ? 'Duplicate' : 'No') + ' Decision Register row ' + id};
  const d = matches[0];
  if (String(d['Pipeline ID']).trim() !== String(item['ID']).trim())
    return {error: 'Decision ' + id + ' belongs to Pipeline ' + d['Pipeline ID']};
  const status = norm(d['Status']);
  if (status === 'proposed' || !status) return {skip: 'decision ' + id + ' not decided yet'};
  const stage = String(d['Review stage'] || '').trim();
  const outcome = OUTCOMES[status + '|' + stage];
  if (!outcome) return {error: 'Decision ' + id + ': unknown status "' + d['Status'] + '" or Review stage "' + stage + '"'};
  const itemStage = String(item['Review stage'] || '').trim();
  if (itemStage && itemStage !== stage)
    return {error: 'Decision ' + id + ' is for ' + stage + ' but the item is reviewing ' + itemStage};
  if (status === 'rework' && !String(d['Rework instructions'] || '').trim())
    return {error: 'Decision ' + id + ' is rework but has no Rework instructions'};
  return {decision: id, transition: outcome.transition, set: pipelineChange(item, outcome, stage)};
}

// The Pipeline fields an outcome sets, for the decision's Review stage and the item's Agent type.
function pipelineChange(item, outcome, stage) {
  const agent = outcome['Agent status'] === 'Ready' && !AGENT_TYPES.includes(norm(item['Agent type']))
    ? 'No action' : outcome['Agent status'];
  return {
    'Status': outcome['Status'],
    'Stage': outcome['Stage'] === 'REVIEW'
      ? (stage === 'Investigation proposal' ? 'Stage 1' : 'Stage 3') : outcome['Stage'],
    'Agent status': agent
  };
}

/* The change revising the item's current, already decided decision to newStatus makes, or {error}.
 * The item moves as newStatus would have moved it from review. Pure: no sheet access.
 */
function revise(item, decision, newStatus) {
  const id = String(decision['Decision ID'] || '').trim();
  if (String(item['Current decision ID'] || '').trim() !== id)
    return {error: 'Decision ' + id + ' is not the item’s current decision'};
  if (String(decision['Pipeline ID']).trim() !== String(item['ID']).trim())
    return {error: 'Decision ' + id + ' belongs to Pipeline ' + decision['Pipeline ID']};
  if (!REVISE.decision_statuses.includes(norm(decision['Status'])))
    return {error: 'Decision ' + id + ' is ' + (decision['Status'] || 'blank') + '; only a decided decision can be revised'};
  if (!REVISE.item_statuses.map(norm).includes(norm(item['Status'])))
    return {error: 'Pipeline ' + item['ID'] + ' is ' + item['Status'] + '; it can be revised only when no run or review is open'};
  const status = norm(newStatus);
  if (!REVISE.decision_statuses.includes(status)) return {error: 'Unknown outcome "' + newStatus + '"'};
  const stage = String(decision['Review stage'] || '').trim();
  const outcome = OUTCOMES[status + '|' + stage];
  if (!outcome) return {error: 'Decision ' + id + ': unknown Review stage "' + stage + '"'};
  return {decision: id, transition: REVISE.transition, set: pipelineChange(item, outcome, stage)};
}
