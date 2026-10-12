"""Register restricted Google Drive MCP tools."""
from horology_runtime.operations import observe
from policy import Denied
from shared.access import current_assignment
from shared.writes import WriteStore
from . import client
from .rules import drafts, registers


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
        owned = file_id not in policy['drive']['files'] or file_id not in config.get('drive_files', [])
        if owned:
            await drafts.own_draft(policy,config,assignment,file_id,writes)
        else:
            client.drive_check(policy, config, file_id)
        reserve(assignment, config, 'drive_read_document')
        return await client.drive_read(policy, config, file_id, sheet_range, owned_draft=owned)


    writes = WriteStore(ledger)

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_create_draft(folder_id: str, pipeline_id: str, title: str, operation_key: str, template_id: str = '') -> dict:
        """Create a draft or copy an approved template to an assigned output folder."""
        assignment, config = scope('drive_create_draft')
        drafts.scope_check(policy,config,folder_id,pipeline_id,template_id)
        if not title.strip() or len(title) > 200:
            raise Denied('Draft title must contain 1–200 characters')
        payload = {'folder_id':folder_id,'pipeline_id':pipeline_id,'title':title,'template_id':template_id}
        reserve(assignment,config,'drive_create_draft')
        previous = writes.begin(assignment,'drive_create_draft',operation_key,payload)
        if previous is not None:
            return previous
        result = await drafts.create(policy,config,assignment,folder_id,pipeline_id,title,template_id)
        writes.finish(assignment,'drive_create_draft',operation_key,result)
        return result

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_edit_draft(file_id: str, revision_id: str, operation_key: str, replacements: list[dict], append_text: str = '') -> dict:
        """Replace explicit text or append text in an owned draft with a required revision."""
        assignment, config = scope('drive_edit_draft')
        if not revision_id or len(revision_id)>200 or not 0 <= len(replacements) <= 10 or (not replacements and not append_text) or len(append_text)>20000:
            raise Denied('A revision and bounded edit content are required')
        for replacement in replacements:
            if set(replacement) != {'find','replace'} or any(not isinstance(v,str) for v in replacement.values()) or not replacement['find'] or len(replacement['find'])>2000 or len(replacement['replace'])>20000:
                raise Denied('Invalid bounded text replacement')
        if sum(len(r['replace']) for r in replacements)+len(append_text)>40000:
            raise Denied('Draft edit exceeds content limit')
        await drafts.own_draft(policy,config,assignment,file_id,writes)
        reserve(assignment,config,'drive_edit_draft')
        payload = {'file_id':file_id,'revision_id':revision_id,'replacements':replacements,'append_text':append_text}
        previous = writes.begin(assignment,'drive_edit_draft',operation_key,payload)
        if previous is not None:
            return previous
        result = await drafts.edit(file_id,revision_id,replacements,append_text)
        writes.finish(assignment,'drive_edit_draft',operation_key,result)
        return result

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_read_pipeline(pipeline_id: int) -> dict:
        """Read an approved permanent Pipeline ID and its edit fingerprint."""
        assignment, config = scope('drive_read_pipeline')
        registers.allowed(config, 'pipeline', pipeline_id)
        reserve(assignment, config, 'drive_read_pipeline')
        _, _, item = await registers.record('pipeline', pipeline_id)
        return {'pipeline_id': pipeline_id, 'record': item, 'fingerprint': registers.fingerprint(item)}

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_update_pipeline(pipeline_id: int, expected_fingerprint: str, updates: dict, operation_key: str) -> dict:
        """Update only investigation progress fields; never founder approval or scheduling."""
        assignment, config = scope('drive_update_pipeline')
        registers.allowed(config, 'pipeline', pipeline_id)
        reserve(assignment, config, 'drive_update_pipeline')
        return await registers.update_pipeline(policy, config, assignment, writes, pipeline_id, expected_fingerprint, updates, operation_key)

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_index_draft(pipeline_id: int, file_id: str, document_type: str, operation_key: str) -> dict:
        """Index an assignment-owned draft by Pipeline ID; do not change graph or approval fields."""
        assignment, config = scope('drive_index_draft')
        registers.allowed(config, 'documents', pipeline_id)
        reserve(assignment, config, 'drive_index_draft')
        return await registers.add_record(policy, config, assignment, writes, 'documents', pipeline_id, file_id, document_type, '', '', operation_key)

    @mcp.tool()
    @observe("google_drive", current_assignment)
    async def drive_propose_decision(pipeline_id: int, file_id: str, question: str, reason: str, operation_key: str) -> dict:
        """Add a question/reason/evidence proposal; leave decision, acceptance and dates to the founder."""
        assignment, config = scope('drive_propose_decision')
        registers.allowed(config, 'decisions', pipeline_id)
        reserve(assignment, config, 'drive_propose_decision')
        return await registers.add_record(policy, config, assignment, writes, 'decisions', pipeline_id, file_id, 'assessment', question, reason, operation_key)
