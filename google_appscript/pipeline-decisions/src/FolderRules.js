/* The folder rules, with no Google calls, so they can be tested offline.
 *
 * A row's parent is the row with the same Domain whose Name matches its Parent,
 * in the same Entity, except an Entity folder, whose parent is the Root folder.
 */

const LOCATION_HEADERS = ['Domain', 'Entity', 'Kind', 'Parent', 'Name', 'Type', 'Location', 'Purpose'];

// A Drive folder ID from a folder link, or '' when there is none.
function folderId(url) {
  const m = String(url || '').match(/\/folders\/([\w-]+)/);
  return m ? m[1] : '';
}

function clean(v) { return String(v || '').trim(); }

function rowKey(r) { return [clean(r.Domain), clean(r.Entity), clean(r.Name)].join('|'); }

function parentKey(r) {
  if (!clean(r.Parent)) return '';
  const entity = clean(r.Kind) === 'Entity folder' ? '' : clean(r.Entity);
  return [clean(r.Domain), entity, clean(r.Parent)].join('|');
}

/* Nest the rows: one node per Root folder, children in sheet order.
 * Rows whose parent can't be found go to `unplaced`, so nothing is hidden.
 */
function buildTree(rows) {
  const nodes = rows.map(r => ({
    domain: clean(r.Domain), entity: clean(r.Entity), kind: clean(r.Kind), name: clean(r.Name),
    type: clean(r.Type), purpose: clean(r.Purpose), url: clean(r.Location), children: []
  }));
  const byKey = {};
  rows.forEach((r, i) => { byKey[rowKey(r)] = nodes[i]; });
  const roots = [], unplaced = [];
  rows.forEach((r, i) => {
    if (clean(r.Kind) === 'Root folder') { roots.push(nodes[i]); return; }
    const parent = byKey[parentKey(r)];
    if (parent && parent !== nodes[i]) parent.children.push(nodes[i]); else unplaced.push(nodes[i]);
  });
  return {roots, unplaced};
}

/* Compare the rows with Drive. Rows are identified by the folder ID in Location.
 * drive.get(id) -> {name, parentIds, trashed} or null when it can't be opened;
 * drive.children(id) -> [{id, name}].
 * Returns updates to Name and Parent, problems to show, and unlisted subfolders.
 */
function compareWithDrive(rows, drive) {
  const ids = rows.map(r => folderId(r.Location));
  const rowById = {};
  ids.forEach((id, i) => { if (id) rowById[id] = i; });
  const info = ids.map(id => id ? drive.get(id) : null);
  const label = r => [clean(r.Domain), clean(r.Entity), clean(r.Name)].filter(Boolean).join(' / ');
  const updates = [], problems = [], suggestions = [];

  rows.forEach((r, i) => {
    if (!ids[i]) return;
    const f = info[i];
    if (!f) { problems.push({row: i, message: label(r) + ": can't be opened (no access, or deleted)."}); return; }
    if (f.trashed) problems.push({row: i, message: label(r) + ' is in the Drive trash.'});
    if (f.name !== clean(r.Name)) updates.push({row: i, field: 'Name', from: clean(r.Name), to: f.name});
    if (clean(r.Kind) === 'Root folder') return;
    const p = (f.parentIds || []).map(id => rowById[id]).find(j => j !== undefined);
    if (p === undefined) { problems.push({row: i, message: label(r) + ' was moved out of the listed folders.'}); return; }
    const parentName = info[p] ? info[p].name : clean(rows[p].Name);
    if (parentName !== clean(r.Parent)) updates.push({row: i, field: 'Parent', from: clean(r.Parent), to: parentName});
    const sameDomain = clean(rows[p].Domain) === clean(r.Domain);
    const sameEntity = clean(r.Kind) === 'Entity folder' || clean(rows[p].Entity) === clean(r.Entity);
    if (!sameDomain || !sameEntity)
      problems.push({row: i, message: label(r) + ' now sits in ' + label(rows[p]) + '; check its Domain and Entity.'});
  });

  rows.forEach((r, i) => {
    if (!ids[i] || !info[i] || info[i].trashed) return;
    drive.children(ids[i]).forEach(c => {
      if (rowById[c.id] !== undefined) return;
      const isRoot = clean(r.Kind) === 'Root folder';
      const hasEntities = rows.some(o => clean(o.Domain) === clean(r.Domain) && clean(o.Kind) === 'Entity folder');
      suggestions.push({domain: clean(r.Domain), entity: isRoot ? '' : clean(r.Entity),
        kind: isRoot && hasEntities ? 'Entity folder' : 'Subfolder', parent: info[i].name, name: c.name,
        url: 'https://drive.google.com/drive/folders/' + c.id});
    });
  });
  return {updates, problems, suggestions};
}
