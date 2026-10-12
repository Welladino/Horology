/* Persistent task/comment identities and sync baselines. */

function stateStore(book,live) {
  let s=book.getSheetByName('_ClickUp Sync');
  const records={};
  if(s && s.getLastRow()>1) s.getRange(2,1,s.getLastRow()-1,2).getValues().forEach(r=>{
    if(r[0]) records[r[0]]=JSON.parse(r[1]);
  });
  return {get:k=>records[k]||{}, save:(k,v)=>{
    records[k]=v;
    if(!live) return;
    if(!s) {s=book.insertSheet('_ClickUp Sync');s.appendRow(['Key','State JSON']);}
    const keys=Object.keys(records),row=keys.indexOf(k)+2;
    s.getRange(row,1,1,2).setValues([[k,JSON.stringify(v)]]);SpreadsheetApp.flush();
  }};
}
