/* One maintained comment per Decision Register row. */

function syncDecisionComments(c,dt,row,id,st,live,out) {
  const d=row.data;
  for(const dr of decisionRows(dt,d.ID)) {
    const ck='comment:'+dr.data['Decision ID'],cs=st.get(ck);
    if(cs.pending) throw Error('Uncertain comment write for decision '+dr.data['Decision ID']);
    if(cs.taskId && cs.taskId!==id) throw Error('Decision reassigned to a different task; reconcile its comment.');
    const text='[Welladino Decision '+dr.data['Decision ID']+']\n'+
      dt.headers.map(h=>h+': '+(dr.data[h]||'—')+(dr.links && dr.links[h] && dr.links[h].length?'\n'+dr.links[h].join('\n'):'')).join('\n')+
      '\nRegister: https://docs.google.com/spreadsheets/d/'+c.DECISIONS_SHEET_ID+'/edit#gid='+dt.sheet.getSheetId()+'&range=A'+dr.row;
    if(cs.hash===hash(text)) continue;
    out.push({pipelineId:d.ID,action:cs.id?'update decision comment':'create decision comment',decisionId:dr.data['Decision ID']});
    if(live) {
      cs.pending=true;st.save(ck,cs);
      const result=api(c,cs.id?'comment/'+cs.id:'task/'+id+'/comment',cs.id?'put':'post',{comment_text:text,notify_all:false});
      cs.id=cs.id||result.id;if(!cs.id) throw Error('Comment response missing ID.');
      cs.hash=hash(text);cs.taskId=id;delete cs.pending;st.save(ck,cs);
    }
  }
}