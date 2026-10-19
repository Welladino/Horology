// Offline tests of the portable sync artifact; no credentials or live requests.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sourceDir=require('node:path').join(__dirname,'../src');
const source=fs.readdirSync(sourceDir).filter(n=>/\.(gs|js)$/.test(n)).sort().map(n=>fs.readFileSync(sourceDir+'/'+n,'utf8')).join('\n');
function fixture() {
 const c={PIPELINE_SHEET_ID:'sheet',DECISIONS_SHEET_ID:'decisions',lists:{welladino:'123'},ALLOW_CLICKUP_REVIEW:'true'};
 const row={row:2,data:{ID:'1',Title:'Test',Domain:'welladino',Status:'Awaiting decision',Stage:'Stage 2','Review stage':'Stage 1','Current decision ID':'d1','Agent type':'Codex','Agent status':'No action','ClickUp Pipeline URL':'https://app.clickup.com/t/abc'}};
 const dr={row:2,data:{'Decision ID':'d1','Pipeline ID':'1','Review stage':'Stage 1',Status:'proposed','Rework instructions':''}};
 const dt={headers:Object.keys(dr.data),rows:[dr],sheet:{getSheetId:()=>2}};
 const pt={headers:Object.keys(row.data),rows:[row],sheet:{getSheetId:()=>1}};
 const records={},calls=[],out=[];
 const state={get:k=>records[k]||{},save:(k,v)=>{records[k]=JSON.parse(JSON.stringify(v));}};
 const task={id:'abc',url:'https://app.clickup.com/t/abc',list:{id:'123'},status:{status:'review'},name:'Test',description:'[Welladino Pipeline sheet:1]'};
 const ctx=vm.createContext({console,Date,JSON,Object,Array,String,Number,Set,Error,Utilities:{
  DigestAlgorithm:{SHA_256:'sha256'},computeDigest:(_,s)=>crypto.createHash('sha256').update(s).digest(),
  base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url')
 }});
 vm.runInContext(source,ctx);
 // Tests isolate deployment-specific pilot/write settings.
 vm.runInContext("SYNC_CONFIG.ENABLE_WRITES=false; SYNC_CONFIG.ALLOW_CLICKUP_REVIEW=false; SYNC_CONFIG.PILOT_PIPELINE_IDS=[]; SYNC_CONFIG.SYNC_ALL=false;",ctx);
 ctx.api=(cfg,path,method='get',payload)=>{calls.push({path,method,payload});
  if(path==='task/abc' && method==='get') return task;
  if(path.includes('/task?')) return {tasks:[]};
  if(method==='post' && path==='list/123/task') return {...task,description:payload.description};
  if(method==='post' && path.endsWith('/comment')) return {id:'comment1'};
  if(method==='put') {if(path==='task/abc') {task.name=payload.name;task.description=payload.description;task.status.status=payload.status;}return {};}
  throw Error('Unexpected request '+path);
 };
 ctx.put=(table,r,k,v)=>{r.data[k]=String(v);};
 return {ctx,c,row,dr,dt,pt,records,state,calls,out,task,run:(live)=>ctx.syncRow(c,pt,dt,row,state,{},live,out)};
}
let passed=0;
function test(name,fn) {fn();passed++;console.log('PASS '+name);}
test('preview creates no remote writes or saved state',()=>{
 const f=fixture(); f.row.data.Status='Inbox';f.row.data.Stage='Stage 0';f.row.data['ClickUp Pipeline URL']='';f.run(false);
 assert(f.out.some(x=>x.action==='create task'));assert(f.calls.every(x=>x.method==='get'));assert.deepEqual(f.records,{});
});
test('repeat sync reuses decision comment',()=>{
 const f=fixture();f.run(true);f.run(true);
 assert.equal(f.calls.filter(x=>x.method==='post'&&x.path.endsWith('/comment')).length,1);
});
test('Stage 1 approval authorises Stage 3 once',()=>{
 const f=fixture();f.run(true);f.task.status.status='open';f.run(true);
 assert.equal(f.dr.data.Status,'accepted');assert.equal(f.row.data.Status,'Approved');assert.equal(f.row.data.Stage,'Stage 3');
 f.row.data['Agent status']='No action';f.run(true);assert.equal(f.row.data['Agent status'],'No action');
});
test('Stage 3 approval hands off, does not queue implementation',()=>{
 const f=fixture();f.row.data['Review stage']='Stage 3';f.dr.data['Review stage']='Stage 3';f.run(true);f.task.status.status='open';f.run(true);
 assert.equal(f.row.data.Status,'Handed off');assert.equal(f.row.data['Agent status'],'No action');assert.equal(f.task.status.status,'closed');
});
test('sheet decisions are left to the pipeline-decisions script',()=>{
 const f=fixture();f.run(true);f.dr.data.Status='rework';f.dr.data['Rework instructions']='Compare the managed option cost';
 assert.equal(f.ctx.syncEligibility(f.c,f.dt,f.row,{}).status,'skipped');
 assert.equal(f.row.data.Status,'Awaiting decision');assert.equal(f.row.data['Agent status'],'No action');
});
test('ClickUp approval makes only agent rows Ready',()=>{
 for(const [type,expected] of [['Codex','Ready'],['Unassigned','No action'],['Manual','No action']]) {
  const f=fixture();f.row.data['Agent type']=type;f.run(true);f.task.status.status='open';f.run(true);
  assert.equal(f.row.data.Status,'Approved');assert.equal(f.row.data['Agent status'],expected);
 }
});
test('changed review content rejects stale ClickUp approval',()=>{
 const f=fixture();f.run(true);f.dr.data.Question='Changed proposal';f.task.status.status='open';assert.throws(()=>f.run(true),/contents changed/);
 assert.equal(f.dr.data.Status,'proposed');
});
test('duplicate proposed decisions are blocked before writes',()=>{
 const f=fixture();f.dt.rows.push({row:3,data:{...f.dr.data,'Decision ID':'d2'}});
 assert.throws(()=>f.run(true),/exactly one/);assert.equal(f.calls.length,0);
});
test('uncertain POST blocks repeat creation',()=>{
 const f=fixture();f.records['task:1']={pending:'create task'};assert.throws(()=>f.run(true),/Uncertain previous/);assert.equal(f.calls.length,0);
});
test('both-side status changes block approval',()=>{
 const f=fixture();f.run(true);f.task.status.status='open';f.row.data.Status='Park';assert.throws(()=>f.run(true),/Both sides changed/);
});
test('review ingestion is explicitly opt-in',()=>{
 const f=fixture();f.c.ALLOW_CLICKUP_REVIEW='false';f.run(true);f.task.status.status='open';assert.throws(()=>f.run(true),/ingestion disabled/);
});
// A fake Pipeline workbook with Registers and Domains tabs, and Script Properties.
function workspace(f,props) {
 const tabs={
  Registers:[['Register','Location','Use'],['Horology — Pipeline','https://docs.google.com/spreadsheets/d/pipe/edit',''],
   ['Horology — Decision Register','https://docs.google.com/spreadsheets/d/dec/edit',''],
   ['Horology — Document Index','https://docs.google.com/spreadsheets/d/docs/edit','']],
  Domains:[['Domain','Entities'],['Horology',''],['Shop','Caps'],['Notes','']]};
 const requested=[];
 f.ctx.SpreadsheetApp={openById:id=>{assert.equal(id,'pipe');return {getSheetByName:n=>tabs[n]&&{getDataRange:()=>({getDisplayValues:()=>tabs[n]})}};}};
 f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:k=>{requested.push(k);return props[k]||null;},getProperties:()=>{throw Error('Bulk property reads forbidden');}})};
 return {tabs,requested};
}
test('configuration reads the token, Pipeline ID and list properties one by one',()=>{
 const f=fixture(),w=workspace(f,{CLICKUP_TOKEN:'test-token',PIPELINE_SHEET_ID:'pipe',LIST_Horology:'901',LIST_Shop:' 902 '});
 vm.runInContext("SYNC_CONFIG.PILOT_PIPELINE_IDS=['18'];",f.ctx);
 const cfg=f.ctx.config();
 assert.deepEqual(w.requested,['CLICKUP_TOKEN','PIPELINE_SHEET_ID','LIST_Horology','LIST_Shop','LIST_Notes']);
 assert.deepEqual({...cfg.lists},{Horology:'901',Shop:'902'});
 assert.deepEqual([cfg.PIPELINE_SHEET_ID,cfg.DECISIONS_SHEET_ID,cfg.DOCUMENT_INDEX_SHEET_ID],['pipe','dec','docs']);
 assert.equal(cfg.ids[0],'18');assert.equal(cfg.max,5);
 assert.equal(cfg.ALLOW_CLICKUP_REVIEW,'false');
});
test('a missing Pipeline ID or register row fails explicitly',()=>{
 const f=fixture();workspace(f,{CLICKUP_TOKEN:'t'});
 assert.throws(()=>f.ctx.sheetIds(),/PIPELINE_SHEET_ID/);
 const g=fixture(),w=workspace(g,{PIPELINE_SHEET_ID:'pipe'});w.tabs.Registers.splice(3,1);
 assert.throws(()=>g.ctx.sheetIds(),/document index.*found 0/i);
});
test('write gate comes from Config.gs, without reading secret properties',()=>{
 const f=fixture();f.ctx.PropertiesService={getScriptProperties:()=>{throw Error('Should not read properties');}};
 assert.throws(()=>f.ctx.applySync(),/Writes disabled/);
 assert.throws(()=>f.ctx.installHourlyTrigger(),/Enable writes/);
});
test('missing token and empty pilot selection fail explicitly',()=>{
 const f=fixture();f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:()=>null})};
 assert.throws(()=>f.ctx.config(),/CLICKUP_TOKEN/);
 f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:()=> 'test-token'})};
 assert.throws(()=>f.ctx.config(),/Config.gs first/);
});
test('document association matches exact IDs and supports shared documents',()=>{
 const f=fixture(),docs=f.ctx.indexDocuments([
 ['Document ID','Title','Drive URL','Pipeline ID'],
 ['d1','Shared','https://docs.google.com/document/d/shared/edit','1, 11'],
 ['d2','Other','https://drive.google.com/file/d/other/view','11']]);
 assert.equal(docs['1'].length,1);assert.equal(docs['11'].length,2);
});
test('document totals deduplicate links to the same file',()=>{
 const f=fixture(),docs=f.ctx.indexDocuments([
 ['Document ID','Title','Drive URL','Pipeline ID'],
 ['d1','One','https://docs.google.com/document/d/shared/edit','1'],
 ['d2','Same','https://docs.google.com/document/d/shared/edit?tab=t.0','1']]);
 assert.equal(docs['1'].length,1);
});
test('descriptions use indexed documents and current decision ID',()=>{
 const f=fixture();f.row.documents=[{title:'Assessment',url:'https://docs.google.com/document/d/example/edit'}];
 f.row.data['Research / Plan links']='obsolete';f.row.data['Decision link']='obsolete';
 const text=f.ctx.description(f.c,f.pt,f.row);
 assert(text.includes('Assessment: https://docs.google.com/document/d/example/edit'));
 assert(text.includes('Current decision ID: d1'));assert(!text.includes('obsolete'));
});

