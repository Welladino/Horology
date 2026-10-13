from horology_runtime.operations import observe
from shared.access import current_client_id
"""Register restricted supabase MCP tools."""
from . import client
import asyncio
from policy import Denied


def register_tools(mcp, access):
    policy = access.policy
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("supabase", current_client_id)
    async def supabase_list_schema(schema: str = 'public') -> list[dict]:
        """List schema table names/types; never read application rows."""
        client_id, config = scope('supabase_list_schema')
        await reserve(client_id, config, 'supabase_list_schema')
        return await asyncio.to_thread(client.schema_query, policy, config, schema)

    @mcp.tool()
    @observe("supabase", current_client_id)
    async def supabase_describe_table(table: str, schema: str = 'public') -> dict:
        """Read column names/types/nullability; omit defaults and executable definitions."""
        client_id, config = scope('supabase_describe_table')
        if not table or len(table) > 63:
            raise Denied('Bounded table name required')
        await reserve(client_id, config, 'supabase_describe_table')
        return await asyncio.to_thread(client.schema_query, policy, config, schema, table)

    @mcp.tool()
    @observe("supabase", current_client_id)
    async def supabase_performance_summary(schema: str = 'public') -> dict:
        """Read DB counters and public-table statistics; no auth tables or query text."""
        client_id, config = scope('supabase_performance_summary')
        await reserve(client_id, config, 'supabase_performance_summary')
        return await asyncio.to_thread(client.schema_query, policy, config, schema, performance=True)
