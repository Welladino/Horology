/* Master reads and precise writes. */

const PIPE_FIELDS = ['ID','Title','Domain','Status','Agent status','Agent type',
  'Stage','ClickUp Pipeline URL','Current decision ID','Document count'];
const DEC_FIELDS = ['Decision ID','Status','Pipeline ID','Review stage','Rework instructions'];

function readTable(book, required) {
  const sheet = book.getSheetByName('Master');
  if (!sheet) throw Error('Missing Master tab.');
  const range = sheet.getDataRange(), values = range.getDisplayValues();
  const formulas=range.getFormulas(),rich=range.getRichTextValues();
  const headers = values[0].map(x=>x.trim());
  if (new Set(headers.filter(Boolean)).size !== headers.filter(Boolean).length) throw Error('Duplicate headers.');
  required.forEach(h=>{if (!headers.includes(h)) throw Error('Missing column: '+h);});
  return {sheet, headers, rows:values.slice(1).map((v,i)=>({row:i+2,
    data:Object.fromEntries(headers.map((h,j)=>[h,v[j]||''])),
    links:Object.fromEntries(headers.map((h,j)=>{
      const m=(formulas[i+1][j]||'').match(/^=HYPERLINK\("([^"]+)"/i);
      const runs=rich[i+1][j]?rich[i+1][j].getRuns():[];
      return [h,Array.from(new Set([m?m[1]:'',...runs.map(r=>r.getLinkUrl()||'')].filter(Boolean)))];
    }))})).filter(r=>r.data[headers[0]])};
}

function put(table,row,key,value) {
  const col = table.headers.indexOf(key);
  if (col < 0) throw Error('Missing field '+key);
  // Reject malformed duplicate-ID rows before this point; writes use current row.
  table.sheet.getRange(row.row,col+1).setValue(value); row.data[key]=String(value);
}

function unique(rows,key) {
  const seen=new Set(); rows.forEach(r=>{const id=r.data[key];
    if(seen.has(id)) throw Error('Duplicate '+key+': '+id); seen.add(id);});
}
