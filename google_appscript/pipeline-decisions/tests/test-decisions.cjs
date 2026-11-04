// Offline tests: the decision rules, and the run against in-memory sheets. No Google access.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const dir = path.join(__dirname, '../src');
const source = fs.readdirSync(dir).filter(n => n.endsWith('.js')).sort().map(n => fs.readFileSync(path.join(dir, n), 'utf8')).join('\n');

function load(extra = {}) {
  const ctx = vm.createContext({console: {log: () => {}}, Date, JSON, Object, Array, String, Error, ...extra});
  vm.runInContext(source, ctx);
  return ctx;
}

const item = (o = {}) => ({'ID': '42', 'Status': 'Awaiting decision', 'Stage': 'Stage 2', 'Review stage': 'Investigation proposal',
  'Agent status': 'No action', 'Agent type': 'Claude Code', 'Current decision ID': 'D-3', ...o});
const decision = (o = {}) => ({'Decision ID': 'D-3', 'Pipeline ID': '42', 'Status': 'accepted', 'Review stage': 'Investigation proposal',
  'Rework instructions': '', ...o});

let passed = 0;
function test(name, fn) { fn(); passed++; console.log('PASS ' + name); }
const {decide, revise} = load();

test('accepting a Stage 1 review approves the item and makes it Ready', () => {
  const r = decide(item(), [decision()]);
  assert.equal(r.transition, 'accept-stage-1');
  assert.deepEqual({...r.set}, {'Status': 'Approved', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
});
test('accepting a Stage 3 review completes it without queuing more work', () => {
  const r = decide(item({'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable'}), [decision({'Review stage': 'Specialist deliverable'})]);
  assert.deepEqual({...r.set}, {'Status': 'Completed', 'Stage': 'Stage 4', 'Agent status': 'No action'});
});
test('rework returns to the reviewed stage and needs instructions', () => {
  assert.match(decide(item(), [decision({'Status': 'rework'})]).error, /Rework instructions/);
  const r = decide(item({'Review stage': 'Specialist deliverable'}), [decision({'Status': 'Rework', 'Review stage': 'Specialist deliverable', 'Rework instructions': 'Add costs'})]);
  assert.deepEqual({...r.set}, {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
});
test('park and reject stop the item', () => {
  assert.equal(decide(item(), [decision({'Status': 'parked'})]).set['Status'], 'Parked');
  assert.equal(decide(item(), [decision({'Status': 'rejected'})]).set['Agent status'], 'No action');
  assert.equal(decide(item({'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable'}), [decision({'Status': 'parked', 'Review stage': 'Specialist deliverable'})]).set['Stage'], 'Stage 4');
});
test('Manual and Unassigned items are never made Ready', () => {
  assert.equal(decide(item({'Agent type': 'Manual'}), [decision()]).set['Agent status'], 'No action');
  assert.equal(decide(item({'Agent type': 'Unassigned'}), [decision({'Status': 'rework', 'Rework instructions': 'x'})]).set['Agent status'], 'No action');
  assert.equal(decide(item({'Agent type': 'Codex'}), [decision()]).set['Agent status'], 'Ready');
  assert.equal(decide(item({'Agent type': 'ChatGPT Work'}), [decision()]).set['Agent status'], 'Ready');
  assert.equal(decide(item({'Agent type': 'Hermes'}), [decision()]).set['Agent status'], 'Ready');
});
test('only items still awaiting a decision are touched, so nothing is applied twice', () => {
  assert.ok(decide(item({'Status': 'Approved'}), [decision()]).skip);
  assert.ok(decide(item({'Status': 'Researching'}), [decision()]).skip);
});
test('undecided proposals are skipped', () => {
  assert.ok(decide(item(), [decision({'Status': 'proposed'})]).skip);
});
test('only the current decision counts, and it must match the item', () => {
  assert.match(decide(item({'Current decision ID': ''}), [decision()]).error, /no Current decision ID/);
  assert.match(decide(item(), [decision({'Decision ID': 'D-9'})]).error, /No Decision Register row D-3/);
  assert.match(decide(item(), [decision(), decision()]).error, /Duplicate/);
  assert.match(decide(item(), [decision({'Pipeline ID': '7'})]).error, /belongs to Pipeline 7/);
  assert.match(decide(item({'Review stage': 'Specialist deliverable'}), [decision()]).error, /reviewing Specialist deliverable/);
  assert.match(decide(item(), [decision({'Review stage': 'Stage 2'})]).error, /Review stage/);
});

test('a Stage 4 item is Completed with its Specialist deliverable decision still open', () => {
  const done = (o = {}) => item({'Status': 'Completed', 'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable', ...o});
  const deliverable = (o = {}) => decision({'Review stage': 'Specialist deliverable', ...o});
  assert.ok(decide(done(), [deliverable({'Status': 'proposed'})]).skip);
  // Accepting changes nothing, so the item is not rewritten on every check.
  const accepted = decide(done(), [deliverable()]);
  assert.match(accepted.skip, /already applied/);
  assert.equal(accepted.decision, 'D-3');
  assert.equal(accepted.transition, 'accept-stage-3');
  // Rework, park and reject reopen it.
  assert.deepEqual({...decide(done(), [deliverable({'Status': 'rework', 'Rework instructions': 'Add costs'})]).set},
    {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  assert.deepEqual({...decide(done(), [deliverable({'Status': 'parked'})]).set},
    {'Status': 'Parked', 'Stage': 'Stage 4', 'Agent status': 'No action'});
  assert.equal(decide(done(), [deliverable({'Status': 'rejected'})]).set['Status'], 'Rejected');
});
test('a finished implementation is Completed at Stage 4 and its decision can send it back to Stage 3', () => {
  // Item 69 (04/11/2026): the implementation route ends like the investigation route.
  const done = (o = {}) => item({'Type': 'Enhancement', 'Status': 'Completed', 'Stage': 'Stage 4',
    'Review stage': 'Specialist deliverable', ...o});
  const deliverable = (o = {}) => decision({'Review stage': 'Specialist deliverable', ...o});
  assert.match(decide(done(), [deliverable()]).skip, /already applied/);
  const rework = decide(done(), [deliverable({'Status': 'rework', 'Rework instructions': 'Cover the digest too'})]);
  assert.equal(rework.transition, 'rework');
  assert.deepEqual({...rework.set}, {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  assert.ok(load().readyStatuses("Enhancement").includes("Rework"));
  assert.deepEqual({...decide(done({'Agent type': 'Manual'}), [deliverable({'Status': 'rework', 'Rework instructions': 'x'})]).set},
    {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'No action'});
  assert.deepEqual({...decide(done(), [deliverable({'Status': 'parked'})]).set},
    {'Status': 'Parked', 'Stage': 'Stage 4', 'Agent status': 'No action'});
});
test('a Completed item without an open Stage 4 review is left alone, without errors', () => {
  // Items finished before Stage 4 had its own decision still point at their Stage 2 decision.
  assert.match(decide(item({'Status': 'Completed', 'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable'}),
    [decision()]).skip, /is for Investigation proposal/);
  assert.ok(decide(item({'Status': 'Completed', 'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable',
    'Current decision ID': ''}), [decision()]).skip);
  // A finished implementation (Completed at Stage 3) has no open review.
  assert.ok(decide(item({'Status': 'Completed', 'Stage': 'Stage 3', 'Review stage': 'Implementation question'}),
    [decision({'Status': 'parked', 'Review stage': 'Implementation question'})]).skip);
});
test('revise moves a decided item as the new outcome would from review', () => {
  const approved = item({'Status': 'Approved', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  const r = revise(approved, decision(), 'parked');
  assert.equal(r.transition, 'revise');
  assert.deepEqual({...r.set}, {'Status': 'Parked', 'Stage': 'Stage 2', 'Agent status': 'No action'});
  const done = item({'Status': 'Completed', 'Stage': 'Stage 4', 'Review stage': 'Specialist deliverable'});
  assert.deepEqual({...revise(done, decision({'Review stage': 'Specialist deliverable'}), 'rework').set},
    {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  const parked = item({'Status': 'Parked', 'Agent type': 'Manual'});
  assert.deepEqual({...revise(parked, decision({'Status': 'parked'}), 'accepted').set},
    {'Status': 'Approved', 'Stage': 'Stage 3', 'Agent status': 'No action'});
});
test('revise needs the item\'s current decided decision and no open run or review', () => {
  const approved = item({'Status': 'Approved'});
  assert.match(revise(approved, decision({'Decision ID': 'D-1'}), 'parked').error, /not the item/);
  assert.match(revise(approved, decision({'Status': 'proposed'}), 'parked').error, /only a decided decision/);
  assert.match(revise(item(), decision(), 'parked').error, /Awaiting decision; it can be revised only/);
  assert.match(revise(item({'Status': 'Researching'}), decision(), 'parked').error, /Researching/);
  assert.match(revise(approved, decision(), 'proposed').error, /Unknown outcome/);
  assert.match(revise(approved, decision({'Pipeline ID': '7'}), 'parked').error, /belongs to Pipeline 7/);
});

test('answering an Implementation question resumes the item at Stage 3, In progress and Ready', () => {
  const asked = item({'Stage': 'Stage 3', 'Review stage': 'Implementation question'});
  const answer = decision({'Review stage': 'Implementation question'});
  const r = decide(asked, [answer]);
  assert.equal(r.transition, 'resume-implementation');
  assert.deepEqual({...r.set}, {'Status': 'In progress', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  assert.equal(decide({...asked, 'Agent type': 'Manual'}, [answer]).set['Agent status'], 'No action');
  assert.deepEqual({...decide(asked, [decision({'Status': 'rework', 'Review stage': 'Implementation question',
    'Rework instructions': 'Use the smaller option'})]).set}, {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
  assert.deepEqual({...decide(asked, [decision({'Status': 'parked', 'Review stage': 'Implementation question'})]).set},
    {'Status': 'Parked', 'Stage': 'Stage 3', 'Agent status': 'No action'});
  assert.equal(decide(asked, [decision({'Status': 'rejected', 'Review stage': 'Implementation question'})]).set['Status'], 'Rejected');
});
test('an item In progress is a run in progress: no decision is applied and it cannot be revised', () => {
  assert.ok(decide(item({'Status': 'In progress', 'Stage': 'Stage 3'}), [decision()]).skip);
  assert.match(revise(item({'Status': 'In progress'}), decision(), 'parked').error, /In progress/);
  const parked = item({'Status': 'Parked', 'Stage': 'Stage 3', 'Review stage': 'Implementation question'});
  assert.deepEqual({...revise(parked, decision({'Status': 'parked', 'Review stage': 'Implementation question'}), 'accepted').set},
    {'Status': 'In progress', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
});
test('Type chooses the route; Fix takes the implementation route', () => {
  const ctx = load(), {itemRoute, readyStatuses} = ctx;
  assert.ok(vm.runInContext('ITEM_OPTIONS.Type', ctx).includes('Fix'));
  for (const type of ['Feature', 'Enhancement', 'Refactor', 'Fix']) assert.equal(itemRoute(type), 'implementation');
  for (const type of ['Idea', 'Research', 'Direction', 'Plan', '']) assert.equal(itemRoute(type), 'investigation');
  assert.ok(readyStatuses('Fix').includes('In progress'));
  assert.ok(!readyStatuses('Research').includes('In progress'));
});

// The run, against fake workbooks.
function sheet(rows) {
  const writes = [];
  return {rows, writes, getSheetId: () => 2040100901, getLastColumn: () => rows[0].length,
    getDataRange: () => ({getDisplayValues: () => rows.map(r => r.map(String)),
      getValues: () => rows.map(r => r.slice())}),
    getRange: (r, c, h, w) => ({
      getDisplayValues: () => rows.slice(r - 1, r - 1 + (h || 1))
        .map(row => row.slice(c - 1, c - 1 + (w || 1)).map(String)),
      getDataValidation: () => null,
      setValue: v => { writes.push([r, c, v]); rows[r - 1][c - 1] = v; },
      setValues: values => { writes.push([r, c, values[0]]); rows[r - 1] = values[0]; }
    })};
}
function workbooks() {
  const pipeline = sheet([
    ['ID', 'Title', 'Status', 'Stage', 'Review stage', 'Agent status', 'Agent type', 'Current decision ID', 'Updated'],
    ['42', 'Pricing', 'Awaiting decision', 'Stage 2', 'Investigation proposal', 'No action', 'Claude Code', 'D-3', ''],
    ['43', 'Brand', 'Awaiting decision', 'Stage 2', 'Investigation proposal', 'No action', 'Codex', 'D-4', ''],
    ['44', 'Old', 'Researching', 'Investigation proposal', '', 'No action', 'Codex', 'D-1', '']]);
  const register = sheet([
    ['Decision ID', 'Pipeline ID', 'Status', 'Review stage', 'Rework instructions', 'Decision Date'],
    ['D-1', '44', 'accepted', 'Investigation proposal', '', '2026-10-01'],
    ['D-3', '42', 'accepted', 'Investigation proposal', '', ''],
    ['D-4', '43', 'proposed', 'Investigation proposal', '', '']]);
  const registers = sheet([['Register', 'Location', 'Use'],
    ['Horology — Pipeline', 'https://docs.google.com/spreadsheets/d/P/edit', ''],
    ['Horology — Decision Register', 'https://docs.google.com/spreadsheets/d/D/edit', '']]);
  const books = {P: {Master: pipeline, Registers: registers}, D: {Master: register}};
  const book = id => ({getId: () => id, getSheetByName: n => books[id][n] || null});
  const lock = {released: false, tryLock: () => true, releaseLock() { this.released = true; }};
  const ctx = load({SpreadsheetApp: {openById: book, getActiveSpreadsheet: () => book('P')},
    LockService: {getScriptLock: () => lock}});
  return {ctx, pipeline, register, registers, lock};
}

test('preview reports what would change and writes nothing', () => {
  const w = workbooks();
  const out = w.ctx.previewDecisions();
  assert.equal(out.length, 1);
  assert.equal(out[0].pipelineId, '42');
  assert.equal(out[0].applied, false);
  assert.deepEqual(w.pipeline.writes, []);
  assert.ok(w.lock.released);
});
test('apply writes the item, dates it, and is not repeated on the next run', () => {
  const w = workbooks();
  w.ctx.applyDecisions();
  assert.deepEqual(w.pipeline.rows[1].slice(2, 6), ['Approved', 'Stage 3', 'Investigation proposal', 'Ready']);
  assert.ok(w.pipeline.rows[1][8] instanceof Date);
  assert.ok(w.register.rows[2][5] instanceof Date);  // Decision Date filled in
  assert.equal(w.register.rows[1][5], '2026-10-01');  // an existing date is kept
  assert.deepEqual(w.pipeline.rows[2].slice(2, 6), ['Awaiting decision', 'Stage 2', 'Investigation proposal', 'No action']);
  assert.equal(w.pipeline.rows[3][2], 'Researching');  // an old accepted decision is never replayed
  const before = w.pipeline.writes.length;
  assert.equal(w.ctx.applyDecisions().length, 0);
  assert.equal(w.pipeline.writes.length, before);
});
test('ENABLE_WRITES false makes apply a preview', () => {
  const w = workbooks();
  vm.runInContext('DECISIONS_CONFIG.ENABLE_WRITES=false;', w.ctx);
  w.ctx.applyDecisions();
  assert.deepEqual(w.pipeline.writes, []);
});
test('a missing column stops the run before any write', () => {
  const w = workbooks();
  w.pipeline.rows[0][7] = 'Decision';
  assert.throws(() => w.ctx.applyDecisions(), /Missing column Current decision ID/);
  assert.deepEqual(w.pipeline.writes, []);
  assert.ok(w.lock.released);
});

test('the Decision Register is found on the bound Pipeline\'s Registers tab', () => {
  const w = workbooks();
  assert.deepEqual({...w.ctx.registerIds()}, {PIPELINE_ID: 'P', DECISIONS_ID: 'D'});
});
test('a missing or duplicated Decision Register row stops the run before any write', () => {
  const w = workbooks();
  w.registers.rows.push(['Old Decision Register', 'https://docs.google.com/spreadsheets/d/X/edit', '']);
  assert.throws(() => w.ctx.applyDecisions(), /exactly one row/);
  w.registers.rows.splice(2, 2);
  assert.throws(() => w.ctx.applyDecisions(), /found 0/);
  assert.deepEqual(w.pipeline.writes, []);
});

// CacheService's script cache, with its 100 KB per-value limit (counted in UTF-8 bytes).
function fakeCache() {
  const store = {};
  const put = (k, v) => {
    assert.ok(Buffer.byteLength(v) <= 100 * 1024, 'cache value over 100 KB: ' + k);
    store[k] = v;
  };
  return {store, get: k => store[k] ?? null, put, putAll: o => Object.keys(o).forEach(k => put(k, o[k])),
    getAll: ks => Object.fromEntries(ks.filter(k => k in store).map(k => [k, store[k]])),
    remove: k => { delete store[k]; }, removeAll: ks => ks.forEach(k => { delete store[k]; })};
}
function webWorkbooks(tabs = {}) {
  const pipeline = sheet([
    ['ID','Title','Status','Stage','Review stage','Agent status','Agent type','Current decision ID','Updated',
      'Next step / Research question','Domain','Entity','Type','Run location','Summary / Why','Revisit trigger'],
    ['14','TF-IDF and SERP-grounded drafting','Awaiting decision','Stage 2','Investigation proposal','No action','Codex','1','','','Article Aggregator','','Research','Local','',''],
    ['22','Audience lists','Completed','Stage 4','Specialist deliverable','No action','Codex','4','','','Article Aggregator','','Direction','Local','','']]);
  const register = sheet([
    ['Decision ID','Pipeline ID','Pipeline title','Domain','Review stage','Question','Decision','Reason',
      'Status','Decision Date','Research Links','Rework instructions','Review source'],
    ['1','14','TF-IDF and SERP-grounded drafting','Article Aggregator','Investigation proposal',
      'Which content feature?','Proposed: run a measurement spike (Option B). Build TF-IDF term gap (Option C).',
      'The pilot has not shown a gap.','proposed','','https://docs.google.com/document/d/evidence/edit','',''],
    ['3','22','Audience lists','Article Aggregator','Investigation proposal',
      'Should we own sending?','Accepted: delegate sending.','Keep scope narrow.',
      'accepted','2026-10-19','','',''],
    ['4','22','Audience lists','Article Aggregator','Specialist deliverable',
      'Should we own sending?','Accepted: stay ESP-delegated (Option A).','No pilot demand.',
      'accepted','2026-10-20','','','']]);
  const registers = sheet([['Register','Location'],['Horology — Decision Register','https://docs.google.com/spreadsheets/d/D/edit']]);
  const domains = sheet(tabs.domains || [['Domain','Entities'],['Article Aggregator',''],['Horology','']]);
  const books = {P:{Master:pipeline,Registers:registers,Domains:domains},D:{Master:register}};
  if (tabs.options) books.D.Options = sheet(tabs.options);
  if (tabs.steps) books.P.Steps = sheet(tabs.steps);
  const book = id => {
    const key = id === '1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI' ? 'P' : id;
    return {getId:()=>key,getSheetByName:n=>books[key][n]||null};
  };
  const lock = {tryLock:()=>true,releaseLock:()=>{}};
  const cache = fakeCache(), opened = [];
  const ctx = load({SpreadsheetApp:{openById:id => { opened.push(id); return book(id); },getActiveSpreadsheet:()=>null,
    DataValidationCriteria:{VALUE_IN_LIST:'list'}},
    LockService:{getScriptLock:()=>lock}, CacheService:{getScriptCache:()=>cache}});
  return {ctx,pipeline,register,cache,opened};
}

test('web review lists current proposals and recent decisions without adding tabs', () => {
  const w = webWorkbooks(), dashboard = w.ctx.getReviewDashboard();
  assert.equal(dashboard.pending.map(r=>r.id).join(','), '1');
  assert.equal(dashboard.recent.map(r=>r.id).join(','), '4,3');
  // The list carries summaries only; the full record comes when a decision is opened.
  assert.deepEqual(Object.keys(dashboard.pending[0]).sort(),
    ['date','domain','editable','id','pipelineId','question','stage','status','title']);
  // Age in the inbox: the Decision Date once decided, else the item's Updated date.
  assert.equal(dashboard.recent[0].date, '2026-10-20');
  w.pipeline.rows[1][8] = '28/10/2026';
  assert.equal(w.ctx.getReviewDashboard({fresh:true}).pending[0].date, '28/10/2026');
  const record = w.ctx.getDecisionReview('1');
  assert.equal(record.options.map(o=>o.code).join(','), 'B,C');
  assert.equal(record.links.length, 1);
  assert.equal(record.editable, true);
  assert.equal(w.ctx.getDecisionReview('3').editable, false);
  assert.throws(() => w.ctx.getDecisionReview('99'), /Expected one Decision ID 99; found 0/);
});
test('lists are cached briefly, in chunks under 100 KB, and Refresh reads the sheets again', () => {
  const w = webWorkbooks();
  assert.equal(w.ctx.getReviewDashboard().cachedAt, 0);
  w.register.rows[3][5] = 'Changed in the sheet';
  const cached = w.ctx.getReviewDashboard();
  assert.ok(cached.cachedAt > 0);
  assert.equal(cached.recent[0].question, 'Should we own sending?');
  assert.equal(w.ctx.getReviewDashboard({fresh: true}).recent[0].question, 'Changed in the sheet');
  // A list larger than one cache value is split; every chunk stays under the limit (fakeCache checks it).
  for (let i = 0; i < 400; i++)
    w.pipeline.rows.push([String(100 + i), 'Item ' + i + ' – ' + '€'.repeat(150), 'Inbox', 'Stage 0', '', 'No action',
      'Codex', '', '', '', 'Horology', '', 'Idea', 'Local', 'Ünïcode reason '.repeat(30), '']);
  const fresh = w.ctx.getPipelineOverview({fresh: true});
  assert.equal(fresh.rows.length, 402);
  assert.ok(Object.keys(w.cache.store).filter(k => k.startsWith('pipelineOverview:')).length > 1);
  assert.equal(w.ctx.getPipelineOverview().rows.length, 402);
  assert.ok(w.ctx.getPipelineOverview().cachedAt > 0);
});
test('every write from the page clears the cached lists', () => {
  const w = webWorkbooks();
  const fill = () => { w.ctx.getReviewDashboard(); w.ctx.getPipelineOverview(); assert.ok(w.cache.store.reviewDashboard && w.cache.store.pipelineOverview); };
  const cleared = () => assert.ok(!w.cache.store.reviewDashboard && !w.cache.store.pipelineOverview);
  fill();
  w.ctx.submitDecisionReview({decisionId:'1',version:w.ctx.getDecisionReview('1').version,action:'rework',note:'More detail.'});
  cleared(); fill();
  w.ctx.updatePipelineItemFromWeb({pipelineId:'22',version:w.ctx.getPipelineItem('22').version,fields:{Title:'Renamed'}});
  cleared(); fill();
  w.ctx.addPipelineItemFromWeb({Title:'New idea',Domain:'Horology',Type:'Idea','Agent status':'No action','Agent type':'Unassigned'});
  cleared(); fill();
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({pipelineId:'22',version:'old',fields:{}}), /changed since/);
  cleared();  // also cleared when a save is refused: the page reloads what changed
});
test('a request opens each workbook once', () => {
  const w = webWorkbooks({steps: [['Pipeline ID','Step','Task']], options: [['Decision ID','Code','Summary','Recommended']]});
  w.ctx.getDecisionReview('1');
  assert.deepEqual([...new Set(w.opened)].length, w.opened.length);
});
test('the page arrives with the first Decisions list embedded safely', () => {
  const w = webWorkbooks();
  w.register.rows[3][5] = 'Close it? </script><script>alert(1)</script>';
  let template;
  const output = {setTitle() { return this; }, addMetaTag() { return this; }};
  vm.runInContext('this.HtmlService = h;', Object.assign(w.ctx, {h: {createTemplateFromFile: () =>
    (template = {evaluate: () => output})}}));
  w.ctx.doGet();
  assert.doesNotMatch(template.initialJson, /<\//);
  assert.equal(JSON.parse(template.initialJson).recent[0].question, 'Close it? </script><script>alert(1)</script>');
  w.ctx.CacheService = {getScriptCache: () => { throw Error('cache down'); }};
  w.ctx.doGet();
  assert.equal(template.initialJson, 'null');  // the page loads the list itself and shows any error
});
test('web review accepts a different option and applies the Pipeline transition immediately', () => {
  const w = webWorkbooks(), version = w.ctx.getDecisionReview('1').version;
  const result = w.ctx.submitDecisionReview({decisionId:'1',version,action:'accepted',
    optionCode:'C',wording:'Accepted: build TF-IDF term gap (Option C), after a pilot check.',
    note:'The pilot now needs this feature.'});
  assert.equal(result.saved,true);
  assert.equal(result.applied,true);
  assert.equal(w.register.rows[1][8],'accepted');
  assert.match(w.register.rows[1][7], /Founder reason for Option C/);
  assert.equal(w.pipeline.rows[1][2],'Approved');
  assert.equal(w.pipeline.rows[1][3],'Stage 3');
});
test('web review offers a Completed Stage 4 item\'s proposed decision: accept keeps it, rework reopens it', () => {
  const proposed = () => { const w = webWorkbooks(); w.register.rows[3][8] = 'proposed'; return w; };
  let w = proposed();
  assert.equal(w.ctx.getReviewDashboard().pending.map(r=>r.id).join(','), '1,4');
  let record = w.ctx.getDecisionReview('4');
  assert.equal(record.editable, true);
  assert.equal(record.itemStatus, 'Completed');
  const kept = w.ctx.submitDecisionReview({decisionId:'4',version:record.version,action:'accepted',
    optionCode:'A',wording:'Accepted: stay ESP-delegated (Option A).',note:'Fine as it is.'});
  assert.equal(kept.applied, true);
  assert.equal(kept.warning, '');
  assert.equal(w.register.rows[3][8], 'accepted');
  assert.deepEqual(w.pipeline.writes, []);
  w = proposed(); record = w.ctx.getDecisionReview('4');
  w.ctx.submitDecisionReview({decisionId:'4',version:record.version,action:'rework',note:'Add the costs.'});
  assert.deepEqual(w.pipeline.rows[2].slice(2, 6), ['Rework','Stage 3','Specialist deliverable','Ready']);
});
test('web review rejects stale proposals and requires a reason for an alternative', () => {
  const w = webWorkbooks(), version = w.ctx.getDecisionReview('1').version;
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version:'old',action:'accepted',
    optionCode:'B',wording:'Accepted: measurement spike.'}),/changed since/);
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version,action:'accepted',
    optionCode:'C',wording:'Accepted: build TF-IDF term gap.'}),/short reason/);
  assert.deepEqual(w.register.writes,[]);
});
test('web review requires rework instructions and records them before status', () => {
  const w = webWorkbooks(), version = w.ctx.getDecisionReview('1').version;
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version,action:'rework',note:''}),/instructions/);
  const result = w.ctx.submitDecisionReview({decisionId:'1',version,action:'rework',note:'Compare pilot drafts.'});
  assert.equal(result.applied,true);
  assert.equal(w.register.rows[1][11],'Compare pilot drafts.');
  assert.equal(w.register.rows[1][8],'rework');
  assert.equal(w.pipeline.rows[1][2],'Rework');
});
const DECISION_6 = 'Proposed (Option B): lead with intermediate lifters. Positioning: mechanism-first. ' +
  'Alternatives: A lead with beginners; C lead with coaches as a paid research review; park; reject.';
test('without Options rows, options come from the text, including lettered alternatives', () => {
  const w = webWorkbooks();
  w.register.rows[1][6] = DECISION_6;
  const options = w.ctx.getDecisionReview('1').options;
  assert.equal(options.map(o => o.code).join(','), 'A,B,C');
  assert.equal(options.find(o => o.recommended).code, 'B');
  assert.equal(options[0].context, 'lead with beginners');
  const five = w.ctx.proposalOptions('Proposed: approve stages 1–2 only (Option A): interviews. ' +
    'Alternatives: B approve stages 1–4 (about S$450–1,450), C park, D reject.');
  assert.equal(five.map(o => o.code + (o.recommended ? '*' : '')).join(','), 'A*,B,C,D');
  assert.equal(five[1].context, 'approve stages 1–4 (about S$450–1,450)');
});
test('Options rows replace the parsed text, and planned steps come from the Steps tab', () => {
  const w = webWorkbooks({
    options: [['Decision ID','Code','Summary','Recommended','Key figures'],
      ['1','C','Build TF-IDF term gap','','About $0.50 a plan run\nEffort Medium'],
      ['1','A','Do nothing','',''],['1','B','Measurement spike first','Yes',''],['3','A','Other decision','Yes','']],
    steps: [['Pipeline ID','Step','Task','Specialist','Status'],
      ['14','2','Offline TF-IDF test on 2–3 plans','horology-research','Planned'],
      ['14','1','Read persisted search-quality reports','horology-technical-assessment','Done'],
      ['22','1','Another item','','']]});
  const r = w.ctx.getDecisionReview('1');
  assert.equal(r.options.map(o => o.code).join(','), 'A,B,C');
  assert.equal(r.options.find(o => o.recommended).code, 'B');
  assert.deepEqual([...r.options[2].figures], ['About $0.50 a plan run', 'Effort Medium']);
  assert.equal(r.steps.map(x => x.number + ':' + x.status).join(','), '1:Done,2:Planned');
  const version = r.version;
  const saved = w.ctx.submitDecisionReview({decisionId:'1',version,action:'accepted',optionCode:'B',
    wording:'Accepted: measurement spike first (Option B).',note:''});
  assert.equal(saved.saved, true);
  assert.equal(w.pipeline.rows[1][2], 'Approved');
});
test('without Steps rows, planned steps come from a numbered Next step; reasons become bullets', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][9] = 'Overall question\n1. Demand gate [horology-research]\n2) Current state';
  const r = w.ctx.getDecisionReview('1');
  assert.deepEqual(JSON.parse(JSON.stringify(r.steps.map(x => [x.number, x.task, x.specialist]))),
    [['1', 'Demand gate', 'horology-research'], ['2', 'Current state', '']]);
  assert.deepEqual([...w.ctx.bulletPoints('Costs ~$90 a month; e.g. 250+ readers. Effort Medium.\n- Uncertainty Low')],
    ['Costs ~$90 a month; e.g. 250+ readers.', 'Effort Medium.', 'Uncertainty Low']);
});
test('a decided current decision can be revised: Approved item parked from the page', () => {
  const w = webWorkbooks();
  w.register.rows[1][8] = 'accepted';
  w.pipeline.rows[1][2] = 'Approved'; w.pipeline.rows[1][3] = 'Stage 3'; w.pipeline.rows[1][5] = 'Ready';
  const record = w.ctx.getDecisionReview('1');
  assert.equal(record.revisable, true);
  assert.equal(w.ctx.getDecisionReview('4').revisable, true);
  assert.equal(w.ctx.getDecisionReview('3').revisable, false);  // not current
  assert.throws(() => w.ctx.reviseDecisionReview({decisionId:'1',version:record.version,action:'parked',note:''}), /reason/);
  assert.throws(() => w.ctx.reviseDecisionReview({decisionId:'1',version:'old',action:'parked',note:'Later'}), /changed since/);
  assert.deepEqual(w.register.writes, []);
  const result = w.ctx.reviseDecisionReview({decisionId:'1',version:record.version,action:'parked',note:'No pilot yet.'});
  assert.equal(result.transition, 'revise');
  assert.equal(w.register.rows[1][8], 'parked');
  assert.match(w.register.rows[1][7], /Founder revised accepted to parked on \d\d\/\d\d\/\d{4}: No pilot yet\.$/);
  assert.match(w.register.rows[1][12], /revise .* parked$/);
  assert.deepEqual(w.pipeline.rows[1].slice(2, 6), ['Parked', 'Stage 2', 'Investigation proposal', 'No action']);
  assert.ok(w.pipeline.rows[1][8] instanceof Date);
});
test('revise refuses an item under review or a run in progress, before writing', () => {
  const w = webWorkbooks();
  w.register.rows[1][8] = 'accepted';
  w.pipeline.rows[1][2] = 'Researching';
  const record = w.ctx.getDecisionReview('1');
  assert.equal(record.revisable, false);
  w.pipeline.rows[1][2] = 'Approved';
  const version = w.ctx.getDecisionReview('1').version;
  w.pipeline.rows[1][2] = 'Researching';
  assert.throws(() => w.ctx.reviseDecisionReview({decisionId:'1',version,action:'parked',note:'x'}), /changed since/);
  assert.equal(w.register.writes.length + w.pipeline.writes.length, 0);
});

test('web item form uses live domains and adds a captured row with the next permanent ID', () => {
  const w = webWorkbooks(), data = w.ctx.getPipelineFormData();
  assert.equal(Object.keys(data.domains).join(','),'Article Aggregator,Horology');
  const added = w.ctx.addPipelineItemFromWeb({Title:'New idea',Domain:'Horology'});
  assert.equal(added.id,'23');
  assert.equal(added.stage,'Stage 0');
  assert.equal(w.pipeline.rows[3][1],'New idea');
  assert.equal(w.pipeline.rows[3][2],'Inbox');
  assert.equal(w.pipeline.rows[3][3],'Stage 0');
});
test('web item form rejects invalid Ready items before writing', () => {
  const w = webWorkbooks();
  assert.throws(() => w.ctx.addPipelineItemFromWeb({Title:'Ready idea',Domain:'Horology',
    'Agent status':'Ready','Agent type':'Unassigned'}),/Claude Code, Codex, ChatGPT Work or Hermes/);
  assert.equal(w.pipeline.writes.length,0);
});
test('web item form enforces ChatGPT Work Cloud-only and Hermes Local-only', () => {
  let w = webWorkbooks();
  assert.throws(() => w.ctx.addPipelineItemFromWeb({Title:'Work item',Domain:'Horology',
    'Agent status':'Ready','Agent type':'ChatGPT Work','Run location':'Local',
    'Next step / Research question':'Research'}),/ChatGPT Work uses Run location Cloud only/);
  assert.equal(w.pipeline.writes.length,0);
  w = webWorkbooks();
  assert.throws(() => w.ctx.addPipelineItemFromWeb({Title:'Hermes item',Domain:'Horology',
    'Agent status':'Ready','Agent type':'Hermes','Run location':'Cloud',
    'Next step / Research question':'Run locally'}),/Hermes uses Run location Local only/);
  assert.equal(w.pipeline.writes.length,0);
  w = webWorkbooks();
  assert.equal(w.ctx.addPipelineItemFromWeb({Title:'Work item',Domain:'Horology',
    'Agent status':'Ready','Agent type':'ChatGPT Work','Run location':'Cloud',
    'Next step / Research question':'Research'}).stage,'Stage 1');
  w = webWorkbooks();
  assert.equal(w.ctx.addPipelineItemFromWeb({Title:'Hermes item',Domain:'Horology',
    'Agent status':'Ready','Agent type':'Hermes','Run location':'Local',
    'Next step / Research question':'Run locally'}).stage,'Stage 1');
});
test('Pipeline overview includes every Master row as a light list row and makes no writes', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][14] = 'Why it matters.\n\n' + 'A long reason. '.repeat(40);
  w.pipeline.rows[2][9] = 'Only a next step';
  const rows = w.ctx.getPipelineOverview().rows;
  assert.equal(rows.length,2);
  assert.equal(rows[0].ID,'14');
  assert.equal(rows[1].Status,'Completed');
  assert.ok(rows[0].summary.startsWith('Why it matters. A long reason.') && rows[0].summary.endsWith('…'));
  assert.ok(rows[0].summary.length <= 181);
  assert.equal(rows[1].summary,'Only a next step');
  for (const field of ['Summary / Why','Next step / Research question','Revisit trigger','steps','version'])
    assert.equal(field in rows[0], false, field);
  const item = w.ctx.getPipelineItem('14');
  assert.match(item.sheetUrl,/gid=2040100901&range=A2$/);
  assert.match(item['Summary / Why'],/^Why it matters\.\n\n/);
  assert.equal(item.route,'investigation');
  assert.throws(() => w.ctx.getPipelineItem('99'),/Expected one ID 99; found 0/);
  assert.equal(w.pipeline.writes.length,0);
});
test('Pipeline search finds items by words in their long text, which the list does not carry', () => {
  const w = webWorkbooks();
  w.pipeline.rows[2][15] = 'Revisit when a pilot asks for Postmark sending.';
  assert.deepEqual([...w.ctx.searchPipelineItems('postmark PILOT')],['22']);
  assert.deepEqual([...w.ctx.searchPipelineItems('audience')],['22']);
  assert.deepEqual([...w.ctx.searchPipelineItems('postmark beginners')],[]);
  assert.deepEqual([...w.ctx.searchPipelineItems('  ')],[]);
  assert.throws(() => w.ctx.searchPipelineItems('x'.repeat(121)),/too long/);
});

test('An opened Pipeline item has its Steps-tab rows in order, and none without a tab', () => {
  const w = webWorkbooks({steps: [['Pipeline ID','Step','Task','Specialist','Status'],
    ['22','2','Write the plan','horology-gtm','Planned'],['22','1','Read the research','','Done'],
    ['14','','','','']]});
  assert.deepEqual(JSON.parse(JSON.stringify(w.ctx.getPipelineItem('22').steps.map(s => [s.number, s.task, s.status]))),
    [['1','Read the research','Done'],['2','Write the plan','Planned']]);
  assert.equal(w.ctx.getPipelineItem('14').steps.length, 0);
  assert.equal(webWorkbooks().ctx.getPipelineItem('14').steps.length, 0);
  assert.equal(w.pipeline.writes.length, 0);
});
test('Pipeline edit saves fields by ID and moves an Inbox Ready item to Stage 1', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][2] = 'Inbox'; w.pipeline.rows[1][3] = 'Stage 0';
  const item = w.ctx.getPipelineItem('14');
  const result = w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields:{
    'Title':'Sharper title','Type':'Research','Summary / Why':'A clear reason',
    'Next step / Research question':'Investigate the gap','Revisit trigger':'After pilot',
    'Agent status':'Ready','Agent type':'Codex','Run location':'Local'
  }});
  assert.equal(result.changed,true);
  assert.equal(w.pipeline.rows[1][1],'Sharper title');
  assert.equal(w.pipeline.rows[1][3],'Stage 1');
  assert.equal(w.pipeline.rows[1][5],'Ready');
  assert.equal(w.pipeline.rows[1][10],'Article Aggregator');
  assert.ok(w.pipeline.rows[1][8] instanceof Date);
});
test('Pipeline edit rejects stale data, forbidden fields and invalid Ready moves', () => {
  const w = webWorkbooks(), item = w.ctx.getPipelineItem('14');
  const base = {pipelineId:'14',version:item.version,fields:{
    'Title':'Changed','Agent status':'Ready','Agent type':'Codex',
    'Run location':'Local','Next step / Research question':'Investigate'
  }};
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({...base,version:'old'}),/changed since/);
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({...base,fields:{...base.fields,Status:'Completed'}}),
    /cannot be edited/);
  assert.throws(() => w.ctx.updatePipelineItemFromWeb(base),/Agent status change is not allowed/);
  assert.equal(w.pipeline.writes.length,0);
});
test('Pipeline edit enforces the harness Run location', () => {
  const w = webWorkbooks(), item = w.ctx.getPipelineItem('14');
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,
    fields:{'Agent type':'ChatGPT Work','Run location':'Local'}}),/ChatGPT Work uses Run location Cloud only/);
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,
    fields:{'Agent type':'Hermes','Run location':'Cloud'}}),/Hermes uses Run location Local only/);
  assert.equal(w.pipeline.writes.length,0);
});
test('Pipeline edit makes a Fix item Ready at Stage 1, and an In progress one Ready again at Stage 3', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][2] = 'Inbox'; w.pipeline.rows[1][3] = 'Stage 0';
  let item = w.ctx.getPipelineItem('14');
  const fields = {'Type':'Fix','Agent status':'Ready','Agent type':'Claude Code','Run location':'Cloud',
    'Next step / Research question':'Fix the broken link'};
  assert.equal(w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields}).stage,'Stage 1');
  w.pipeline.rows[1][2] = 'In progress'; w.pipeline.rows[1][3] = 'Stage 3'; w.pipeline.rows[1][5] = 'No action';
  item = w.ctx.getPipelineItem('14');
  assert.equal(item.route,'implementation');
  assert.equal(w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields}).stage,'Stage 3');
  assert.equal(w.pipeline.rows[1][5],'Ready');
  w.pipeline.rows[1][5] = 'No action';
  item = w.ctx.getPipelineItem('14');
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,
    fields:{...fields,'Type':'Research'}}),/Agent status change is not allowed/);
});
test('Pipeline edit leaves Stage 3 unchanged and avoids writes when nothing changed', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][2] = 'Approved'; w.pipeline.rows[1][3] = 'Stage 3';
  const item = w.ctx.getPipelineItem('14');
  const unchanged = w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields:{}});
  assert.equal(unchanged.changed,false);
  assert.equal(w.pipeline.writes.length,0);
  const moved = w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields:{
    'Agent status':'Ready','Next step / Research question':'Produce the deliverable'
  }});
  assert.equal(moved.stage,'Stage 3');
  assert.equal(w.pipeline.rows[1][5],'Ready');
});

