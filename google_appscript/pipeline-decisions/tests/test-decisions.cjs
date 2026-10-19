// Offline tests: the decision rules, and the run against in-memory sheets. No Google access.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const dir = path.join(__dirname, '../src');
const source = fs.readdirSync(dir).filter(n => n.endsWith('.js')).sort().map(n => fs.readFileSync(path.join(dir, n), 'utf8')).join('\n');

function load(extra = {}) {
  const ctx = vm.createContext({console: {log: () => {}}, Date, JSON, Object, Array, String, Error, ...extra});
  vm.runInContext(source, ctx);
  return ctx;
}

const item = (o = {}) => ({'ID': '42', 'Status': 'Awaiting decision', 'Stage': 'Stage 2', 'Review stage': 'Stage 1',
  'Agent status': 'No action', 'Agent type': 'Claude Code', 'Current decision ID': 'D-3', ...o});
const decision = (o = {}) => ({'Decision ID': 'D-3', 'Pipeline ID': '42', 'Status': 'accepted', 'Review stage': 'Stage 1',
  'Rework instructions': '', ...o});

let passed = 0;
function test(name, fn) { fn(); passed++; console.log('PASS ' + name); }
const {decide} = load();

test('accepting a Stage 1 review approves the item and makes it Ready', () => {
  const r = decide(item(), [decision()]);
  assert.equal(r.transition, 'accept-stage-1');
  assert.deepEqual({...r.set}, {'Status': 'Approved', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
});
test('accepting a Stage 3 review hands it off without queuing more work', () => {
  const r = decide(item({'Review stage': 'Stage 3'}), [decision({'Review stage': 'Stage 3'})]);
  assert.deepEqual({...r.set}, {'Status': 'Handed off', 'Stage': 'Stage 3', 'Agent status': 'No action'});
});
test('rework returns to the reviewed stage and needs instructions', () => {
  assert.match(decide(item(), [decision({'Status': 'rework'})]).error, /Rework instructions/);
  const r = decide(item({'Review stage': 'Stage 3'}), [decision({'Status': 'Rework', 'Review stage': 'Stage 3', 'Rework instructions': 'Add costs'})]);
  assert.deepEqual({...r.set}, {'Status': 'Rework', 'Stage': 'Stage 3', 'Agent status': 'Ready'});
});
test('park and reject stop the item', () => {
  assert.equal(decide(item(), [decision({'Status': 'parked'})]).set['Status'], 'Parked');
  assert.equal(decide(item(), [decision({'Status': 'rejected'})]).set['Agent status'], 'No action');
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
  assert.match(decide(item({'Review stage': 'Stage 3'}), [decision()]).error, /reviewing Stage 3/);
  assert.match(decide(item(), [decision({'Review stage': 'Stage 2'})]).error, /Review stage/);
});

// The run, against fake workbooks.
function sheet(rows) {
  const writes = [];
  return {rows, writes, getDataRange: () => ({getDisplayValues: () => rows.map(r => r.map(String))}),
    getRange: (r, c) => ({setValue: v => { writes.push([r, c, v]); rows[r - 1][c - 1] = v; }})};
}
function workbooks() {
  const pipeline = sheet([
    ['ID', 'Title', 'Status', 'Stage', 'Review stage', 'Agent status', 'Agent type', 'Current decision ID', 'Updated'],
    ['42', 'Pricing', 'Awaiting decision', 'Stage 2', 'Stage 1', 'No action', 'Claude Code', 'D-3', ''],
    ['43', 'Brand', 'Awaiting decision', 'Stage 2', 'Stage 1', 'No action', 'Codex', 'D-4', ''],
    ['44', 'Old', 'Researching', 'Stage 1', '', 'No action', 'Codex', 'D-1', '']]);
  const register = sheet([
    ['Decision ID', 'Pipeline ID', 'Status', 'Review stage', 'Rework instructions', 'Decision Date'],
    ['D-1', '44', 'accepted', 'Stage 1', '', '2026-10-01'],
    ['D-3', '42', 'accepted', 'Stage 1', '', ''],
    ['D-4', '43', 'proposed', 'Stage 1', '', '']]);
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
  assert.deepEqual(w.pipeline.rows[1].slice(2, 6), ['Approved', 'Stage 3', 'Stage 1', 'Ready']);
  assert.ok(w.pipeline.rows[1][8] instanceof Date);
  assert.ok(w.register.rows[2][5] instanceof Date);  // Decision Date filled in
  assert.equal(w.register.rows[1][5], '2026-10-01');  // an existing date is kept
  assert.deepEqual(w.pipeline.rows[2].slice(2, 6), ['Awaiting decision', 'Stage 2', 'Stage 1', 'No action']);
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

console.log(passed + ' tests passed');