function captureRow(id,overrides={}) {
 return {row:Number(id)+1,data:{ID:String(id),Title:'Item '+id,Domain:'welladino',Status:'Inbox',Stage:'Stage 0',
  'Agent type':'Unassigned','Agent status':'No action','ClickUp Pipeline URL':'','Document count':'0',...overrides}};
}
function batchFixture(rows,{max=5,ids=[]}={}) {
 const f=fixture();f.c.ids=ids;f.c.max=max;f.c.DOCUMENT_INDEX_SHEET_ID='documents';f.pt.rows=rows;
 f.ctx.config=()=>f.c;
 f.ctx.SpreadsheetApp={openById:id=>({id})};
 f.ctx.readTable=book=>book.id==='sheet'?f.pt:f.dt;
 f.ctx.readDocumentIndex=()=>({});
 f.ctx.stateStore=()=>f.state;
 f.ctx.LockService={getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{f.released=true;}})};
 f.ctx.console={log:()=>{}};
 f.attempted=[];
 f.ctx.syncRow=(c,pt,dt,row)=>{f.attempted.push(row.data.ID);};
 f.batch=live=>f.ctx.runSync(live);
 return f;
}
test('blank legacy stages do not consume slots or receive writes',()=>{
 const rows=Array.from({length:30},(_,i)=>captureRow(i+1,{Stage:''}));
 rows.push(captureRow('31'));
 const f=batchFixture(rows);f.ctx.put=()=>{throw Error('No document-count write expected');};
 const out=f.batch(true);
 assert.deepEqual(f.attempted,['31']);
 assert.equal(out.filter(x=>x.status==='skipped').length,30);
 assert.equal(out.at(-1).attempted,1);assert.equal(out.at(-1).succeeded,1);
 assert.equal(f.records.cursor.lastPipelineId,'31');assert(f.released);
});
test('eligible batch includes Manual and No action items',()=>{
 const f=batchFixture([captureRow('1',{'Agent type':'Manual'}),captureRow('2')]);f.batch(true);
 assert.deepEqual(f.attempted,['1','2']);
});
test('missing title, unsupported status, unmapped domain and invalid stages are blocked',()=>{
 const f=batchFixture([captureRow('1',{Title:''}),captureRow('2',{Status:'constructor'}),captureRow('3',{Domain:'unknown'}),captureRow('4',{Stage:'Stage 9'}),captureRow('5')]);
 const out=f.batch(true);assert.deepEqual(f.attempted,['5']);assert.equal(out.at(-1).blocked,4);
});
test('invalid permanent IDs are blocked even with a blank stage',()=>{
 const f=fixture();assert.equal(f.ctx.syncEligibility(f.c,f.dt,captureRow('bad',{Stage:''}),{}).status,'blocked');
});
test('published review requires the correct stage and exactly one proposal',()=>{
 const f=fixture();f.row.data.Stage='Stage 1';assert.equal(f.ctx.syncEligibility(f.c,f.dt,f.row,{}).status,'blocked');
 f.row.data.Stage='Stage 2';f.dt.rows.push({row:3,data:{...f.dr.data,'Decision ID':'d2'}});
 assert.equal(f.ctx.syncEligibility(f.c,f.dt,f.row,{}).status,'blocked');
});
test('pending writes and linked task conflicts are blocked before batch writes',()=>{
 const f=batchFixture([captureRow('1'),captureRow('2',{'ClickUp Pipeline URL':'https://app.clickup.com/t/other'}),captureRow('3')]);
 f.records['task:1']={pending:'create task'};f.records['task:2']={taskId:'abc'};
 const out=f.batch(true);assert.deepEqual(f.attempted,['3']);assert.equal(out.at(-1).blocked,2);
});
test('managed rows with cleared stages are blocked rather than skipped',()=>{
 const f=fixture();const row=captureRow('1',{Stage:''});
 assert.equal(f.ctx.syncEligibility(f.c,f.dt,row,{taskId:'abc'}).status,'blocked');
});
test('cursor follows permanent IDs through sorting, insertion and row removal',()=>{
 const f=batchFixture([captureRow('10'),captureRow('2'),captureRow('1')],{max:1});
 f.batch(true);assert.deepEqual(f.attempted,['1']);
 f.pt.rows=[captureRow('10'),captureRow('3'),captureRow('2')];f.batch(true);
 f.batch(true);f.batch(true);f.batch(true);
 assert.deepEqual(f.attempted,['1','2','3','10','2']);
});
test('old positional cursor starts the new eligible sequence safely',()=>{
 const f=batchFixture([captureRow('20'),captureRow('10')],{max:1});f.records.cursor={offset:99};f.batch(true);
 assert.deepEqual(f.attempted,['10']);assert.equal(f.records.cursor.lastPipelineId,'10');
});
test('ID sorting does not round large decimal IDs',()=>{
 const f=batchFixture([captureRow('9007199254740993'),captureRow('9007199254740992')],{max:1});f.batch(true);
 assert.deepEqual(f.attempted,['9007199254740992']);f.batch(true);assert.equal(f.attempted[1],'9007199254740993');
});
test('remote failures consume bounded attempts and advance the identity cursor',()=>{
 const f=batchFixture([captureRow('1'),captureRow('2'),captureRow('3')],{max:2});
 f.ctx.syncRow=(c,pt,dt,row)=>{f.attempted.push(row.data.ID);throw Error('ClickUp failed');};
 const out=f.batch(true);assert.deepEqual(f.attempted,['1','2']);assert.equal(out.at(-1).failed,2);
 assert.equal(f.records.cursor.lastPipelineId,'2');f.batch(true);assert.equal(f.attempted[2],'3');
});
test('preview does not write document counts or advance cursor',()=>{
 const f=batchFixture([captureRow('1',{'Document count':'99'})]);
 f.ctx.put=()=>{throw Error('Preview cannot write Sheets');};const out=f.batch(false);
 assert.equal(out.at(-1).attempted,1);assert.deepEqual(f.records,{});
});
test('pilot filter still scopes eligibility when explicitly configured',()=>{
 const f=batchFixture([captureRow('1'),captureRow('2')],{ids:['2']});const out=f.batch(true);
 assert.deepEqual(f.attempted,['2']);assert.equal(out.at(-1).selected,1);
});
test('empty eligible selection performs no writes and preserves cursor',()=>{
 const f=batchFixture([captureRow('1',{Stage:''})]);f.records.cursor={lastPipelineId:'9'};
 const out=f.batch(true);assert.equal(out.at(-1).attempted,0);assert.equal(f.records.cursor.lastPipelineId,'9');
});
test('duplicate Pipeline IDs stop the run before any row processing',()=>{
 const f=batchFixture([captureRow('1'),captureRow('1')]);assert.throws(()=>f.batch(true),/Duplicate ID/);
 assert.deepEqual(f.attempted,[]);assert.deepEqual(f.records,{});assert(f.released);
});

console.log(passed+' tests passed');