const NEWSLETTER_DOMAINS = [['Domain','Entities'],['Article Aggregator',''],['Horology',''],
  ['Newsletter','WIP_exercise science, Weekly digest']];
test('Quick edit changes Domain and Entity by ID, validated against the Domains tab', () => {
  const w = webWorkbooks({domains: NEWSLETTER_DOMAINS});
  let item = w.ctx.getPipelineItem('14');
  const quick = fields => w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields});
  const result = quick({'Agent status':'No action','Agent type':'Claude Code','Run location':'Cloud',
    'Domain':'Newsletter','Entity':'WIP_exercise science'});
  assert.equal(result.changed,true);
  assert.deepEqual(w.pipeline.rows[1].slice(10,14),['Newsletter','WIP_exercise science','Research','Cloud']);
  assert.equal(w.pipeline.rows[1][6],'Claude Code');
  assert.equal(w.pipeline.rows[1][1],'TF-IDF and SERP-grounded drafting');  // fields not sent are kept
  assert.equal(w.pipeline.rows[2][10],'Article Aggregator');  // other rows untouched
  // A domain with no entities clears the Entity.
  item = w.ctx.getPipelineItem('14');
  quick({'Domain':'Horology','Entity':'WIP_exercise science'});
  assert.deepEqual(w.pipeline.rows[1].slice(10,12),['Horology','']);
});
test('Quick edit rejects an unknown domain, an entity of another domain, stale data and a disallowed move', () => {
  const w = webWorkbooks({domains: NEWSLETTER_DOMAINS}), item = w.ctx.getPipelineItem('14');
  const quick = (fields, version = item.version) =>
    () => w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version,fields});
  assert.throws(quick({'Domain':'Gardening'}),/Choose a domain from the Domains tab/);
  assert.throws(quick({'Domain':'Newsletter','Entity':'Shopify store'}),/Shopify store is not an entity of Newsletter/);
  assert.throws(quick({'Domain':'Newsletter'},'old'),/changed since/);
  // Item 14 is Awaiting decision, so it cannot be made Ready from here.
  assert.throws(quick({'Agent status':'Ready','Agent type':'Codex','Run location':'Local'}),
    /Agent status change is not allowed/);
  assert.throws(quick({'Agent type':'Robot'}),/Agent type must be one of/);
  assert.equal(w.pipeline.writes.length,0);
  // An unchanged legacy Domain that is no longer on the Domains tab does not block other edits.
  w.pipeline.rows[1][10] = 'Retired domain';
  const legacy = w.ctx.getPipelineItem('14');
  w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:legacy.version,fields:{'Run location':'Cloud','Domain':'Retired domain'}});
  assert.equal(w.pipeline.rows[1][13],'Cloud');
});

