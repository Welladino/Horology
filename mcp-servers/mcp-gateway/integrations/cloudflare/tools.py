"""Workspace-scoped MCP entry point for private Pages publishing (pages, small sites, dashboards)."""

from mcp.server.auth.middleware.auth_context import get_access_token

from horology_runtime.operations import observe
from policy import Denied
from shared.access import current_client_id
from . import client, protection


def publisher_email(token):
    claims = getattr(token, "claims", None) or {}
    email = claims.get("email", "")
    if not isinstance(email, str) or not email.strip():
        raise Denied("Publishing requires Google sign-in")
    return email.strip().lower()


def register_tools(mcp, access, directory=None, pages=None):
    @mcp.tool()
    @observe("cloudflare", current_client_id)
    async def publish_synthesis(pipeline_id: int, html: str, assets: list[dict] | None = None,
                                page: str | None = None) -> dict:
        """Publish a private HTML page, small site or dashboard for a Pipeline item to your workspace's Pages project.

        html becomes index.html. assets are extra files as {path, base64}: more .html pages, .js, .json,
        .css and images, at most 64 files and 8 MiB in all, 2 MiB per .html, .js or .json file; paths starting with _ or
        functions/ are refused. Without page it publishes to branch pipeline-<ID> (the Stage 4 synthesis);
        with a page name such as "dashboard" it publishes to pipeline-<ID>-<page> (at most 28 characters),
        so one item can keep several sites. Every branch sits behind the workspace's Cloudflare Access rules.
        """
        client_id, config = access.scope("publish_synthesis")
        # Expected setup failures return an actionable result without reserving or uploading.
        email = publisher_email(get_access_token())
        if directory is None:
            raise Denied("Publishing requires cloud Google sign-in")
        workspaces = await directory.workspaces(email)
        if len(workspaces) != 1:
            return {"status": "needs_admin_setup", "message": "Your workspace is not uniquely assigned. Contact your Horology administrator."}
        workspace = workspaces[0]
        mapping = await pages.get(workspace)
        if mapping is None or not mapping['enabled']:
            return {"status": "needs_admin_setup", "workspace": workspace,
                    "message": "Private publishing is not configured for this workspace. Contact your Cloudflare administrator."}
        members = await pages.viewers(workspace)
        try:
            await protection.ensure_private(mapping, members, email)
        except protection.ProtectionNotReady:
            return {"status": "needs_admin_setup", "workspace": workspace,
                    "message": "Cloudflare Access is missing or does not allow this workspace. Contact your Cloudflare administrator."}
        # Validate the branch before reserving, so a bad page name spends nothing.
        client.branch_name(pipeline_id, page)
        await access.reserve(client_id, config, "publish_synthesis")
        result = await client.publish(pipeline_id, html, assets or [], mapping['project'], page)
        return {"status": "published", "workspace": workspace, **result}
