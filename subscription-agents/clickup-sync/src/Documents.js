/* Document Index associations; permanent Pipeline IDs, never task titles. */
function indexDocuments(values) {
  if(!values.length) throw Error('Document Index is empty.');
  const headers=values[0].map(x=>String(x).trim());
  ['Document ID','Title','Drive URL','Pipeline ID'].forEach(h=>{if(!headers.includes(h)) throw Error('Document Index missing '+h);});
  const result={},seen=new Set();
  values.slice(1).forEach(cells=>{
    const d=Object.fromEntries(headers.map((h,i)=>[h,String(cells[i]||'').trim()]));
    if(!d['Document ID']) return;
    if(seen.has(d['Document ID'])) throw Error('Duplicate Document ID: '+d['Document ID']);
    seen.add(d['Document ID']);
    const ids=Array.from(new Set(d['Pipeline ID'].split(',').map(x=>x.trim()).filter(Boolean)));
    if(ids.length && !/^https:\/\/(docs|drive)\.google\.com\//.test(d['Drive URL'])) throw Error('Invalid indexed Drive URL: '+d['Document ID']);
    const file=d['Drive URL'].match(/\/d\/([^/?#]+)/);
    const key=file?file[1]:d['Drive URL'];
    ids.forEach(id=>{
      if(!/^\d+$/.test(id)) throw Error('Invalid indexed Pipeline ID: '+id);
      const docs=result[id]||(result[id]=[]);
      if(!docs.some(doc=>doc.key===key)) docs.push({id:d['Document ID'],title:d.Title,url:d['Drive URL'],key});
    });
  });
  return result;
}
function readDocumentIndex(book) {
  const sheet=book.getSheetByName('Document Index');
  if(!sheet) throw Error('Missing Document Index tab.');
  return indexDocuments(sheet.getDataRange().getDisplayValues());
}
function refreshDocumentCounts() {
  const lock=LockService.getScriptLock();if(!lock.tryLock(1000)) throw Error('Sync already running.');
  try {
    const p=SYNC_CONFIG,pt=readTable(SpreadsheetApp.openById(p.PIPELINE_SHEET_ID),['ID','Document count']);
    unique(pt.rows,'ID');
    const documents=readDocumentIndex(SpreadsheetApp.openById(p.DOCUMENT_INDEX_SHEET_ID));
    pt.rows.forEach(row=>{const count=(documents[row.data.ID]||[]).length;
      if(row.data['Document count']!==String(count)) put(pt,row,'Document count',count);
    });
    console.log('Refreshed document counts for '+pt.rows.length+' Pipeline rows. No ClickUp requests.');
  } finally {lock.releaseLock();}
}