// The page script in a minimal browser: elements accept anything, and server calls are recorded.
function page({embedded = null, hash = ''} = {}) {
  const html = fs.readFileSync(path.join(dir,'Review.html'),'utf8');
  assert.match(html, /<script type="application\/json" id="initial-data"><\?!= initialJson \?><\/script>/);
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const element = () => new Proxy(function () {}, {
    get: (target, key) => key === 'textContent' || key === 'value' ? '' : key === Symbol.iterator ? [][Symbol.iterator] : element(),
    set: () => true, apply: () => element()});
  const calls = [], pushed = [];
  const runner = () => {
    const handlers = {};
    return new Proxy({}, {get: (target, key) => {
      if (key === 'withSuccessHandler') return fn => { handlers.ok = fn; return runner.current; };
      if (key === 'withFailureHandler') return fn => { handlers.fail = fn; return runner.current; };
      return (...args) => calls.push({method: key, args, ok: handlers.ok, fail: handlers.fail});
    }});
  };
  const google = {script: {
    get run() { runner.current = runner(); return runner.current; },
    url: {getLocation: fn => fn({hash})},
    history: {push: (state, params, h) => pushed.push(h), setChangeHandler: () => {}}}};
  const initial = {textContent: JSON.stringify(embedded)};
  const ctx = vm.createContext({window: {scrollTo() {}}, setTimeout: fn => fn(), clearTimeout() {},
    document: {getElementById: id => id === 'initial-data' ? initial : element()},
    HorologyUi: {element: () => element()}, google});
  vm.runInContext(script, ctx);
  return {ctx, calls, pushed, run: code => JSON.parse(vm.runInContext('JSON.stringify(' + code + ')', ctx))};
}

