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
test('manual rework requires feedback and queues originating stage',()=>{
 const f=fixture();f.run(true);f.dr.data.Status='rework';
 assert.throws(()=>f.run(true),/instructions required/);
 f.dr.data['Rework instructions']='Compare the managed option cost';f.run(true);
 assert.equal(f.row.data.Status,'Rework');assert.equal(f.row.data.Stage,'Stage 1');assert.equal(f.row.data['Agent status'],'Ready');
});
test('Manual agent is never automatically queued',()=>{
 const f=fixture();f.row.data['Agent type']='Manual';f.dr.data.Status='accepted';f.run(true);assert.equal(f.row.data['Agent status'],'No action');
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
test('configuration reads only the token from Script Properties',()=>{
 const f=fixture(),requested=[];
 f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:k=>{requested.push(k);return 'test-token';},getProperties:()=>{throw Error('Bulk property reads forbidden');}})};
 vm.runInContext("SYNC_CONFIG.PILOT_PIPELINE_IDS=['18']; DOMAIN_LISTS.welladino='456';",f.ctx);
 const cfg=f.ctx.config();assert.deepEqual(requested,['CLICKUP_TOKEN']);
 assert.equal(cfg.lists.welladino,'456');assert.equal(cfg.ids[0],'18');assert.equal(cfg.max,5);
 assert.equal(cfg.ALLOW_CLICKUP_REVIEW,'false');
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
console.log(passed+' tests passed');
