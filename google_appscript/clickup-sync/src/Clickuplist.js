function discoverClickUpLists() {
  const token = PropertiesService.getScriptProperties()
    .getProperty('CLICKUP_TOKEN');

  if (!token) {
    throw new Error('Add CLICKUP_TOKEN in Script Properties first.');
  }

  const c = { CLICKUP_TOKEN: token };
  const rows = [];
  const workspaces = api(c, 'team').teams || [];

  function recordLists(workspace, space, folder, lists) {
    for (const list of lists) {
      const row = {
        workspace: workspace.name,
        workspaceId: String(workspace.id),
        space: space.name,
        spaceId: String(space.id),
        folder: folder ? folder.name : '(No folder)',
        folderId: folder ? String(folder.id) : '',
        list: list.name,
        listId: String(list.id)
      };

      rows.push(row);
      console.log(JSON.stringify(row));
    }
  }

  for (const workspace of workspaces) {
    const spaces = api(
      c,
      'team/' + workspace.id + '/space?archived=false'
    ).spaces || [];

    for (const space of spaces) {
      // Lists directly inside the Space.
      const folderless = api(
        c,
        'space/' + space.id + '/list?archived=false'
      ).lists || [];

      recordLists(workspace, space, null, folderless);

      // Folders, including subfolders returned by the API.
      const folders = api(
        c,
        'space/' + space.id + '/folder?archived=false'
      ).folders || [];

      for (const folder of folders) {
        const lists = api(
          c,
          'folder/' + folder.id + '/list?archived=false'
        ).lists || [];

        recordLists(workspace, space, folder, lists);
      }
    }
  }

  console.log('Found ' + rows.length + ' accessible, non-archived lists.');
  return rows;
}