test('the Decisions inbox lists proposals and history, newest first, and search narrows both', () => {
  const {run, ctx} = page();
  vm.runInContext("dashboard={pending:[{id:'5',pipelineId:'22',editable:true,title:'Audience lists'},{id:'7',pipelineId:'30',editable:true,title:'Pricing'}],recent:[{id:'4',pipelineId:'22',editable:false,title:'Audience lists'},{id:'3',pipelineId:'14',editable:false,title:'TF-IDF drafting',question:'Which content feature?'}]}", ctx);
  const inbox = run('decisionInbox()');
  assert.deepEqual(inbox.pending.map(r => r.id), ['7','5']);
  assert.deepEqual(inbox.history.map(r => r.id), ['4','3']);
  const searched = run("decisionInbox('content FEATURE')");
  assert.deepEqual([searched.pending.length, searched.history.map(r => r.id)], [0, ['3']]);
});
test('decision age reads both sheet date formats', () => {
  const {run} = page();
  const now = 'new Date(2026,9,30,15).getTime()';
  assert.equal(run(`ageLabel('2026-10-27',${now})`), '3d');
  assert.equal(run(`ageLabel('30/10/2026',${now})`), 'today');
  assert.equal(run(`ageLabel('01/06/2026',${now})`), '5mo');
  assert.equal(run(`ageLabel('',${now})`), '');
  assert.equal(run(`ageLabel('soon',${now})`), '');
});
test('the Pipeline board places each item in one column, Done most recent first', () => {
  const {run} = page();
  const rows = JSON.stringify([
    {ID:'1',Status:'Inbox',Stage:'Stage 0'}, {ID:'2',Status:'Researching',Stage:'Stage 1'},
    {ID:'3',Status:'In progress',Stage:'Stage 1'}, {ID:'4',Status:'Awaiting decision',Stage:'Stage 2'},
    {ID:'5',Status:'Approved',Stage:'Stage 3'}, {ID:'6',Status:'In progress',Stage:'Stage 3'},
    {ID:'7',Status:'Rework',Stage:'Stage 3'}, {ID:'8',Status:'Completed',Updated:'01/10/2026'},
    {ID:'9',Status:'Completed',Updated:'28/10/2026'}, {ID:'10',Status:'Parked'},
    {ID:'11',Status:'Rejected'}, {ID:'12',Status:'',Stage:''}, {ID:'13',Status:'Rework',Stage:'Stage 1'}]);
  const groups = run(`(g => Object.fromEntries(Object.entries(g).map(([k,v]) => [k,v.map(r => r.ID)])))(boardGroups(${rows}))`);
  assert.deepEqual(groups, {inbox:['1','12'], investigating:['2','3','13'], waiting:['4'],
    building:['5','6','7'], done:['9','8'], parked:['10'], rejected:['11']});
});
test('the Type filter groups Build and Investigate types', () => {
  const {run} = page();
  const rows = JSON.stringify(['Feature','Enhancement','Refactor','Fix','Research','Idea','Plan','Direction','']
    .map((Type, i) => ({ID: String(i), Type})));
  assert.deepEqual(run(`filteredPipelineRows(${rows}, '', {Type:'@build'}).map(r => r.Type)`),
    ['Feature','Enhancement','Refactor','Fix']);
  assert.deepEqual(run(`filteredPipelineRows(${rows}, '', {Type:'@investigate'}).map(r => r.Type)`),
    ['Research','Idea','Plan','Direction','']);
  assert.deepEqual(run(`filteredPipelineRows(${rows}, '', {Type:'Fix'}).map(r => r.Type)`), ['Fix']);
});
test('Pipeline search and filters combine', () => {
  const {run} = page();
  const rows = "[{ID:'1',Title:'Audience',Domain:'Article Aggregator',Entity:'',Type:'Research',Status:'Inbox',Stage:'','Agent status':'No action','Agent type':'Codex','Run location':'Local',summary:'Lists for pilots'},{ID:'2',Title:'Campaign',Domain:'Horology',Entity:'',Type:'Plan',Status:'Approved',Stage:'Stage 3','Agent status':'Ready','Agent type':'Claude Code','Run location':'Cloud',summary:''}]";
  const filtered = run(`filteredPipelineRows(${rows}, 'aud', {Domain:'Article Aggregator',Stage:'__blank__'})`);
  assert.equal(filtered.length,1);
  assert.equal(filtered[0].ID,'1');
  assert.equal(run(`filteredPipelineRows(${rows}, 'pilots audience', {})`).length, 1);  // words in any field
  assert.equal(run(`filteredPipelineRows(${rows}, 'postmark', {})`).length, 0);
  // Items whose long text matched on the server are added, still within the filters.
  assert.deepEqual(run(`filteredPipelineRows(${rows}, 'postmark', {}, new Set(['2'])).map(r => r.ID)`), ['2']);
  assert.equal(run(`filteredPipelineRows(${rows}, 'postmark', {Status:'Inbox'}, new Set(['2'])).length`), 0);
});
test('Pipeline sort: sheet order, needs attention first, newest, recently updated', () => {
  const {run} = page();
  const rows = "[{ID:'9',Status:'Completed',Updated:'02/11/2026'},{ID:'12',Status:'Inbox',Updated:'30/10/2026'},{ID:'10',Status:'Awaiting decision',Updated:'01/12/2025'}]";
  assert.deepEqual(run(`sortedPipelineRows(${rows},'sheet').map(r => r.ID)`), ['9','12','10']);
  assert.deepEqual(run(`sortedPipelineRows(${rows},'status').map(r => r.ID)`), ['10','12','9']);
  assert.deepEqual(run(`sortedPipelineRows(${rows},'newest').map(r => r.ID)`), ['12','10','9']);
  assert.deepEqual(run(`sortedPipelineRows(${rows},'updated').map(r => r.ID)`), ['9','12','10']);
});
test('views are kept in the URL hash, and unknown hashes fall back to Decisions', () => {
  const {run} = page();
  assert.deepEqual(run("parseHash('#item/51')"), {view:'item',id:'51'});
  assert.deepEqual(run("parseHash('decision/9')"), {view:'decision',id:'9'});
  assert.deepEqual(run("parseHash('pipeline')"), {view:'pipeline'});
  assert.deepEqual(run("parseHash('item')"), {view:'pipeline'});
  for (const bad of ['', 'graph', 'item/<script>', 'decision/1/2'])
    assert.deepEqual(run(`parseHash(${JSON.stringify(bad)})`), {view:'decisions'}, bad);
  assert.equal(run("hashFor({view:'item',id:'51'})"), 'item/51');
});
test('the page paints the embedded Decisions list, then loads the Pipeline list in the background', () => {
  const {calls} = page({embedded: {pending: [], recent: []}});
  assert.deepEqual(calls.map(c => c.method), ['getPipelineOverview']);
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0].args)), [{fresh: false}]);
  const without = page();
  assert.deepEqual(without.calls.map(c => c.method), ['getReviewDashboard', 'getPipelineOverview']);
});
test('a linked item or decision is read fresh when opened, and opening one updates the hash', () => {
  const item = page({embedded: {pending: [], recent: []}, hash: 'item/51'});
  assert.deepEqual(item.calls.map(c => c.method + ':' + c.args.join()), ['getPipelineFormData:', 'getPipelineItem:51', 'getPipelineOverview:[object Object]']);
  const decision = page({embedded: {pending: [], recent: []}, hash: 'decision/9'});
  assert.equal(decision.calls[0].method + ':' + decision.calls[0].args[0], 'getDecisionReview:9');
  vm.runInContext("show({view:'item',id:'14'},true)", decision.ctx);
  assert.deepEqual(decision.pushed, ['item/14']);
  // A failed load leaves an error with a retry, not a blank page.
  const failed = decision.calls.find(c => c.method === 'getPipelineItem');
  failed.fail(Error('Expected one ID 14; found 0.'));
});

