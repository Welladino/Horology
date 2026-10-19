// Offline tests: building the folder tree and comparing Locations with Drive. No Google access.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
const ctx = vm.createContext({console, JSON, Object, Array, String, Error});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/Rules.js'), 'utf8'), ctx);
// Results cross from the sandbox; copy them into this realm so deepEqual compares values.
const plain = fn => (...args) => JSON.parse(JSON.stringify(fn(...args)));
const buildTree = plain(ctx.buildTree), compareWithDrive = plain(ctx.compareWithDrive), folderId = ctx.folderId;

const url = id => 'https://drive.google.com/drive/folders/' + id;
const row = (o) => ({Domain: 'Shop', Entity: '', Kind: 'Subfolder', Parent: '', Name: '', Type: '', Location: '', Purpose: '', ...o});
const sheet = () => [
  row({Kind: 'Root folder', Name: '04_Shop', Location: url('root')}),
  row({Kind: 'Entity folder', Entity: 'Caps', Parent: '04_Shop', Name: '01_Caps', Location: url('caps')}),
  row({Entity: 'Caps', Parent: '01_Caps', Name: '01_Strategy', Location: url('strat')}),
  row({Entity: 'Caps', Parent: '01_Strategy', Name: '01_Direction', Type: 'Output', Location: url('dir')}),
];
// A fake Drive matching the sheet, with overrides per folder.
function drive(over = {}, kids = {}) {
  const base = {root: {name: '04_Shop', parentIds: ['top']}, caps: {name: '01_Caps', parentIds: ['root']},
    strat: {name: '01_Strategy', parentIds: ['caps']}, dir: {name: '01_Direction', parentIds: ['strat']}};
  return {
    get: id => (id in over ? over[id] : base[id]) ? {trashed: false, ...base[id], ...over[id]} : null,
    children: id => kids[id] || [],
  };
}

let passed = 0;
function test(name, fn) { fn(); passed++; console.log('PASS ' + name); }

