from horology_runtime.operations import observe
from shared.access import current_assignment
"""Register restricted google_drive MCP tools."""
from . import client


def register_tools(mcp, access):
    policy, ledger = access.policy, access.ledger
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_list_documents() -> list[dict]:
        """List metadata only for explicit files approved for this assignment."""
        assignment, config = scope('drive_list_documents')
        reserve(assignment, config, 'drive_list_documents')
        return await client.drive_list(policy, config)

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_read_document(file_id: str, sheet_range: str = '') -> dict:
        """Read an approved native Google Doc or exact approved Sheet range."""
        assignment, config = scope('drive_read_document')
        client.drive_check(policy, config, file_id)
        reserve(assignment, config, 'drive_read_document')
        return await client.drive_read(policy, config, file_id, sheet_range)
