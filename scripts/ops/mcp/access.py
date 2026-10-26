"""Manage who may use which MCP server and workspace (the users tables in Neon).

Uses the owner connection, DATABASE_URL, like migrations; the services only
read these tables. Changes reach the running services within 5 minutes
(their access cache). From the repository root:

    .venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py user list

Commands:
    server list | server add ID "Display name" | server enable ID | server disable ID
    workspace list | workspace add NAME "Display name" [--index ID] [--pipeline ID] [--decisions ID]
    workspace set NAME [--display TEXT] [--index ID] [--pipeline ID] [--decisions ID]
    workspace enable NAME | workspace disable NAME
    user list | user show EMAIL | user add EMAIL [--note TEXT]
    user enable EMAIL | user disable EMAIL
    member add EMAIL WORKSPACE [--role owner|member] | member remove EMAIL WORKSPACE
    grant EMAIL SERVER [--note TEXT] | revoke EMAIL SERVER

Nothing is deleted except memberships and grants: disable users, workspaces
and servers instead, so their history keeps its meaning.
"""
import argparse
import os
import sys

import psycopg


class AdminError(Exception):
    """A request the tables refuse, with a message for the operator."""


def _email(value):
    email = value.strip().lower()
    if '@' not in email:
        raise AdminError(f'Not an email address: {value!r}')
    return email


def _one(conn, sql, params, missing):
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise AdminError(missing)
    return row


def _user_id(conn, email):
    return _one(conn, 'SELECT id FROM access.users WHERE email = %s', (_email(email),), f'No user {email}; add them first')[0]


def _changed(cur, missing):
    if cur.rowcount == 0:
        raise AdminError(missing)


# --- servers ---------------------------------------------------------------

def server_list(conn):
    return conn.execute("""
        SELECT s.id, s.display_name, s.active, count(a.user_id)
        FROM access.mcp_servers s LEFT JOIN access.user_mcp_access a ON a.server_id = s.id
        GROUP BY s.id ORDER BY s.id""").fetchall()


def server_add(conn, server_id, display_name):
    conn.execute('INSERT INTO access.mcp_servers (id, display_name) VALUES (%s, %s)', (server_id, display_name))


def server_active(conn, server_id, active):
    _changed(conn.execute('UPDATE access.mcp_servers SET active = %s WHERE id = %s', (active, server_id)), f'No server {server_id}')


# --- workspaces --------------------------------------------------------------

SHEETS = {'index': 'index_sheet_id', 'pipeline': 'pipeline_sheet_id', 'decisions': 'decisions_sheet_id'}


def workspace_list(conn):
    return conn.execute("""
        SELECT w.name, w.display_name, w.active, w.index_sheet_id, w.pipeline_sheet_id, w.decisions_sheet_id,
               count(m.user_id)
        FROM access.workspaces w LEFT JOIN access.workspace_members m ON m.workspace = w.name
        GROUP BY w.name ORDER BY w.name""").fetchall()


def workspace_add(conn, name, display_name, **sheets):
    conn.execute('INSERT INTO access.workspaces (name, display_name, index_sheet_id, pipeline_sheet_id, decisions_sheet_id) '
                 'VALUES (%s, %s, %s, %s, %s)',
                 (name, display_name, sheets.get('index'), sheets.get('pipeline'), sheets.get('decisions')))


def workspace_set(conn, name, display_name=None, **sheets):
    fields = {SHEETS[k]: v for k, v in sheets.items() if v is not None}
    if display_name is not None:
        fields['display_name'] = display_name
    if not fields:
        raise AdminError('Nothing to change')
    assignments = ', '.join(f'{column} = %s' for column in fields)  # column names come from SHEETS, not input
    _changed(conn.execute(f'UPDATE access.workspaces SET {assignments} WHERE name = %s',  # nosec B608: fixed column names
                          (*fields.values(), name)), f'No workspace {name}')


def workspace_active(conn, name, active):
    _changed(conn.execute('UPDATE access.workspaces SET active = %s WHERE name = %s', (active, name)), f'No workspace {name}')


# --- users, members and grants ----------------------------------------------

def user_list(conn):
    return conn.execute("""
        SELECT u.email, u.active,
               coalesce((SELECT string_agg(server_id, ', ' ORDER BY server_id) FROM access.user_mcp_access WHERE user_id = u.id), ''),
               coalesce((SELECT string_agg(workspace || ' (' || role || ')', ', ' ORDER BY workspace)
                         FROM access.workspace_members WHERE user_id = u.id), ''),
               coalesce(u.note, '')
        FROM access.users u ORDER BY u.email""").fetchall()


def user_show(conn, email):
    rows = [row for row in user_list(conn) if row[0] == _email(email)]
    if not rows:
        raise AdminError(f'No user {email}')
    return rows[0]


def user_add(conn, email, note=None):
    conn.execute('INSERT INTO access.users (email, note) VALUES (%s, %s)', (_email(email), note))


def user_active(conn, email, active):
    _changed(conn.execute('UPDATE access.users SET active = %s WHERE email = %s', (active, _email(email))), f'No user {email}')


def member_add(conn, email, workspace, role='member'):
    conn.execute('INSERT INTO access.workspace_members (user_id, workspace, role) VALUES (%s, %s, %s) '
                 'ON CONFLICT (user_id, workspace) DO UPDATE SET role = excluded.role',
                 (_user_id(conn, email), workspace, role))


