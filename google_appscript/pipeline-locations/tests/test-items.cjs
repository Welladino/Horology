// Offline tests: the Add Pipeline item rules, and adding a row to a fake Master. No Google access.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const dir = path.join(__dirname, '../src');
const ctx = vm.createContext({console, JSON, Object, Array, String, Number, Error, Date, Math});
['ItemRules.js', 'Items.js'].forEach(f => vm.runInContext(fs.readFileSync(path.join(dir, f), 'utf8'), ctx));
const plain = x => JSON.parse(JSON.stringify(x));

let passed = 0;
function test(name, fn) { fn(); passed++; console.log('PASS ' + name); }

const domains = {Horology: [], Ecommerce: ['Caps', 'Mugs']};
const today = new Date(2026, 9, 19);
const add = (form, ids = ['1', '2', '7', 'x']) => ctx.itemValues(form, domains, vm.runInContext('ITEM_OPTIONS', ctx), ids, today);

test('the next ID is one more than the highest numeric ID', () => {
  assert.equal(ctx.nextItemId(['1', '7', '', 'old', ' 3 ']), 8);
  assert.equal(ctx.nextItemId([]), 1);
});
test('the Domains tab becomes domain -> entities', () => {
  assert.deepEqual(plain(ctx.domainMap([['Domain', 'Entities', 'Root folder'], ['Horology', '', 'x'], ['Ecommerce', 'Caps, Mugs', 'y'], ['', '', '']])), domains);
});
test('a new item is captured: Inbox, Stage 0, No action, Unassigned, dated', () => {
  const r = add({Title: ' Pricing page ', Domain: 'Horology'});
  assert.deepEqual(plain(r.errors), []);
  const v = r.values;
  assert.deepEqual([v.ID, v.Title, v.Status, v.Stage, v['Agent status'], v['Agent type']], ['8', 'Pricing page', 'Inbox', 'Stage 0', 'No action', 'Unassigned']);
  assert.equal(v.Created.getTime(), today.getTime());
});
test('a Ready item is selected: Stage 1, and needs a platform and a question', () => {
  assert.equal(add({Title: 'T', Domain: 'Horology', 'Agent status': 'Ready', 'Agent type': 'Codex', 'Next step / Research question': 'Q?'}).values.Stage, 'Stage 1');
  const r = add({Title: 'T', Domain: 'Horology', 'Agent status': 'Ready'});
  assert.match(r.errors.join(' '), /Claude Code or Codex/);
  assert.match(r.errors.join(' '), /Next step/);
});
test('domain, entity and dropdown values are checked', () => {
  assert.match(add({Title: 'T', Domain: 'Nope'}).errors[0], /domain/);
  assert.match(add({Title: 'T', Domain: 'Ecommerce', Entity: 'Hats'}).errors[0], /not an entity of Ecommerce/);
  assert.deepEqual(plain(add({Title: 'T', Domain: 'Ecommerce', Entity: 'Caps'}).errors), []);
  assert.match(add({Title: 'T', Domain: 'Horology', Type: 'Wish'}).errors[0], /Type must be one of/);
  assert.match(add({Domain: 'Horology'}).errors[0], /title/);
});
test('the row follows Master\'s header order and leaves other columns empty', () => {
  const row = ctx.itemRow(['ID', 'Title', 'Document count', 'Domain'], {ID: '3', Title: 'T', Domain: 'Horology'});
  assert.deepEqual(plain(row), ['3', 'T', '', 'Horology']);
});

// The server side, against a fake workbook.
function workbook() {
  const writes = [];
  const master = [['ID', 'Title', 'Domain', 'Entity', 'Status', 'Stage', 'Agent status', 'Agent type', 'Created', 'Updated'],
    ['1', 'A', 'Horology', '', 'Inbox', 'Stage 0', 'No action', 'Unassigned', '', ''],
    ['4', 'B', 'Horology', '', 'Inbox', 'Stage 0', 'No action', 'Unassigned', '', ''], ['', '', '', '', '', '', '', '', '', ''], ['', '', '', '', '', '', '', '', '', '']];
  const sheets = {
    Master: {getDataRange: () => ({getValues: () => master}), getLastColumn: () => master[0].length,
      getRange: (r, c, h, w) => ({getDisplayValues: () => [master[0]], getDataValidation: () => null,
        setValues: rows => { writes.push([r, c, rows[0]]); master[r - 1] = rows[0]; }})},
    Domains: {getDataRange: () => ({getDisplayValues: () => [['Domain', 'Entities'], ['Horology', ''], ['Ecommerce', 'Caps']]})}
  };
  const lock = {released: false, tryLock: () => true, releaseLock() { this.released = true; }};
  ctx.SpreadsheetApp = {getActiveSpreadsheet: () => ({getSheetByName: n => sheets[n] || null}), DataValidationCriteria: {VALUE_IN_LIST: 'list'}};
  ctx.LockService = {getDocumentLock: () => lock};
  return {master, writes, lock};
}
test('adding writes one row just below the last item, under the lock', () => {
  const w = workbook();
  const r = plain(ctx.addPipelineItem({Title: 'New', Domain: 'Ecommerce', Entity: 'Caps'}));
  assert.deepEqual(r, {id: '5', row: 4});
  assert.equal(w.writes.length, 1);
  assert.deepEqual(w.writes[0][2].slice(0, 8), ['5', 'New', 'Ecommerce', 'Caps', 'Inbox', 'Stage 0', 'No action', 'Unassigned']);
  assert.ok(w.lock.released);
});
test('an invalid form writes nothing and says why', () => {
  const w = workbook();
  assert.throws(() => ctx.addPipelineItem({Title: '', Domain: 'Horology'}), /title/);
  assert.equal(w.writes.length, 0);
  assert.ok(w.lock.released);
});

console.log(passed + ' tests passed');
