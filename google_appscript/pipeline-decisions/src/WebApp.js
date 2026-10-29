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
        'Decision', 'Reason', 'Rework instructions']),
    options: readTab(ids.DECISIONS_ID, 'Options', ['Decision ID', 'Code', 'Summary', 'Recommended']),
    steps: readTab(ids.PIPELINE_ID, 'Steps', ['Pipeline ID', 'Step', 'Task'])
  };
}

// A child tab (workflow.yaml tabs) as {header: display text} rows. A workbook without the tab
// gives no rows, so its decisions and items fall back to the text in their Master cells.
function readTab(spreadsheetId, name, required) {
  const sheet = SpreadsheetApp.openById(spreadsheetId).getSheetByName(name);
  if (!sheet) return [];
  const values = sheet.getDataRange().getDisplayValues();
  const headers = (values[0] || []).map(h => String(h).trim());
  required.forEach(h => { if (!headers.includes(h)) throw Error('Missing column ' + h + ' in the ' + name + ' tab.'); });
  return values.slice(1).map(v => Object.fromEntries(headers.map((h, j) => [h, String(v[j] == null ? '' : v[j])])))
    .filter(r => String(r[required[0]]).trim());
}

function uniqueRow(table, column, id) {
  const matches = table.rows.filter(r => String(r.data[column]).trim() === String(id).trim());
  if (matches.length !== 1) throw Error('Expected one ' + column + ' ' + id + '; found ' + matches.length + '.');
  return matches[0];
}

function reviewVersion(item, decision, options) {
  return JSON.stringify([
    item.data.Title, item.data.Status, item.data['Review stage'], item.data['Current decision ID'],
    decision.data['Pipeline ID'], decision.data.Status, decision.data['Review stage'],
    decision.data.Question, decision.data.Decision, decision.data.Reason,
    decision.data['Research Links'], decision.data['Rework instructions'],
    (options || []).map(o => [o.code, o.context, o.recommended, o.figures])
  ]);
}

// A decision's options: its rows on the Decision Register's Options tab, in code order.
// A decision with no Options rows falls back to the option codes in its Decision text.
function decisionOptions(decisionId, optionRows, text) {
  const id = String(decisionId).trim(), seen = {};
  const rows = (optionRows || []).filter(r => String(r['Decision ID']).trim() === id && String(r.Code).trim());
  if (!rows.length) return proposalOptions(text);
  return rows.map(r => ({
    code: String(r.Code).trim().toUpperCase(),
    context: String(r.Summary || '').trim() || 'See the proposal for details',
    recommended: /^(yes|y|true|1|✓)$/i.test(String(r.Recommended || '').trim()),
    figures: bulletPoints(r['Key figures'])
  })).filter(o => !seen[o.code] && (seen[o.code] = true))
    .sort((a, b) => a.code.localeCompare(b.code));
}

// An item's planned steps: its rows on the Pipeline's Steps tab, in step order, or else
// the numbered lines of an older multi-line Next step.
function plannedSteps(pipelineId, stepRows, nextStep) {
  const id = String(pipelineId).trim();
  const rows = (stepRows || []).filter(r => String(r['Pipeline ID']).trim() === id && String(r.Task || '').trim());
  if (rows.length) return rows.map(r => ({
    number: String(r.Step).trim(), task: String(r.Task).trim(),
    specialist: String(r.Specialist || '').trim(), status: String(r.Status || '').trim()
  })).sort((a, b) => (Number(a.number) || 0) - (Number(b.number) || 0));
  return String(nextStep || '').split('\n').map(line => line.match(/^\s*(\d+)[.)]\s+(.+)$/)).filter(Boolean)
    .map(m => {
      const named = m[2].match(/\s*\[([^\]]+)\]\s*$/);
      return {number: m[1], task: (named ? m[2].slice(0, named.index) : m[2]).trim(),
        specialist: named ? named[1].trim() : '', status: ''};
    });
}

