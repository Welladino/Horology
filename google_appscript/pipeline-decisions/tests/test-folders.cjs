const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const dir = path.join(__dirname, '../src');
const sources = ['Config.js','FolderRules.js','Folders.js','Registers.js']
  .map(name => fs.readFileSync(path.join(dir,name),'utf8')).join('\n');
const cells = [
  ['Domain','Entity','Kind','Parent','Name','Type','Location','Purpose'],
  ['Shop','','Root folder','','Root','','https://drive.google.com/drive/folders/root',''],
  ['Shop','','Subfolder','Root','Old','','https://drive.google.com/drive/folders/child','Briefs']
];
const writes = [];
const sheet = {getDataRange:() => ({getDisplayValues:() => cells.map(row => row.slice())}),
  getRange:(row,col) => ({setValue:value => {writes.push([row,col,value]); cells[row-1][col-1]=value;}})};
const driveFiles = {
  root:{id:'root',name:'Root',parents:['outside'],trashed:false},
  child:{id:'child',name:'New',parents:['root'],trashed:false}
};
const Drive = {Files:{
  list:() => ({files:[driveFiles.child]}),
  get:id => driveFiles[id]
}};
const lock = {released:false,tryLock:() => true,releaseLock(){this.released=true;}};
const ctx = vm.createContext({console,JSON,Object,Array,String,Error,Drive,
  SpreadsheetApp:{openById:() => ({getSheetByName:name => name === 'Locations' ? sheet : null})},
  LockService:{getScriptLock:() => lock}});
vm.runInContext(sources,ctx);
const overview = JSON.parse(JSON.stringify(ctx.getFolderOverview()));
assert.equal(overview.count,2);
assert.equal(overview.tree.roots[0].children[0].name,'Old');
assert.deepEqual(writes,[],'browsing must be read-only');
const check = JSON.parse(JSON.stringify(ctx.checkFoldersAgainstDrive()));
assert.equal(check.updates.length,1);
assert.deepEqual(writes,[[3,5,'New']]);
assert.equal(check.tree.roots[0].children[0].name,'New');
assert.ok(lock.released);
console.log('PASS folder browsing is read-only; explicit Drive check updates Locations and refreshes the tree');
