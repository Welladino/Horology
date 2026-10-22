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
test('initial sync maps Sheet status but does not publish historical comments',()=>{
  const f=fixture();f.dt.rows.push(decision('4'));
  f.documents['1']=[{key:'doc1',title:'Report',url:'https://docs.google.com/document/d/doc1/edit'}];
  f.run(true);
  assert.equal(f.tasks.abc.status.status,'backlogs');
  assert.equal(f.calls.filter(x=>x.method==='post').length,0);
  assert(f.records['task:1'].notebook.documents.doc1);
  assert.equal(f.tasks.abc.description,'My own notes');
});
test('changed status and decision produce one concise comment, once',()=>{
  const f=fixture();f.dt.rows.push(decision('4'));
  f.run(true);f.pt.rows[0].data.Status='Approved';f.pt.rows[0].data.Stage='Stage 3';
  f.dt.rows[0].data.Status='accepted';
  f.run(true);f.run(true);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);
  assert.match(posts[0].payload.comment_text,/Pipeline: Stage 3 · Approved/);
  assert.match(posts[0].payload.comment_text,/Decision 4 · accepted/);
  assert.match(posts[0].payload.comment_text,/^Horology updates:/);
  assert.match(posts[0].payload.comment_text,/Horology workspace: https:\/\/script\.google\.com\/a\/macros\/welladino\.com\/s\/workspace\/exec/);
  assert.equal(f.tasks.abc.status.status,'open');
  assert.equal(f.tasks.abc.description,'My own notes');
});
test('new indexed document produces a linked comment and no duplicate',()=>{
  const f=fixture();f.run(true);
  f.documents['1']=[{key:'doc1',title:'Assessment',url:'https://docs.google.com/document/d/doc1/edit'}];
  f.run(true);f.run(true);
  const posts=f.calls.filter(x=>x.method==='post');
  assert.equal(posts.length,1);assert.match(posts[0].payload.comment_text,/Assessment.*doc1\/edit/);
});
test('Completed posts a comment but leaves ClickUp status for the founder to close',()=>{
  const f=fixture();f.run(true);
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
  const f=fixture();f.run(false);
  assert(f.calls.every(x=>x.method==='get'));
  assert.deepEqual(f.records,{});
});
test('preview shows the exact pending comment without posting it',()=>{
  const f=fixture();f.run(true);f.pt.rows[0].data.Stage='Stage 2';
  const out=f.run(false);
  const comment=out.find(x=>x.action==='post milestone comment').comment;
  assert.match(comment,/^Horology updates:/);
  assert.match(comment,/Pipeline: Stage 2 · Inbox/);
  assert(f.calls.every(x=>x.method!=='post'));
  assert.equal(f.records['task:1'].notebook.stage,'Stage 0');
});
test('both rows sharing one task are blocked',()=>{
  const f=fixture([pipeline('1'),pipeline('2',{'ClickUp Pipeline URL':'https://app.clickup.com/t/abc'})]);
  const out=f.run(true);
  assert.equal(out.at(-1).blocked,2);assert.equal(f.calls.length,0);
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
console.log(passed+' tests passed');
