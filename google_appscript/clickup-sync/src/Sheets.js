/* Master reads and precise writes. */

const PIPE_FIELDS = ['ID','Title','Status','Stage','ClickUp Pipeline URL'];
const DEC_FIELDS = ['Decision ID','Status','Pipeline ID','Review stage','Question','Decision'];

function readTable(book, required) {
  const sheet = book.getSheetByName('Master');
  if (!sheet) throw Error('Missing Master tab.');
  const range = sheet.getDataRange(), values = range.getDisplayValues();
  const formulas=range.getFormulas(),rich=range.getRichTextValues();
  const headers = values[0].map(x=>x.trim());
  if (new Set(headers.filter(Boolean)).size !== headers.filter(Boolean).length) throw Error('Duplicate headers.');
  required.forEach(h=>{if (!headers.includes(h)) throw Error('Missing column: '+h);});
  return {sheet, headers, key:required[0], rows:values.slice(1).map((v,i)=>({row:i+2,
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
  table.sheet.getRange(currentRowById(table,row),col+1).setValue(value); row.data[key]=String(value);
}

// Find the row by its permanent ID (the table's key column: ID or Decision ID) just before writing, never by
// the position read earlier, which a sort, insert or agent write may have changed.
function currentRowById(table,row) {
  const idKey=table.key||table.headers[0],col=table.headers.indexOf(idKey),id=String(row.data[idKey]).trim(),found=[];
  if(!id) throw Error('Rows are written by '+idKey+'; this row has none.');
  table.sheet.getDataRange().getDisplayValues().forEach((cells,i)=>{
    if(i>0&&String(cells[col]).trim()===id) found.push(i+1);});
  if(found.length!==1) throw Error(idKey+' '+id+(found.length?' appears '+found.length+' times':' is no longer in the sheet')+
    '; nothing was written.');
  row.row=found[0]; return row.row;
}

function unique(rows,key) {
  const seen=new Set(); rows.forEach(r=>{const id=r.data[key];
    if(seen.has(id)) throw Error('Duplicate '+key+': '+id); seen.add(id);});
}