test('the item view loads the quick-edit fields and offers only the allowed Agent status moves', () => {
  const opened = page({embedded: {pending: [], recent: []}, hash: 'item/65'});
  const load = opened.calls.find(c => c.method === 'getPipelineItem');
  load.ok({ID:'65',Title:'Quick edit',Status:'Inbox','Agent status':'No action',Domain:'Horology',
    readyStatuses:['Inbox','Rework','Approved','In progress'],steps:[],version:'v'});
  const fields = opened.calls.filter(c => c.method === 'getPipelineFormData');
  assert.equal(fields.length, 1);
  // The options were requested alongside the item, so the selects fill as soon as the item renders.
  fields[0].ok({domains:{Horology:[]},options:{'Agent type':['Claude Code'],'Run location':['Local']}});
  const {run} = opened;
  assert.equal(opened.calls.filter(c => c.method === 'getPipelineFormData').length, 1);
  assert.equal(run("formData !== null"), true);
  // The Domain hint is placed after its control (the page's DOM is a stub, so check the source).
  const html = fs.readFileSync(path.join(dir,'Review.html'),'utf8');
  assert.match(html, /\.field small\.hint-after \{ margin:6px 0 0; \}/);
  assert.match(html, /domain\.hint\.className = 'hint-after'; domain\.wrap\.appendChild\(domain\.hint\);/);
  assert.deepEqual(run("agentStatusChoices({Status:'In progress','Agent status':'No action',readyStatuses:['Inbox','In progress']})"),
    ['No action','Plan','Ready']);
  assert.deepEqual(run("agentStatusChoices({Status:'Awaiting decision','Agent status':'No action'})"), ['No action']);
  assert.deepEqual(run("agentStatusChoices({Status:'Inbox','Agent status':'Plan'})"), ['Plan','Ready']);
  assert.deepEqual(run("withCurrent(['Horology'],'Retired domain')"), ['Retired domain','Horology']);
  assert.deepEqual(run("withCurrent(['Horology'],'Horology')"), ['Horology']);
});
test('a long cell reads as spaced paragraphs, starting a new one at each labelled sentence', () => {
  const {run} = page({embedded: {pending: [], recent: []}});
  const long = 'A'.repeat(200) + '. Second sentence keeps the first chunk going past the limit. Third starts a new one.';
  assert.deepEqual(run(`paragraphChunks(${JSON.stringify(long)})`),
    ['A'.repeat(200) + '. Second sentence keeps the first chunk going past the limit.', 'Third starts a new one.']);
  assert.deepEqual(run(`paragraphChunks('Proposed: park it (Option A). Keep the steps, e.g. 2 and 3. Alternatives: B build. If accepted, plan it.\\n\\nNew line.')`),
    ['Proposed: park it (Option A). Keep the steps, e.g. 2 and 3.', 'Alternatives: B build.', 'If accepted, plan it.', 'New line.']);
});
test('a numbered step stays one paragraph with its marker (HOR-15: items 39 and 55)', () => {
  const {run} = page({embedded: {pending: [], recent: []}});
  // Item 39's Next step: step text that opens with a labelled phrase used to leave "1." on its own.
  const item39 = 'Founder decision on Decision 6: accept the proposed direction, rework, park or reject. Steps 1–4 done on 28/10/2026; retained below for history.\n' +
    '1. Reader demand: which audience (gym beginners and intermediate trainees, strength and performance enthusiasts, coaches and fitness-curious readers) shows the strongest interest in evidence-based exercise science, what questions do they ask, and what depth of detail do they want? Answered = ranked audience hypotheses with sourced demand signals and a stated lead audience, or \'no clear demand\'. [horology-research]\n' +
    '4. Direction and plan: using steps 1–3, propose the target readership. Concept level only; brand name, cadence, distribution and monetisation stay deferred. Answered = concise proposed direction for founder review. [horology-gtm]\n\n' +
    'Read the entity\'s registered 00_Foundations Agent reference documents first. Treat them as founder intent.';
  const chunks = run(`paragraphChunks(${JSON.stringify(item39)})`);
  assert.deepEqual(chunks.map(c => c.slice(0, 18)), ['Founder decision o', '1. Reader demand: ',
    '4. Direction and p', 'Read the entity\'s ']);
  assert.ok(chunks[1].endsWith('[horology-research]'));
  // Item 55's steps, which were once a numbered Next step: long, labelled and ending "Stop here until answered."
  const item55 = '3. Implementation question, one decision for Groups B and C: run select name, model_default from system_prompts where model_default is not null; then ask the founder (a) whether prompt defaults should start winning for the Group B features (drafting, digest, article cards, analysis, curation) and (b) which Group C features get a plan role. Stop here until answered.\n' +
    '4. After the decision: move the Group B and C sites as decided and delete the 4 *_MODEL_FALLBACK constants.\n' +
    '5) Check: outside tests and alembic/versions, "gemini-2.5-flash-lite" remains only in config.py; run the unit suite.\n' +
    '- Note: a bulleted line keeps its marker too.';
  assert.deepEqual(run(`paragraphChunks(${JSON.stringify(item55)})`), item55.split('\n'));
  // A number inside prose, or a year, is not a marker.
  assert.deepEqual(run(`paragraphChunks('2026 was busy. Check: the list.')`), ['2026 was busy.', 'Check: the list.']);
});