// Text as short bullet points: one per line, and long lines split into sentences.
function bulletPoints(text) {
  const out = [];
  String(text || '').split('\n').map(line => line.trim().replace(/^[-•*]\s+/, '')).filter(Boolean)
    .forEach(line => line.split(/(?<=[.;])\s+(?=[A-Z(“"])/).forEach(part => {
      if (part.trim()) out.push(part.trim());
    }));
  return out;
}

// Option codes already written into Decision text are hints, not a new data source.
// The full proposal and evidence are always shown so the founder can assess the wording.
function proposalOptions(text) {
  const value = String(text || '');
  const found = [], seen = {};
  const opening = value.match(/^\s*Proposed\b[^.]*?\bOption\s+([A-Z])\b/i);
  const recommendedCode = opening ? opening[1].toUpperCase() : '';
  const alternatives = alternativeOptions(value);
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
    if (alternatives[code]) context = alternatives[code];
    if (context.length > 160) context = '…' + context.slice(-157);
    found.push({code, context: context || 'See the proposal for details', recommended: code === recommendedCode, figures: []});
  }
  Object.keys(alternatives).filter(code => !seen[code]).forEach(code =>
    found.push({code, context: alternatives[code], recommended: code === recommendedCode, figures: []}));
  return found.sort((a, b) => a.code.localeCompare(b.code));
}

// "Alternatives: A lead with beginners; C lead with coaches; park" names options by letter alone.
function alternativeOptions(value) {
  const out = {};
  const m = value.match(/\bAlternatives?\s*:\s*([\s\S]*?)(?:\.(?=\s*$|\s*\n|\s+[A-Z][a-z])|\n|$)/);
  if (!m) return out;
  m[1].split(/;\s*|,\s+(?=(?:Option\s+)?[A-Z][\s,:])/).forEach(piece => {
    const hit = piece.trim().match(/^(?:Option\s+)?([A-Z])[\s,:–—-]+(\S[\s\S]*)$/);
    if (hit && !out[hit[1]]) out[hit[1]] = hit[2].trim().replace(/[.;]+$/, '').slice(0, 160);
  });
  return out;
}

function sourceLinks(text) {
  const matches = String(text || '').match(/https:\/\/[^\s<>"']+/g) || [];
  return [...new Set(matches.map(s => s.replace(/[),.;]+$/, '')))].slice(0, 12);
}

function reviewRecord(decision, item, tables) {
  const d = decision.data, p = item && item.data;
  const editable = !!p && norm(p.Status) === 'awaiting decision' &&
    String(p['Current decision ID']).trim() === String(d['Decision ID']).trim() &&
    norm(d.Status) === 'proposed' && norm(p['Review stage']) === norm(d['Review stage']);
  const revisable = !!p && !editable && !revise(p, d, 'parked').error;
  const options = decisionOptions(d['Decision ID'], tables && tables.options, d.Decision);
  return {
    id: String(d['Decision ID']), pipelineId: String(d['Pipeline ID']),
    title: d['Pipeline title'] || (p && p.Title) || 'Untitled decision',
    domain: d.Domain || '', stage: d['Review stage'], status: d.Status,
    question: d.Question, proposal: d.Decision, reason: d.Reason,
    reasonPoints: bulletPoints(d.Reason),
    steps: p ? plannedSteps(p.ID, tables && tables.steps, p['Next step / Research question']) : [],
    links: sourceLinks(d['Research Links']), options,
    editable, revisable,
    version: editable || revisable ? reviewVersion(item, decision, options) : '',
    itemStatus: p ? p.Status : '',
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
    const record = reviewRecord(row, item, tables);
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
    const options = decisionOptions(id, tables.options, decision.data.Decision);
    if (input.version !== reviewVersion(item, decision, options))
      throw Error('The proposal changed since you opened it. Refresh before saving.');
    pipelineId = String(item.data.ID);
    const note = cleanReviewText(input.note, 3000, 'Your note');
    const originalReason = String(decision.data.Reason || '').trim();
    if (action === 'accepted') {
      const code = cleanReviewText(input.optionCode, 12, 'Option').toUpperCase();
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

/* Revise the item's current, already decided decision (workflow.yaml revise), for example
 * Approved to Parked. The decision row keeps its ID; Status becomes the new outcome and the
 * founder's reason is appended. The Pipeline item moves in the same call.
 */
function reviseDecisionReview(request) {
  if (!DECISIONS_CONFIG.ENABLE_WRITES) throw Error('Decision writes are disabled.');
  const input = request || {};
  const id = cleanReviewText(input.decisionId, 80, 'Decision ID');
  const action = cleanReviewText(input.action, 30, 'Outcome').toLowerCase();
  if (!id || !REVISE.decision_statuses.includes(action)) throw Error('Choose a decision and a valid new outcome.');
  const note = cleanReviewText(input.note, 3000, 'Your note');
  if (!note) throw Error(action === 'rework' ? 'Add rework instructions.' : 'Add a reason for revising this decision.');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw Error('Another decision is being saved. Please try again.');
  try {
    const tables = reviewTables();
    const decision = uniqueRow(tables.register, 'Decision ID', id);
    const item = uniqueRow(tables.pipeline, 'ID', decision.data['Pipeline ID']);
    const options = decisionOptions(id, tables.options, decision.data.Decision);
    if (input.version !== reviewVersion(item, decision, options))
      throw Error('This decision or its item changed since you opened it. Refresh before saving.');
    const result = revise(item.data, decision.data, action);
    if (result.error) throw Error(result.error + '.');
    const before = String(decision.data.Status || '').trim();
    let label = action;
    if (action === 'accepted') {
      const code = cleanReviewText(input.optionCode, 12, 'Option').toUpperCase();
      const selected = options.find(o => o.code === code);
      if (!selected && code !== 'OTHER' && !(code === 'PROPOSAL' && !options.length))
        throw Error('Choose one of the listed options or Another option.');
      const wording = cleanReviewText(input.wording, 4000, 'Decision wording');
      if (wording.length < 12) throw Error('Write the decision that should be recorded.');
      write(tables.register, decision, 'Decision', wording);
      label = 'accepted' + (selected ? ' (Option ' + code + ')' : '');
    }
    if (action === 'rework') write(tables.register, decision, 'Rework instructions', note);
    const reason = String(decision.data.Reason || '').trim();
    write(tables.register, decision, 'Reason', reason + (reason ? '\n\n' : '') + 'Founder revised ' +
      before + ' to ' + label + ' on ' + displayDate(today()) +
      ': ' + note);
    if (tables.register.headers.includes('Review source')) {
      const previous = String(decision.data['Review source'] || '').trim();
      write(tables.register, decision, 'Review source', previous + (previous ? '\n' : '') +
        'Horology decision web page · revise · ' + new Date().toISOString() + ' · ' + label);
    }
    write(tables.register, decision, 'Status', action);
    Object.keys(result.set).forEach(h => write(tables.pipeline, item, h, result.set[h]));
    if (tables.pipeline.headers.includes('Updated')) write(tables.pipeline, item, 'Updated', today());
    return {saved: true, applied: true, transition: result.transition, set: result.set};
  } finally {
    lock.releaseLock();
  }
}

function displayDate(date) {
  const pad = n => String(n).padStart(2, '0');
  return pad(date.getDate()) + '/' + pad(date.getMonth() + 1) + '/' + date.getFullYear();
}
