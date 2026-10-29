/* Building a new Pipeline Master row from the Add item form, with no Google calls.
 * A new item follows the capture move in workflow.yaml (Inbox, Stage 0, No action,
 * Unassigned), or the select move when it is marked Ready straight away (Stage 1).
 * Type chooses the route (workflow.yaml routes): implementation-route items plan at
 * Stage 1 and implement at Stage 3 with Status In progress; the rest investigate.
 */

const ITEM_FIELDS = ['Title', 'Domain', 'Entity', 'Type', 'Summary / Why', 'Next step / Research question',
  'Revisit trigger', 'Agent status', 'Agent type', 'Run location', 'Link type', 'URL', 'GitHub branch'];

const ITEM_OPTIONS = {
  'Type': ['Idea', 'Research', 'Direction', 'Plan', 'Feature', 'Enhancement', 'Refactor', 'Fix'],
  'Agent status': ['No action', 'Plan', 'Ready'],
  'Agent type': ['Unassigned', 'Claude Code', 'Codex', 'Manual'],
  'Run location': ['Local', 'Cloud'],
  'Link type': ['GitHub', 'Website', 'Service endpoint', 'Other']
};

const IMPLEMENTATION_TYPES = ['Feature', 'Enhancement', 'Refactor', 'Fix'];

function itemRoute(type) {
  return IMPLEMENTATION_TYPES.includes(String(type || '').trim()) ? 'implementation' : 'investigation';
}

/* The Statuses from which the founder may make an item Ready (select in workflow.yaml).
 * An implementation-route item In progress can be selected again after its run failed or stopped.
 */
function readyStatuses(type) {
  return itemRoute(type) === 'implementation'
    ? ['Inbox', 'Rework', 'Approved', 'In progress'] : ['Inbox', 'Rework', 'Approved'];
}

// The next unused permanent ID: one more than the highest numeric ID.
function nextItemId(ids) {
  return ids.reduce((top, id) => /^\d+$/.test(String(id).trim()) ? Math.max(top, Number(id)) : top, 0) + 1;
}

// Domains tab rows (Domain, Entities) -> {domain: [entity, ...]}.
function domainMap(values) {
  const headers = (values[0] || []).map(h => String(h).trim());
  const d = headers.indexOf('Domain'), e = headers.indexOf('Entities');
  const map = {};
  values.slice(1).forEach(r => {
    const name = String(r[d] || '').trim();
    if (name) map[name] = String(r[e] || '').split(',').map(x => x.trim()).filter(Boolean);
  });
  return map;
}

/* The values for a new row, or the reasons it can't be added.
 * form: field -> text; domains: domainMap(); options: field -> allowed values.
 */
function itemValues(form, domains, options, ids, today) {
  const f = {};
  ITEM_FIELDS.forEach(k => { f[k] = String(form[k] || '').trim(); });
  f['Agent status'] = f['Agent status'] || 'No action';
  f['Agent type'] = f['Agent type'] || 'Unassigned';
  const errors = [];
  if (!f.Title) errors.push('Give the item a title.');
  if (!domains[f.Domain]) errors.push('Choose a domain from the Domains tab.');
  else if (f.Entity && domains[f.Domain].indexOf(f.Entity) < 0) errors.push(f.Entity + ' is not an entity of ' + f.Domain + '.');
  Object.keys(options).forEach(k => {
    if (f[k] && options[k].length && options[k].indexOf(f[k]) < 0) errors.push(k + ' must be one of: ' + options[k].join(', ') + '.');
  });
  if (f['Agent status'] === 'Ready') {
    if (['Claude Code', 'Codex'].indexOf(f['Agent type']) < 0) errors.push('A Ready item needs Agent type Claude Code or Codex.');
    if (!f['Next step / Research question']) errors.push('A Ready item needs a Next step / Research question.');
  }
  if (errors.length) return {errors};
  const values = Object.assign({}, f, {
    'ID': String(nextItemId(ids)), 'Status': 'Inbox', 'Created': today, 'Updated': today,
    'Stage': f['Agent status'] === 'Ready' ? 'Stage 1' : 'Stage 0'
  });
  return {errors, values};
}

// The row in header order; columns the form doesn't fill stay empty.
function itemRow(headers, values) {
  return headers.map(h => Object.prototype.hasOwnProperty.call(values, h) ? values[h] : '');
}
