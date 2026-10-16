"""Workspace of the current caller; every graph query is scoped to it.

Local mode has no sign-in and one workspace from DOCUMENT_GRAPH_WORKSPACE.
With sign-in on, the person picks one of their workspaces when connecting
(workspace_members in Neon); it is stored on the connection's tokens, and the
OAuth provider re-checks membership on every request
(horology_runtime.access.Directory) before putting it in the token's claims.
"""
import os

from mcp.server.auth.middleware.auth_context import get_access_token

_signed_in = False


def configure(signed_in):
    """True for signed-in mode (the workspace comes from the token), False for local mode."""
    global _signed_in
    _signed_in = bool(signed_in)


def current_workspace():
    if not _signed_in:
        workspace = os.environ.get('DOCUMENT_GRAPH_WORKSPACE', 'welladino').strip()
        if not workspace:
            raise ValueError('DOCUMENT_GRAPH_WORKSPACE is empty')
        return workspace
    token = get_access_token()
    if token is None:
        raise ValueError('Authentication required')
    workspace = (token.claims or {}).get('workspace')
    if not workspace:
        raise ValueError('This connection has no workspace: reconnect to choose one')
    return workspace
