/* What each founder decision does to its Pipeline item.
 * Mirrors the decision transitions in workflow.yaml (horology-capture-triage
 * references); a Python test checks the two agree. "REVIEW" means the item's
 * Review stage. Agent status Ready applies only to agent rows (see AGENT_TYPES).
 */

const OUTCOMES = {
  "accepted|Stage 1": {"transition": "accept-stage-1", "Status": "Approved", "Stage": "Stage 3", "Agent status": "Ready"},
  "accepted|Stage 3": {"transition": "accept-stage-3", "Status": "Handed off", "Stage": "Stage 3", "Agent status": "No action"},
  "rework|Stage 1": {"transition": "rework", "Status": "Rework", "Stage": "REVIEW", "Agent status": "Ready"},
  "rework|Stage 3": {"transition": "rework", "Status": "Rework", "Stage": "REVIEW", "Agent status": "Ready"},
  "parked|Stage 1": {"transition": "decide-park", "Status": "Parked", "Stage": "Stage 2", "Agent status": "No action"},
  "parked|Stage 3": {"transition": "decide-park", "Status": "Parked", "Stage": "Stage 2", "Agent status": "No action"},
  "rejected|Stage 1": {"transition": "decide-reject", "Status": "Rejected", "Stage": "Stage 2", "Agent status": "No action"},
  "rejected|Stage 3": {"transition": "decide-reject", "Status": "Rejected", "Stage": "Stage 2", "Agent status": "No action"}
};

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
  const agent = outcome['Agent status'] === 'Ready' && !AGENT_TYPES.includes(norm(item['Agent type']))
    ? 'No action' : outcome['Agent status'];
  return {decision: id, transition: outcome.transition, set: {
    'Status': outcome['Status'],
    'Stage': outcome['Stage'] === 'REVIEW' ? stage : outcome['Stage'],
    'Agent status': agent
  }};
}
