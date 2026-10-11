"""Restricted supabase integration."""
from horology_runtime.settings import TIMEOUTS
import psycopg2
from psycopg2.extras import RealDictCursor
from policy import Denied, credential


def schema_query(policy, config, schema, table='', performance=False):
    if schema not in policy['supabase']['schemas'] or schema not in config.get('schemas', []):
        raise Denied('Schema is outside assignment scope')
    dsn = credential('SUPABASE_METADATA_DSN')
    details = psycopg2.extensions.parse_dsn(dsn)
    project = policy['supabase']['project']
    # Direct host or Supabase pooler username must identify the exact project.
    if not (details.get('host') == f'db.{project}.supabase.co' or (details.get('host', '').endswith('.pooler.supabase.com') and details.get('user', '').endswith('.' + project))):
        raise Denied('Database connection is outside the configured project')
    if details.get('user', '').split('.')[0] != 'horology_agents':
        raise Denied('Dedicated horology_agents role required')
    with psycopg2.connect(dsn, sslmode='verify-full', connect_timeout=TIMEOUTS.database_connect) as connection:
        connection.set_session(readonly=True)
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT set_config('statement_timeout', %s, true)", (str(TIMEOUTS.supabase_statement_ms),))
            if performance:
                cursor.execute('SELECT numbackends,xact_commit,xact_rollback,blks_read,blks_hit,tup_returned,tup_fetched,deadlocks FROM pg_catalog.pg_stat_database WHERE datname=current_database()')
                database = dict(cursor.fetchone())
                cursor.execute('SELECT relname,seq_scan,idx_scan,n_live_tup,n_dead_tup,last_autovacuum,last_autoanalyze FROM pg_catalog.pg_stat_user_tables WHERE schemaname=%s ORDER BY relname LIMIT 200', (schema,))
                return {'database': database, 'tables': [dict(row) for row in cursor.fetchall()]}
            if table:
                # No defaults, expressions, view/function bodies or row data.
                cursor.execute('SELECT a.attname AS column_name, pg_catalog.format_type(a.atttypid,a.atttypmod) AS data_type, NOT a.attnotnull AS nullable FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s AND c.relkind IN (\'r\',\'p\',\'v\',\'m\',\'f\') AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum LIMIT 200', (schema, table))
            else:
                cursor.execute('SELECT c.relname AS table_name,c.relkind AS object_kind FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind IN (\'r\',\'p\',\'v\',\'m\',\'f\') ORDER BY c.relname LIMIT 200', (schema,))
            columns = [dict(row) for row in cursor.fetchall()]
            if not table:
                return columns
            cursor.execute('SELECT con.conname AS name,con.contype AS kind,con.conkey AS column_numbers FROM pg_catalog.pg_constraint con JOIN pg_catalog.pg_class c ON c.oid=con.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s AND con.contype IN (\'p\',\'u\',\'f\') ORDER BY con.conname LIMIT 200', (schema, table))
            keys = [dict(row) for row in cursor.fetchall()]
            cursor.execute('SELECT i.relname AS name,x.indisunique AS is_unique,x.indisprimary AS is_primary,x.indkey::text AS column_numbers FROM pg_catalog.pg_index x JOIN pg_catalog.pg_class c ON c.oid=x.indrelid JOIN pg_catalog.pg_class i ON i.oid=x.indexrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s ORDER BY i.relname LIMIT 200', (schema, table))
            return {'columns': columns, 'keys': keys, 'indexes': [dict(row) for row in cursor.fetchall()]}
