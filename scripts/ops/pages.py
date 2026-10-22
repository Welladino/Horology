"""Register private Pages projects after an administrator protects both hostnames.

Uses the owner DATABASE_URL. This script never creates an unprotected project
or changes Cloudflare Access. The gateway checks the live Cloudflare setup on
every publish and refuses to upload when it is incomplete.
"""
import argparse
import os
import re
import sys

import psycopg


def parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('list')
    for action in ('enable', 'disable'):
        sub.add_parser(action).add_argument('workspace')
    register = sub.add_parser('register')
    register.add_argument('workspace')
    register.add_argument('project')
    register.add_argument('main_access_app_id')
    register.add_argument('preview_access_app_id')
    return p


def run(conn, args):
    if args.action == 'list':
        rows = conn.execute('SELECT workspace, project, enabled FROM access.workspace_pages ORDER BY workspace').fetchall()
        for workspace, project, enabled in rows:
            print(f'{workspace}\t{project}\t{"enabled" if enabled else "disabled"}')
        return
    if args.action == 'register':
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', args.project):
            raise ValueError('Project must be a lowercase Cloudflare Pages slug')
        if not args.main_access_app_id or not args.preview_access_app_id or args.main_access_app_id == args.preview_access_app_id:
            raise ValueError('Provide two distinct Access application IDs')
        conn.execute('''
            INSERT INTO access.workspace_pages
                (workspace, project, main_access_app_id, preview_access_app_id, enabled)
            VALUES (%s, %s, %s, %s, false)
            ON CONFLICT (workspace) DO UPDATE SET
                project = excluded.project,
                main_access_app_id = excluded.main_access_app_id,
                preview_access_app_id = excluded.preview_access_app_id,
                enabled = false,
                updated_at = now()
        ''', (args.workspace, args.project, args.main_access_app_id, args.preview_access_app_id))
        print(f'Registered {args.project} for {args.workspace}, disabled until explicitly enabled')
        return
    enabled = args.action == 'enable'
    row = conn.execute('UPDATE access.workspace_pages SET enabled = %s, updated_at = now() WHERE workspace = %s RETURNING project',
                       (enabled, args.workspace)).fetchone()
    if row is None:
        raise ValueError(f'No Pages project registered for {args.workspace}')
    print(f'{args.workspace}: {"enabled" if enabled else "disabled"}; live Access checks still apply')


def main():
    args = parser().parse_args()
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        sys.exit('Set DATABASE_URL to the owner connection used for migrations')
    try:
        with psycopg.connect(dsn) as conn:
            run(conn, args)
    except (ValueError, psycopg.Error) as exc:
        sys.exit(str(exc))


if __name__ == '__main__':
    main()
