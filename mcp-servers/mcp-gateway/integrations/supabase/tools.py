from horology_runtime.operations import observe
from shared.access import current_assignment
"""Register restricted supabase MCP tools."""
from . import client
import asyncio
from policy import Denied


def register_tools(mcp, access):
    policy, ledger = access.policy, access.ledger
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("supabase", current_assignment)
    async def supabase_list_schema(schema: str = 'public') -> list[dict]:
        """List schema table names/types; never read application rows."""
        assignment, config = scope('supabase_list_schema')
        reserve(assignment, config, 'supabase_list_schema')
        return await asyncio.to_thread(client.schema_query, policy, config, schema)

    @mcp.tool()
    @observe("supabase", current_assignment)
    async def supabase_describe_table(table: str, schema: str = 'public') -> dict:
        """Read column names/types/nullability; omit defaults and executable definitions."""
        assignment, config = scope('supabase_describe_table')
        if not table or len(table) > 63:
            raise Denied('Bounded table name required')
        reserve(assignment, config, 'supabase_describe_table')
        return await asyncio.to_thread(client.schema_query, policy, config, schema, table)

    @mcp.tool()
    @observe("supabase", current_assignment)
    async def supabase_performance_summary(schema: str = 'public') -> dict:
        """Read DB counters and public-table statistics; no auth tables or query text."""
        assignment, config = scope('supabase_performance_summary')
        reserve(assignment, config, 'supabase_performance_summary')
        return await asyncio.to_thread(client.schema_query, policy, config, schema, performance=True)
