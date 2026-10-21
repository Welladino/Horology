/* Founder decision review page. Master sheets remain the only records. */

function doGet() {
  return HtmlService.createTemplateFromFile('Review').evaluate()
    .setTitle('Horology workspace')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function include(name) {
  if (name !== 'SharedUi') throw Error('Unknown HTML fragment.');
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}

function webRegisterIds() {
  const pipeline = SpreadsheetApp.openById(DECISIONS_CONFIG.WEB_PIPELINE_SHEET_ID);
  const tab = pipeline.getSheetByName('Registers');
  if (!tab) throw Error('The Pipeline has no Registers tab.');
  return {
    PIPELINE_ID: pipeline.getId(),
    DECISIONS_ID: registerIdFrom(tab.getDataRange().getDisplayValues(), /decision register/i)
  };
}

function reviewTables() {
  const ids = webRegisterIds();
  return {
    pipeline: readMaster(ids.PIPELINE_ID,
      ['ID', 'Title', 'Status', 'Review stage', 'Current decision ID']),
    register: readMaster(ids.DECISIONS_ID,
      ['Decision ID', 'Pipeline ID', 'Status', 'Review stage', 'Question',
        'Decision', 'Reason', 'Rework instructions'])
  };
}

function uniqueRow(table, column, id) {
  const matches = table.rows.filter(r => String(r.data[column]).trim() === String(id).trim());
  if (matches.length !== 1) throw Error('Expected one ' + column + ' ' + id + '; found ' + matches.length + '.');
  return matches[0];
}

function reviewVersion(item, decision) {
  return JSON.stringify([
    item.data.Title, item.data.Status, item.data['Review stage'], item.data['Current decision ID'],
    decision.data['Pipeline ID'], decision.data.Status, decision.data['Review stage'],
    decision.data.Question, decision.data.Decision, decision.data.Reason,
    decision.data['Research Links'], decision.data['Rework instructions']
  ]);
}

// Option codes already written into Decision text are hints, not a new data source.
// The full proposal and evidence are always shown so the founder can assess the wording.
function proposalOptions(text) {
  const value = String(text || '');
  const found = [], seen = {};
  const opening = value.match(/^\s*Proposed\s*:[^.]*?\bOption\s+([A-Z])\b/i);
  const recommendedCode = opening ? opening[1].toUpperCase() : '';
  const pattern = /\bOption\s+([A-Z])\b/gi;
  let match;
  while ((match = pattern.exec(value)) !== null) {
    const code = match[1].toUpperCase();
    if (seen[code]) continue;
    seen[code] = true;
    const before = value.slice(0, match.index);
    const boundary = Math.max(before.lastIndexOf('. '), before.lastIndexOf('; '), before.lastIndexOf('\n'));
    let context = before.slice(boundary < 0 ? 0 : boundary + 2).trim()
      .replace(/^(Proposed|Accepted):\s*/i, '').replace(/[\s(,;:–—-]+$/, '');
    if (context.length > 160) context = '…' + context.slice(-157);
    found.push({code, context: context || 'See the proposal for details', recommended: code === recommendedCode});
  }
  return found;
}

function sourceLinks(text) {
  const matches = String(text || '').match(/https:\/\/[^\s<>"']+/g) || [];
  return [...new Set(matches.map(s => s.replace(/[),.;]+$/, '')))].slice(0, 12);
}

function reviewRecord(decision, item) {
  const d = decision.data, p = item && item.data;
  const editable = !!p && norm(p.Status) === 'awaiting decision' &&
    String(p['Current decision ID']).trim() === String(d['Decision ID']).trim() &&
    norm(d.Status) === 'proposed' && norm(p['Review stage']) === norm(d['Review stage']);
  return {
    id: String(d['Decision ID']), pipelineId: String(d['Pipeline ID']),
    title: d['Pipeline title'] || (p && p.Title) || 'Untitled decision',
    domain: d.Domain || '', stage: d['Review stage'], status: d.Status,
    question: d.Question, proposal: d.Decision, reason: d.Reason,
    links: sourceLinks(d['Research Links']), options: proposalOptions(d.Decision),
    editable, version: editable ? reviewVersion(item, decision) : '',
    reviewTrigger: d['Review Trigger'] || '',
    reworkInstructions: d['Rework instructions'] || ''
  };
}

function getReviewDashboard() {
  const tables = reviewTables(), current = {}, pending = [], recent = [];
  tables.pipeline.rows.forEach(row => {
    const id = String(row.data['Current decision ID']).trim();
    if (id) current[id] = row;
  });
  tables.register.rows.forEach(row => {
    const id = String(row.data['Decision ID']).trim();
    const item = current[id] && String(current[id].data.ID).trim() === String(row.data['Pipeline ID']).trim()
      ? current[id] : null;
    const record = reviewRecord(row, item);
    if (record.editable) pending.push(record);
    else if (norm(row.data.Status) !== 'proposed') recent.push(record);
  });
  recent.sort((a, b) => Number(b.id) - Number(a.id));
  return {pending, recent};
}

function cleanReviewText(value, max, label) {
  const text = String(value == null ? '' : value).trim();
  if (text.length > max) throw Error(label + ' is too long.');
  return text;
}

function submitDecisionReview(request) {
  if (!DECISIONS_CONFIG.ENABLE_WRITES) throw Error('Decision writes are disabled.');
  const input = request || {};
  const id = cleanReviewText(input.decisionId, 80, 'Decision ID');
  const action = cleanReviewText(input.action, 30, 'Outcome').toLowerCase();
  if (!id || !['accepted', 'rework', 'parked', 'rejected'].includes(action))
    throw Error('Choose a current decision and a valid outcome.');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw Error('Another decision is being saved. Please try again.');
  let pipelineId;
  try {
    const tables = reviewTables();
    const decision = uniqueRow(tables.register, 'Decision ID', id);
    const item = uniqueRow(tables.pipeline, 'ID', decision.data['Pipeline ID']);
    if (norm(item.data.Status) !== 'awaiting decision' ||
        String(item.data['Current decision ID']).trim() !== id ||
        norm(decision.data.Status) !== 'proposed' ||
        norm(item.data['Review stage']) !== norm(decision.data['Review stage']))
      throw Error('This proposal is no longer the item’s current review. Refresh the page.');
    if (input.version !== reviewVersion(item, decision))
      throw Error('The proposal changed since you opened it. Refresh before saving.');
    pipelineId = String(item.data.ID);
    const note = cleanReviewText(input.note, 3000, 'Your note');
    const originalReason = String(decision.data.Reason || '').trim();
    if (action === 'accepted') {
      const code = cleanReviewText(input.optionCode, 12, 'Option').toUpperCase();
      const options = proposalOptions(decision.data.Decision);
      const selected = options.find(o => o.code === code);
      if (!selected && code !== 'OTHER' && !(code === 'PROPOSAL' && !options.length))
        throw Error('Choose one of the listed options or Another option.');
      if ((code === 'OTHER' || (selected && !selected.recommended)) && !note)
        throw Error('Add a short reason for choosing a different option.');
      const wording = cleanReviewText(input.wording, 4000, 'Decision wording');
      if (wording.length < 12) throw Error('Write the decision that should be recorded.');
      write(tables.register, decision, 'Decision', wording);
      if (note) {
        const label = selected ? 'Option ' + code : 'another option';
        write(tables.register, decision, 'Reason',
          originalReason + (originalReason ? '\n\n' : '') + 'Founder reason for ' + label + ': ' + note);
      }
    } else if (action === 'rework') {
      if (!note) throw Error('Add rework instructions.');
      write(tables.register, decision, 'Rework instructions', note);
    } else {
      if (!note) throw Error('Add a reason for this outcome.');
      write(tables.register, decision, 'Reason',
        originalReason + (originalReason ? '\n\n' : '') + 'Founder ' + action + ': ' + note);
    }
    if (tables.register.headers.includes('Review source')) {
      const source = 'Horology decision web page · ' + new Date().toISOString() +
        (action === 'accepted' ? ' · ' + (input.optionCode || '') : '');
      const previous = String(decision.data['Review source'] || '').trim();
      write(tables.register, decision, 'Review source',
        previous + (previous ? '\n' : '') + source);
    }
    if (tables.register.headers.includes('Decision Date') &&
        !String(decision.data['Decision Date'] || '').trim())
      write(tables.register, decision, 'Decision Date', today());
    // Status is last: the existing decision processor sees a complete record.
    write(tables.register, decision, 'Status', action);
  } finally {
    lock.releaseLock();
  }
  // Apps Script writes do not fire edit triggers. Apply immediately, then report any
  // pending transition honestly; the owner can retry applyDecisions in the editor.
  try {
    const result = applyDecisions(id).find(r => r.pipelineId === pipelineId && r.decision === id);
    return {saved: true, applied: !!(result && result.applied), warning:
      result && result.error ? result.error : result && result.applied ? '' :
        'Decision saved; the Pipeline transition is pending. Ask the owner to run applyDecisions.'};
  } catch (error) {
    return {saved: true, applied: false, warning:
      'Decision saved; the Pipeline transition is pending: ' + error.message};
  }
}
