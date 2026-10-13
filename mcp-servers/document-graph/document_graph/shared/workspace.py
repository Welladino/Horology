"""Workspace of the current caller; every graph query is scoped to it.

Local mode has no sign-in and one workspace from DOCUMENT_GRAPH_WORKSPACE.
With sign-in on, each approved Google email maps to exactly one workspace,
and an email without a mapping can't sign in or use a token.
"""
import os

from mcp.server.auth.middleware.auth_context import get_access_token

_workspaces = None


def configure(mapping):
    """Turn on signed-in mode with an {email: workspace} map, or None for local mode."""
    global _workspaces
    if mapping is not None:
        if not isinstance(mapping, dict) or not mapping or not all(
                isinstance(e, str) and '@' in e and isinstance(w, str) and w.strip() for e, w in mapping.items()):
            raise ValueError('DOCUMENT_GRAPH_WORKSPACES must map approved emails to workspace names')
        mapping = {email.lower(): workspace.strip() for email, workspace in mapping.items()}
    _workspaces = mapping


def workspace_for(email):
    workspace = (_workspaces or {}).get((email or '').lower())
    if workspace is None:
        raise ValueError('This account has no workspace')
    return workspace


def current_workspace():
    if _workspaces is None:
        workspace = os.environ.get('DOCUMENT_GRAPH_WORKSPACE', 'welladino').strip()
        if not workspace:
            raise ValueError('DOCUMENT_GRAPH_WORKSPACE is empty')
        return workspace
    token = get_access_token()
    if token is None:
        raise ValueError('Authentication required')
    return workspace_for((token.claims or {}).get('email', ''))