test('folderId reads a Drive folder link', () => {
  assert.equal(folderId(url('abc_1-2')), 'abc_1-2');
  assert.equal(folderId('not a link'), '');
});
test('the tree nests rows by Parent within Domain and Entity', () => {
  const t = buildTree(sheet());
  assert.equal(t.roots.length, 1);
  assert.equal(t.roots[0].children[0].name, '01_Caps');
  assert.equal(t.roots[0].children[0].children[0].children[0].type, 'Output');
  assert.equal(t.unplaced.length, 0);
});
test('a row whose parent is missing is shown as unplaced, not dropped', () => {
  const t = buildTree([...sheet(), row({Entity: 'Caps', Parent: '09_Nowhere', Name: 'Lost'})]);
  assert.equal(t.unplaced[0].name, 'Lost');
});
test('the same folder name in another entity does not become the parent', () => {
  const rows = [...sheet(), row({Kind: 'Entity folder', Entity: 'Mugs', Parent: '04_Shop', Name: '02_Mugs'}),
    row({Entity: 'Mugs', Parent: '01_Strategy', Name: 'Orphan'})];
  assert.equal(buildTree(rows).unplaced[0].name, 'Orphan');
});
test('matching Drive gives no changes', () => {
  const r = compareWithDrive(sheet(), drive());
  assert.deepEqual([r.updates.length, r.problems.length, r.suggestions.length], [0, 0, 0]);
});
test('a renamed folder updates its Name and its children\'s Parent', () => {
  const r = compareWithDrive(sheet(), drive({strat: {name: '02_Strategy'}}));
  assert.deepEqual(r.updates.map(u => [u.row, u.field, u.to]), [[2, 'Name', '02_Strategy'], [3, 'Parent', '02_Strategy']]);
});
test('a folder moved under another listed folder updates its Parent', () => {
  const r = compareWithDrive(sheet(), drive({dir: {parentIds: ['caps']}}));
  assert.deepEqual(r.updates.map(u => [u.field, u.to]), [['Parent', '01_Caps']]);
});
test('moved out of the listed folders, trashed or inaccessible folders are reported, not changed', () => {
  const r = compareWithDrive(sheet(), drive({dir: {parentIds: ['elsewhere']}, strat: {trashed: true}, caps: null}));
  assert.equal(r.problems.length, 3);
  assert.ok(r.problems.some(p => /moved out/.test(p.message)));
  assert.ok(r.problems.some(p => /trash/.test(p.message)));
  assert.ok(r.problems.some(p => /can't be opened/.test(p.message)));
});
test('moving into another entity is flagged to check Domain and Entity', () => {
  const rows = [...sheet(), row({Kind: 'Entity folder', Entity: 'Mugs', Parent: '04_Shop', Name: '02_Mugs', Location: url('mugs')})];
  const d = drive({dir: {parentIds: ['mugs']}, mugs: {name: '02_Mugs', parentIds: ['root']}});
  assert.ok(compareWithDrive(rows, d).problems.some(p => /check its Domain and Entity/.test(p.message)));
});
test('a root folder\'s own parent is never checked', () => {
  assert.equal(compareWithDrive(sheet(), drive({root: {parentIds: ['moved-top']}})).problems.length, 0);
});
test('unlisted subfolders are suggested; under a root with entities as an Entity folder', () => {
  const r = compareWithDrive(sheet(), drive({}, {root: [{id: 'new1', name: '02_Mugs'}], dir: [{id: 'new2', name: 'Notes'}], strat: [{id: 'dir', name: '01_Direction'}]}));
  assert.deepEqual(r.suggestions.map(s => [s.name, s.kind, s.entity, s.parent]),
    [['02_Mugs', 'Entity folder', '', '04_Shop'], ['Notes', 'Subfolder', 'Caps', '01_Direction']]);
});
test('rows without a link are skipped', () => {
  const r = compareWithDrive([...sheet(), row({Entity: 'Caps', Parent: '01_Caps', Name: 'No link'})], drive());
  assert.equal(r.updates.length + r.problems.length, 0);
});

// The Drive adapter, against a fake Drive API: listed folders and subfolders come from batched
// parent queries, and only folders those queries miss are fetched one by one.
const menu = vm.createContext({console, JSON, Object, Array, String, Error});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/Menu.js'), 'utf8'), menu);
function fakeApi(files, broken = []) {
  const calls = {list: 0, get: 0};
  return {calls, Files: {
    list: o => {
      calls.list++;
      const parents = [...o.q.matchAll(/'([^']+)' in parents/g)].map(m => m[1]);
      assert.ok(o.supportsAllDrives && o.includeItemsFromAllDrives, 'shared drives included');
      return {files: files.filter(f => f.parents.some(p => parents.includes(p)))};
    },
    get: id => { calls.get++; if (broken.includes(id)) throw Error('404'); return files.find(f => f.id === id); },
  }};
}
test('the adapter reads 25 listed folders in two queries plus the root', () => {
  const files = [{id: 'root', name: 'Root', parents: ['top']}];
  for (let i = 0; i < 24; i++) files.push({id: 'f' + i, name: 'F' + i, parents: ['root']});
  files.push({id: 'old', name: 'Old', parents: ['f3'], trashed: true});
  const api = fakeApi(files);
  const d = menu.driveAdapter(files.filter(f => f.id !== 'old').map(f => f.id), api);
  assert.deepEqual([api.calls.list, api.calls.get], [2, 1]);
  assert.equal(d.get('f7').name, 'F7');
  assert.equal(d.get('root').parentIds[0], 'top');
  assert.equal(d.children('root').length, 24);
  assert.equal(d.children('f3').length, 0, 'trashed subfolders are not suggested');
  assert.equal(d.get('old').trashed, true);
});
test('a folder that can no longer be opened reads as null', () => {
  const d = menu.driveAdapter(['gone'], fakeApi([], ['gone']));
  assert.equal(d.get('gone'), null);
});

console.log(passed + ' tests passed');
