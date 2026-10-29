// Offline tests: no Google Sheets or ClickUp requests.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const crypto=require('node:crypto'),path=require('node:path');
const sourceDir=path.join(__dirname,'../src');
const source=fs.readdirSync(sourceDir).filter(n=>/\.(gs|js)$/.test(n)).sort()
  .map(n=>fs.readFileSync(path.join(sourceDir,n),'utf8')).join('\n');

function fixture(rows) {
  const pt={headers:[],rows:rows||[pipeline('1')],sheet:{getSheetId:()=>7}};
  const dt={headers:[],rows:[],sheet:{getSheetId:()=>8}};
  const documents={},records={},calls=[],logs=[];
  const tasks={abc:{id:'abc',status:{status:'backlogs'},name:'Personal plan',description:'My own notes'},
    def:{id:'def',status:{status:'backlogs'},name:'Second plan',description:'Private checklist'}};
  const c={PIPELINE_SHEET_ID:'pipe',DECISIONS_SHEET_ID:'dec',DOCUMENT_INDEX_SHEET_ID:'docs',
    WORKSPACE_URL:'https://script.google.com/a/macros/welladino.com/s/workspace/exec',
    CLICKUP_TOKEN:'token',ids:[],max:50};
  const ctx=vm.createContext({Date,JSON,Object,Array,String,Number,Set,Error,
    console:{log:value=>logs.push(value)},
    Utilities:{DigestAlgorithm:{SHA_256:'sha256'},
      computeDigest:(_,s)=>crypto.createHash('sha256').update(s).digest(),
      base64EncodeWebSafe:b=>Buffer.from(b).toString('base64url')}});
  vm.runInContext(source,ctx);
  const originalConfig=ctx.config;
  ctx.config=()=>c;
  ctx.SpreadsheetApp={openById:id=>({id})};
  ctx.readTable=book=>book.id==='pipe'?pt:dt;
  ctx.readDocumentIndex=()=>documents;
  ctx.stateStore=()=>({get:key=>records[key]||{},save:(key,value)=>{
    records[key]=JSON.parse(JSON.stringify(value));
  }});
  ctx.LockService={getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{}})};
  ctx.put=()=>{throw Error('Pipeline and Decision Register must not be written by ClickUp sync.');};
  ctx.api=(_,endpoint,method='get',payload)=>{
    calls.push({endpoint,method,payload});
    const m=endpoint.match(/^task\/(abc|def)(?:\/comment)?$/);
    if(!m) throw Error('Unexpected ClickUp endpoint: '+endpoint);
    const task=tasks[m[1]];
    if(method==='get') return task;
    if(method==='put') {
      assert.deepEqual(Object.keys(payload),['status']);
      task.status.status=payload.status;return task;
    }
    if(method==='post'&&endpoint.endsWith('/comment')) return {id:'comment-'+calls.length};
    throw Error('Unexpected ClickUp write.');
  };
  return {ctx,pt,dt,documents,records,calls,logs,tasks,c,originalConfig,
    run:live=>ctx.runSync(live)};
}
function pipeline(id,overrides={}) {
  return {row:Number(id)+1,data:{ID:id,Title:'Pipeline '+id,Status:'Inbox',Stage:'Stage 0',
    'ClickUp Pipeline URL':'https://app.clickup.com/t/'+(id==='1'?'abc':'def'),...overrides}};
}
function decision(id,status='proposed') {
  return {row:2,data:{'Decision ID':id,'Pipeline ID':'1',Status:status,
    'Review stage':'Investigation proposal',Question:'Which platform?',
    Decision:'Use the existing platform.',Reason:'Lower setup cost.'}};
}
let passed=0;
function test(name,fn) {fn();passed++;console.log('PASS '+name);}