test('writes find the row by ID, not by the position read earlier', () => {
  const w = workbooks();
  // Another writer inserts a row above item 42 after the read (HOR-6: item 41's run wrote item 40's row).
  const getDataRange = w.pipeline.getDataRange;
  let moved = false;
  w.pipeline.getDataRange = () => {
    const range = getDataRange();
    if (!moved) { moved = true; return range; }  // the run's first read sees the old order
    if (w.pipeline.rows[1][0] !== '41') w.pipeline.rows.splice(1, 0, ['41', 'Inserted', 'Inbox', 'Stage 0', '', 'No action', 'Codex', '', '']);
    return getDataRange();
  };
  w.ctx.applyDecisions();
  const row42 = w.pipeline.rows.find(r => r[0] === '42'), row41 = w.pipeline.rows.find(r => r[0] === '41');
  assert.deepEqual(row42.slice(2, 6), ['Approved', 'Stage 3', 'Investigation proposal', 'Ready']);
  assert.deepEqual(row41.slice(2, 6), ['Inbox', 'Stage 0', '', 'No action']);  // untouched
});
test('a row whose ID disappeared or is duplicated is not written', () => {
  const w = workbooks();
  w.pipeline.rows.push(['42', 'Copy', 'Awaiting decision', 'Stage 2', 'Investigation proposal', 'No action', 'Claude Code', 'D-3', '']);
  assert.throws(() => w.ctx.applyDecisions(), /appears 2 times; nothing was written/);
  assert.equal(w.pipeline.writes.length, 0);
});

console.log(passed + ' tests passed');
