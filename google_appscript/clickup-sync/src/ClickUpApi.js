/* API requests and bounded list retrieval. */

function api(c,path,method,payload) {
  // 75 requests/minute maximum within this script, below API's 100/minute limit.
  Utilities.sleep(800);
  const res=UrlFetchApp.fetch('https://api.clickup.com/api/v2/'+path,{
    method:method||'get',contentType:'application/json',headers:{Authorization:c.CLICKUP_TOKEN},
    payload:payload===undefined?undefined:JSON.stringify(payload),muteHttpExceptions:true});
  const code=res.getResponseCode();
  if(code<200||code>=300) throw Error('ClickUp HTTP '+code+' at '+path.split('?')[0]);
  return JSON.parse(res.getContentText()||'{}');
}

function testClickUpConnection() {
  const token = PropertiesService.getScriptProperties()
    .getProperty('CLICKUP_TOKEN');

  if (!token) {
    throw new Error('Add CLICKUP_TOKEN in Script Properties first.');
  }

  const result = api({ CLICKUP_TOKEN: token }, 'user');
  console.log('ClickUp connection successful. User ID: ' + result.user.id);
}