test('unlinked rows are skipped without a ClickUp request or task creation',()=>{
  const f=fixture([pipeline('1',{'ClickUp Pipeline URL':''})]);
  const out=f.run(true);
  assert.equal(out.at(-1).skipped,1);assert.equal(f.calls.length,0);
});
test('first sync posts one intro with Stage, Status and latest decision, not the history',()=>{
  const f=fixture();f.dt.rows.push(decision('4'),{...decision('5'),row:3});
  f.documents['1']=[{key:'doc1',title:'Report',url:'https://docs.google.com/document/d/doc1/edit'}];
  f.run(true);f.run(true);
  assert.equal(f.tasks.abc.status.status,'backlogs');
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);
  const text=posts[0].payload.comment_text;
  assert.match(text,/^Pipeline 1 · Pipeline 1\n\nLinked to Horology\. Now: Stage 0 · Inbox/);
  assert.match(text,/Latest Decision 5 · proposed \(Investigation proposal\)/);
  assert.match(text,/spreadsheets\/d\/dec\/edit#gid=8&range=A3/);
  assert.doesNotMatch(text,/Decision 4|Report/);
  assert(f.records['task:1'].notebook.documents.doc1);
  assert.equal(f.tasks.abc.description,'My own notes');
});
test('intro uses the Current decision ID when it is in the register',()=>{
  const f=fixture([pipeline('1',{'Current decision ID':'4'})]);
  f.dt.rows.push(decision('4'),{...decision('5'),row:3});
  f.run(true);
  assert.match(f.calls.find(x=>x.method==='post').payload.comment_text,/Latest Decision 4 ·[^\n]*\nUse the existing platform\.\nhttps:[^\n]*range=A2\n/);
});
test('intro without decisions says so',()=>{
  const f=fixture();f.run(true);
  assert.match(f.calls.find(x=>x.method==='post').payload.comment_text,/No decision yet\./);
});
test('items already in sync state are not re-introduced',()=>{
  const f=fixture([pipeline('1'),pipeline('2')]);
  f.records['task:1']={taskId:'abc',notebook:{status:'Inbox',stage:'Stage 0',decisions:{},documents:{}}};
  f.records['task:2']={taskId:'def'};  // an older record without a notebook baseline
  f.run(true);
  assert.equal(f.calls.filter(x=>x.method==='post').length,0);
  assert(f.records['task:2'].notebook);
});
test('changed status and decision produce one concise comment, once',()=>{
  const f=fixture();f.dt.rows.push(decision('4'));
  f.run(true);f.calls.length=0;f.pt.rows[0].data.Status='Approved';f.pt.rows[0].data.Stage='Stage 3';
  f.dt.rows[0].data.Status='accepted';
  f.run(true);f.run(true);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);
  assert.match(posts[0].payload.comment_text,/Pipeline: Stage 3 · Approved/);
  assert.match(posts[0].payload.comment_text,/Decision 4 · accepted/);
  assert.match(posts[0].payload.comment_text,/^Pipeline 1 · Pipeline 1\n\nPipeline: Stage 3/);
  assert.match(posts[0].payload.comment_text,/Horology workspace: https:\/\/script\.google\.com\/a\/macros\/welladino\.com\/s\/workspace\/exec/);
  assert.equal(f.tasks.abc.status.status,'open');
  assert.equal(f.tasks.abc.description,'My own notes');
});
test('new indexed document produces a linked comment and no duplicate',()=>{
  const f=fixture();f.run(true);f.calls.length=0;
  f.documents['1']=[{key:'doc1',title:'Assessment',url:'https://docs.google.com/document/d/doc1/edit'}];
  f.run(true);f.run(true);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);assert.match(posts[0].payload.comment_text,/Assessment.*doc1\/edit/);
});
test('In progress (implementation route) sets the ClickUp task to in progress',()=>{
  const f=fixture();f.run(true);f.calls.length=0;
  f.pt.rows[0].data.Status='In progress';f.pt.rows[0].data.Stage='Stage 3';
  f.run(true);f.run(true);
  assert.equal(f.tasks.abc.status.status,'in progress');
  assert.equal(f.calls.filter(x=>x.method==='put').length,1);
  assert.match(f.calls.filter(x=>x.method==='post')[0].payload.comment_text,/Pipeline: Stage 3 · In progress/);
});
test('Completed posts a comment but leaves ClickUp status for the founder to close',()=>{
  const f=fixture();f.run(true);f.calls.length=0;
  f.pt.rows[0].data.Status='Completed';f.pt.rows[0].data.Stage='Stage 4';
  f.tasks.abc.status.status='review';
  f.run(true);f.run(true);
  assert.equal(f.tasks.abc.status.status,'review');
  assert.equal(f.calls.filter(x=>x.method==='put').length,0);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);
  assert.match(posts[0].payload.comment_text,/Pipeline: Stage 4 · Completed/);
});
test('old verb spellings are not accepted as Pipeline statuses',()=>{
  for(const status of ['Park','Reject','Hand off','Handed off']) {
    const f=fixture([pipeline('1',{Status:status})]);
    assert.equal(f.run(true).at(-1).blocked,1);
    assert.equal(f.calls.length,0);
  }
});
test('preview reads the linked task but writes neither service',()=>{
  const f=fixture();const out=f.run(false);
  assert(f.calls.every(x=>x.method==='get'));
  assert.deepEqual(f.records,{});
  assert.match(out.find(x=>x.action==='post milestone comment').comment,/Linked to Horology/);
});
test('preview shows the exact pending comment without posting it',()=>{
  const f=fixture();f.run(true);f.calls.length=0;f.pt.rows[0].data.Stage='Stage 2';
  const out=f.run(false);
  const comment=out.find(x=>x.action==='post milestone comment').comment;
  assert.match(comment,/^Pipeline 1 · Pipeline 1/);
  assert.match(comment,/Pipeline: Stage 2 · Inbox/);
  assert(f.calls.every(x=>x.method!=='post'));
  assert.equal(f.records['task:1'].notebook.stage,'Stage 0');
});
function shared() {
  return fixture([pipeline('1',{Status:'Approved'}),
    pipeline('2',{Title:'Second item','ClickUp Pipeline URL':'https://app.clickup.com/t/abc'})]);
}
test('items sharing one task each post their own headed comment',()=>{
  const f=shared();const out=f.run(true);
  assert.equal(out.at(-1).blocked,0);assert.equal(out.at(-1).succeeded,2);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.deepEqual(posts.map(x=>x.endpoint),['task/abc/comment','task/abc/comment']);
  assert.match(posts[0].payload.comment_text,/^Pipeline 1 · Pipeline 1\n/);
  assert.match(posts[1].payload.comment_text,/^Pipeline 2 · Second item\n/);
  assert.equal(f.records['task:1'].taskId,'abc');assert.equal(f.records['task:2'].taskId,'abc');
});
test('a shared task keeps its ClickUp status',()=>{
  const f=shared();f.run(true);f.pt.rows[1].data.Status='Rejected';f.run(true);
  assert.equal(f.calls.filter(x=>x.method==='put').length,0);
  assert.equal(f.tasks.abc.status.status,'backlogs');
});
test('a change to one sharing item comments for that item only',()=>{
  const f=shared();f.run(true);f.calls.length=0;
  f.pt.rows[1].data.Stage='Stage 2';f.run(true);f.run(true);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);
  assert.match(posts[0].payload.comment_text,/^Pipeline 2 · Second item\n\nPipeline: Stage 2 · Inbox/);
});
test('a pilot scope still sees the other item on a shared task',()=>{
  const f=shared();f.c.ids=['1'];f.run(true);
  assert.equal(f.calls.filter(x=>x.method==='put').length,0);
  assert.equal(f.calls.filter(x=>x.method==='post').length,1);
});
test('a task linked by one item again has its status set',()=>{
  const f=shared();f.run(true);f.pt.rows[1].data['ClickUp Pipeline URL']='';f.run(true);
  assert.equal(f.tasks.abc.status.status,'open');
});
test('old state cannot silently redirect a task',()=>{
  const f=fixture();f.records['task:1']={taskId:'def'};
  const out=f.run(true);
  assert.equal(out.at(-1).blocked,1);assert.equal(f.calls.length,0);
});
test('uncertain comment write blocks another attempt',()=>{
  const f=fixture();f.run(true);
  f.pt.rows[0].data.Status='Approved';
  f.ctx.api=(_,endpoint,method='get')=>{
    if(method==='post') throw Error('Network timeout after submit');
    return f.tasks.abc;
  };
  assert.equal(f.run(true).at(-1).failed,1);
  assert.equal(f.records['task:1'].pending,'comment');
  assert.equal(f.run(true).at(-1).blocked,1);
});
test('batch cursor rotates through pending linked rows',()=>{
  const f=fixture([pipeline('1'),pipeline('2')]);f.c.max=1;
  assert.equal(f.run(true).at(-1).pending,2);
  assert.equal(f.run(true).at(-1).pending,1);
  assert(f.records['task:1'].notebook&&f.records['task:2'].notebook);
});
test('only changed rows are checked on later runs',()=>{
  const f=fixture([pipeline('1'),pipeline('2')]);f.run(true);f.calls.length=0;
  f.pt.rows[1].data.Status='Approved';f.run(true);
  assert.deepEqual(f.calls.filter(x=>x.method==='get').map(x=>x.endpoint),['task/def']);
});
test('writes gate and hourly trigger preserves existing trigger',()=>{
  const f=fixture(),removed=[],created=[];
  f.ctx.ScriptApp={getProjectTriggers:()=>[{getHandlerFunction:()=> 'applySync'}],
    deleteTrigger:t=>removed.push(t),
    newTrigger:name=>({timeBased:()=>({everyHours:n=>({create:()=>created.push([name,n])})})})};
  f.ctx.installHourlyTrigger();
  assert.equal(removed.length,0);assert.deepEqual(created,[]);
  f.ctx.ScriptApp.getProjectTriggers=()=>[];
  f.ctx.installHourlyTrigger();
  assert.deepEqual(created,[['applySync',1]]);
  vm.runInContext('SYNC_CONFIG.ENABLE_WRITES=false',f.ctx);
  assert.throws(()=>f.ctx.applySync(),/Writes disabled/);
});
function triggerApp(existing) {
  const created=[],removed=[];
  const app={created,removed,getProjectTriggers:()=>existing.map(h=>({getHandlerFunction:()=>h})),
    deleteTrigger:t=>removed.push(t.getHandlerFunction()),
    newTrigger:name=>({forSpreadsheet:id=>({onChange:()=>({create:()=>created.push([name,'onChange',id])})}),
      timeBased:()=>({everyHours:n=>({create:()=>created.push([name,'hours',n])})})})};
  return app;
}
test('change trigger is installed once on the Pipeline workbook and removed with stopSync',()=>{
  const f=fixture();f.ctx.sheetIds=()=>({PIPELINE_SHEET_ID:'pipe'});
  f.ctx.ScriptApp=triggerApp([]);f.ctx.installTriggers();
  assert.deepEqual(f.ctx.ScriptApp.created,[['applySync','hours',1],['syncOnPipelineChange','onChange','pipe']]);
  f.ctx.ScriptApp=triggerApp(['applySync','syncOnPipelineChange']);f.ctx.installChangeTrigger();
  assert.deepEqual(f.ctx.ScriptApp.created,[]);
  f.ctx.removeChangeTrigger();assert.deepEqual(f.ctx.ScriptApp.removed,['syncOnPipelineChange']);
  f.ctx.ScriptApp=triggerApp(['applySync','syncOnPipelineChange','other']);f.ctx.stopSync();
  assert.deepEqual(f.ctx.ScriptApp.removed,['applySync','syncOnPipelineChange']);
});
function changeFixture(lockFree=true) {
  const f=fixture(),props={},sleeps=[],waits=[];
  f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:k=>props[k]||null,setProperty:(k,v)=>{props[k]=v;}})};
  f.ctx.Utilities.sleep=ms=>sleeps.push(ms);
  f.ctx.LockService={getScriptLock:()=>({tryLock:ms=>{waits.push(ms);return lockFree;},releaseLock:()=>{}})};
  return {...f,props,sleeps,waits};
}
test('a Pipeline change syncs after the settle wait, waiting for a running sync',()=>{
  const f=changeFixture();f.ctx.syncOnPipelineChange({changeType:'EDIT'});
  assert.deepEqual(f.sleeps,[30000]);assert.deepEqual(f.waits,[120000]);
  assert.equal(f.calls.filter(x=>x.method==='post').length,1);
});
test('a later change supersedes an earlier one, and format changes are ignored',()=>{
  const f=changeFixture();
  f.ctx.Utilities.sleep=()=>{f.props.LAST_PIPELINE_CHANGE='newer';};
  f.ctx.syncOnPipelineChange({changeType:'EDIT'});
  f.ctx.syncOnPipelineChange({changeType:'FORMAT'});
  assert.equal(f.calls.length,0);assert.deepEqual(f.waits,[]);
});
test('a change while the lock is held leaves the work to the running or next sync',()=>{
  const f=changeFixture(false);
  f.ctx.syncOnPipelineChange({changeType:'EDIT'});
  assert.equal(f.calls.length,0);assert.match(f.logs.at(-1),/Sync already running/);
  assert.throws(()=>f.ctx.applySync(),/Sync already running/);
});
test('configuration uses token and register links without domain list properties',()=>{
  const f=fixture(),requested=[];
  f.ctx.PropertiesService={getScriptProperties:()=>({getProperty:key=>{
    requested.push(key);return {CLICKUP_TOKEN:'token',PIPELINE_SHEET_ID:'pipe'}[key]||null;
  }})};
  f.ctx.SpreadsheetApp={openById:()=>({getSheetByName:()=>({getDataRange:()=>({getDisplayValues:()=>[
    ['Register','Location'],['Decision Register','https://docs.google.com/spreadsheets/d/dec/edit'],
    ['Document Index','https://docs.google.com/spreadsheets/d/docs/edit']]})})})};
  const cfg=f.originalConfig();
  assert.deepEqual(requested,['CLICKUP_TOKEN','PIPELINE_SHEET_ID']);
  assert.equal(cfg.max,50);assert.equal(cfg.DECISIONS_SHEET_ID,'dec');
});
test('Document count is written to the row with that ID, wherever it is now',()=>{
  const ctx=vm.createContext({console,Object,Array,String,Error,Set,JSON,Number});
  vm.runInContext(source,ctx);
  const rows=[['Title','ID','Document count'],['Item 39','39','0'],['Item 40','40','0']];
  const writes=[];
  const sheet={getDataRange:()=>({getDisplayValues:()=>rows.map(r=>r.map(String))}),
    getRange:(r,c)=>({setValue:v=>{writes.push([r,c,v]);rows[r-1][c-1]=String(v);}})};
  const table={sheet,headers:rows[0],key:'ID',rows:[{row:2,data:{Title:'Item 39',ID:'39','Document count':'0'}},
    {row:3,data:{Title:'Item 40',ID:'40','Document count':'0'}}]};
  rows.splice(1,0,['Inserted','41','0']);  // a row arrives above them after the read
  ctx.put(table,table.rows[1],'Document count',2);
  assert.deepEqual(rows.find(r=>r[1]==='40'),['Item 40','40','2']);
  assert.deepEqual(rows.find(r=>r[1]==='41'),['Inserted','41','0']);
  rows.splice(3,1);  // item 40 removed
  assert.throws(()=>ctx.put(table,table.rows[1],'Document count',3),/no longer in the sheet; nothing was written/);
  assert.equal(writes.length,1);
});
console.log(passed+' tests passed');
