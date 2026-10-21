/* Update only the status and comments of a manually linked task. */
function taskId(url) {
  const m=String(url||'').match(/^https:\/\/app\.clickup\.com\/t\/([a-zA-Z0-9]+)(?:[/?#]|$)/);
  return m?m[1]:'';
}

function syncRow(c,pt,item,st,live,out) {
  const row=item.row,id=String(row.data.ID),key='task:'+id,s=item.prior;
  const task=api(c,'task/'+item.task);
  if(String(task.id)!==item.task) throw Error('ClickUp returned a different task ID.');
  const desired=STATUS_MAP[norm(row.data.Status)],remote=norm(task.status&&task.status.status);
  if(remote!==desired) {
    out.push({pipelineId:id,action:'update task status',taskId:item.task,from:remote,to:desired});
    if(live) api(c,'task/'+item.task,'put',{status:desired});
  }
  const update=notebookUpdate(c,pt,row,s.notebook,item.snapshot);
  if(update) {
    out.push({pipelineId:id,action:'post milestone comment',taskId:item.task});
    if(live) {
      s.pending='comment';s.pendingHash=hash(update);st.save(key,s);
      const result=api(c,'task/'+item.task+'/comment','post',{comment_text:update,notify_all:false});
      if(!result.id) throw Error('Comment response missing ID; inspect ClickUp before retrying.');
      delete s.pending;delete s.pendingHash;
    }
  }
  if(live) {
    s.taskId=item.task;s.notebook=item.snapshot;
    s.remote=desired;s.sheetStatus=row.data.Status;s.stage=row.data.Stage;
    st.save(key,s);
  }
}
