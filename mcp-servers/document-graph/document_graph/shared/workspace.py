"""Workspace of the current caller; every graph query is scoped to it."""
import os


def current_workspace():
    # Local, unauthenticated mode: one workspace from the environment.
    # Signed-in callers get their mapped workspace once OAuth is added.
    workspace = os.environ.get('DOCUMENT_GRAPH_WORKSPACE', 'welladino').strip()
    if not workspace:
        raise ValueError('DOCUMENT_GRAPH_WORKSPACE is empty')
    return workspace