def member_remove(conn, email, workspace):
    _changed(conn.execute('DELETE FROM access.workspace_members WHERE user_id = %s AND workspace = %s',
                          (_user_id(conn, email), workspace)), f'{email} is not a member of {workspace}')


def grant(conn, email, server_id, note=None):
    conn.execute('INSERT INTO access.user_mcp_access (user_id, server_id, note) VALUES (%s, %s, %s) '
                 'ON CONFLICT (user_id, server_id) DO NOTHING', (_user_id(conn, email), server_id, note))


def revoke(conn, email, server_id):
    _changed(conn.execute('DELETE FROM access.user_mcp_access WHERE user_id = %s AND server_id = %s',
                          (_user_id(conn, email), server_id)), f'{email} has no access to {server_id}')


# --- command line ------------------------------------------------------------

def _table(rows, headers):
    rows = [tuple('' if v is None else str(v) for v in row) for row in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    print('  '.join(h.ljust(w) for h, w in zip(headers, widths)))
    for row in rows:
        print('  '.join(v.ljust(w) for v, w in zip(row, widths)))


def parser():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    area = p.add_subparsers(dest='area', required=True)

    server = area.add_parser('server').add_subparsers(dest='action', required=True)
    server.add_parser('list')
    s = server.add_parser('add'); s.add_argument('id'); s.add_argument('display_name')
    for action in ('enable', 'disable'):
        server.add_parser(action).add_argument('id')

    workspace = area.add_parser('workspace').add_subparsers(dest='action', required=True)
    workspace.add_parser('list')
    for action in ('add', 'set'):
        w = workspace.add_parser(action); w.add_argument('name')
        if action == 'add':
            w.add_argument('display_name')
        else:
            w.add_argument('--display')
        for sheet in SHEETS:
            w.add_argument(f'--{sheet}')
    for action in ('enable', 'disable'):
        workspace.add_parser(action).add_argument('name')

    user = area.add_parser('user').add_subparsers(dest='action', required=True)
    user.add_parser('list')
    user.add_parser('show').add_argument('email')
    u = user.add_parser('add'); u.add_argument('email'); u.add_argument('--note')
    for action in ('enable', 'disable'):
        user.add_parser(action).add_argument('email')

    member = area.add_parser('member').add_subparsers(dest='action', required=True)
    m = member.add_parser('add'); m.add_argument('email'); m.add_argument('workspace')
    m.add_argument('--role', choices=('owner', 'member'), default='member')
    m = member.add_parser('remove'); m.add_argument('email'); m.add_argument('workspace')

    g = area.add_parser('grant'); g.add_argument('email'); g.add_argument('server'); g.add_argument('--note')
    r = area.add_parser('revoke'); r.add_argument('email'); r.add_argument('server')
    return p


def run(conn, args):
    """Carry out one command; returns the text printed for list/show commands (or None)."""
    a, act = args.area, getattr(args, 'action', None)
    if a == 'server':
        if act == 'list':
            return _table(server_list(conn), ('id', 'name', 'active', 'users'))
        if act == 'add':
            return server_add(conn, args.id, args.display_name)
        return server_active(conn, args.id, act == 'enable')
    if a == 'workspace':
        if act == 'list':
            return _table(workspace_list(conn), ('name', 'display', 'active', 'index', 'pipeline', 'decisions', 'members'))
        sheets = {k: getattr(args, k) for k in SHEETS}
        if act == 'add':
            return workspace_add(conn, args.name, args.display_name, **sheets)
        if act == 'set':
            return workspace_set(conn, args.name, args.display, **sheets)
        return workspace_active(conn, args.name, act == 'enable')
    if a == 'user':
        if act == 'list':
            return _table(user_list(conn), ('email', 'active', 'servers', 'workspaces', 'note'))
        if act == 'show':
            return _table([user_show(conn, args.email)], ('email', 'active', 'servers', 'workspaces', 'note'))
        if act == 'add':
            return user_add(conn, args.email, args.note)
        return user_active(conn, args.email, act == 'enable')
    if a == 'member':
        if act == 'add':
            return member_add(conn, args.email, args.workspace, args.role)
        return member_remove(conn, args.email, args.workspace)
    if a == 'grant':
        return grant(conn, args.email, args.server, args.note)
    return revoke(conn, args.email, args.server)


def main(argv=None):
    args = parser().parse_args(argv)
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        sys.exit('Set DATABASE_URL (the owner connection used for migrations).')
    try:
        with psycopg.connect(dsn) as conn:  # one transaction, committed on success
            run(conn, args)
    except AdminError as error:
        sys.exit(str(error))
    except psycopg.errors.UniqueViolation:
        sys.exit('That already exists.')
    except psycopg.errors.ForeignKeyViolation:
        sys.exit('Unknown workspace or server: check the name with "workspace list" or "server list".')
    except psycopg.errors.CheckViolation:
        sys.exit('Invalid value: names are lowercase letters, digits and hyphens; emails must be valid.')
    if args.area in ('grant', 'revoke', 'member') or getattr(args, 'action', None) not in ('list', 'show'):
        print('Done. Running services pick this up within 5 minutes.')


if __name__ == '__main__':
    main()
