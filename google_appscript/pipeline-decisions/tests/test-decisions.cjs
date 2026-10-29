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
const {decide} = load();

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

function webWorkbooks() {
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
  const domains = sheet([['Domain','Entities'],['Article Aggregator',''],['Horology','']]);
  const books = {P:{Master:pipeline,Registers:registers,Domains:domains},D:{Master:register}};
  const book = id => {
    const key = id === '1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI' ? 'P' : id;
    return {getId:()=>key,getSheetByName:n=>books[key][n]||null};
  };
  const lock = {tryLock:()=>true,releaseLock:()=>{}};
  const ctx = load({SpreadsheetApp:{openById:book,getActiveSpreadsheet:()=>null,
    DataValidationCriteria:{VALUE_IN_LIST:'list'}},
    LockService:{getScriptLock:()=>lock}});
  return {ctx,pipeline,register};
}

test('web review lists current proposals and recent decisions without adding tabs', () => {
  const w = webWorkbooks(), dashboard = w.ctx.getReviewDashboard();
  assert.equal(dashboard.pending.map(r=>r.id).join(','), '1');
  assert.equal(dashboard.recent.map(r=>r.id).join(','), '4,3');
  assert.equal(dashboard.pending[0].options.map(o=>o.code).join(','), 'B,C');
  assert.equal(dashboard.pending[0].links.length, 1);
});
test('web review accepts a different option and applies the Pipeline transition immediately', () => {
  const w = webWorkbooks(), version = w.ctx.getReviewDashboard().pending[0].version;
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
test('web review rejects stale proposals and requires a reason for an alternative', () => {
  const w = webWorkbooks(), version = w.ctx.getReviewDashboard().pending[0].version;
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version:'old',action:'accepted',
    optionCode:'B',wording:'Accepted: measurement spike.'}),/changed since/);
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version,action:'accepted',
    optionCode:'C',wording:'Accepted: build TF-IDF term gap.'}),/short reason/);
  assert.deepEqual(w.register.writes,[]);
});
test('web review requires rework instructions and records them before status', () => {
  const w = webWorkbooks(), version = w.ctx.getReviewDashboard().pending[0].version;
  assert.throws(()=>w.ctx.submitDecisionReview({decisionId:'1',version,action:'rework',note:''}),/instructions/);
  const result = w.ctx.submitDecisionReview({decisionId:'1',version,action:'rework',note:'Compare pilot drafts.'});
  assert.equal(result.applied,true);
  assert.equal(w.register.rows[1][11],'Compare pilot drafts.');
  assert.equal(w.register.rows[1][8],'rework');
  assert.equal(w.pipeline.rows[1][2],'Rework');
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
    'Agent status':'Ready','Agent type':'Unassigned'}),/Claude Code or Codex/);
  assert.equal(w.pipeline.writes.length,0);
});
test('Pipeline overview includes every Master row with a direct link and makes no writes', () => {
  const w = webWorkbooks(), rows = w.ctx.getPipelineOverview();
  assert.equal(rows.length,2);
  assert.equal(rows[0].ID,'14');
  assert.equal(rows[1].Status,'Completed');
  assert.match(rows[0].sheetUrl,/gid=2040100901&range=A2$/);
  assert.equal(w.pipeline.writes.length,0);
});

test('Pipeline edit saves fields by ID and moves an Inbox Ready item to Stage 1', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][2] = 'Inbox'; w.pipeline.rows[1][3] = 'Stage 0';
  const item = w.ctx.getPipelineOverview()[0];
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
  const w = webWorkbooks(), item = w.ctx.getPipelineOverview()[0];
  const base = {pipelineId:'14',version:item.version,fields:{
    'Title':'Changed','Agent status':'Ready','Agent type':'Codex',
    'Run location':'Local','Next step / Research question':'Investigate'
  }};
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({...base,version:'old'}),/changed since/);
  assert.throws(() => w.ctx.updatePipelineItemFromWeb({...base,fields:{...base.fields,Domain:'Horology'}}),
    /cannot be edited/);
  assert.throws(() => w.ctx.updatePipelineItemFromWeb(base),/Agent status change is not allowed/);
  assert.equal(w.pipeline.writes.length,0);
});
test('Pipeline edit leaves Stage 3 unchanged and avoids writes when nothing changed', () => {
  const w = webWorkbooks();
  w.pipeline.rows[1][2] = 'Approved'; w.pipeline.rows[1][3] = 'Stage 3';
  const item = w.ctx.getPipelineOverview()[0];
  const unchanged = w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields:{}});
  assert.equal(unchanged.changed,false);
  assert.equal(w.pipeline.writes.length,0);
  const moved = w.ctx.updatePipelineItemFromWeb({pipelineId:'14',version:item.version,fields:{
    'Agent status':'Ready','Next step / Research question':'Produce the deliverable'
  }});
  assert.equal(moved.stage,'Stage 3');
  assert.equal(w.pipeline.rows[1][5],'Ready');
});

test('workspace groups decisions by item and combines search with Pipeline filters', () => {
  const html = fs.readFileSync(path.join(dir,'Review.html'),'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const runner = {withSuccessHandler() { return this; },
    withFailureHandler() { return this; }, getReviewDashboard() {}};
  const ctx = vm.createContext({document:{getElementById:()=>({})},
    HorologyUi:{element:()=>({})},google:{script:{run:runner}}});
  vm.runInContext(script,ctx);
  const groups = JSON.parse(vm.runInContext("dashboard={pending:[{id:'5',pipelineId:'22',editable:true}],recent:[{id:'4',pipelineId:'22',editable:false},{id:'3',pipelineId:'14',editable:false}]};JSON.stringify(decisionGroups())",ctx));
  assert.equal(groups.pending.length,1);
  assert.equal(groups.pending[0].length,2);
  assert.equal(groups.history[0][0].pipelineId,'14');
  const filtered = JSON.parse(vm.runInContext("JSON.stringify(filteredPipelineRows([{ID:'1',Title:'Audience',Domain:'Article Aggregator',Entity:'',Type:'Research',Status:'Inbox',Stage:'', 'Agent status':'No action','Agent type':'Codex','Run location':'Local','Summary / Why':'','Next step / Research question':''},{ID:'2',Title:'Campaign',Domain:'Horology',Entity:'',Type:'Plan',Status:'Approved',Stage:'Stage 3','Agent status':'Ready','Agent type':'Claude Code','Run location':'Cloud','Summary / Why':'','Next step / Research question':''}], 'aud', {Domain:'Article Aggregator',Stage:'__blank__'}))",ctx));
  assert.equal(filtered.length,1);
  assert.equal(filtered[0].ID,'1');
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
