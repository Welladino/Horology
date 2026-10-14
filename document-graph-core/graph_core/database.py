"""The shared Postgres pool for every domain repository, bound once by the caller."""
_database = None


def configure(database):
    """Bind (or with None, unbind) the pool; the server lifespan and the job call this."""
    global _database
    _database = database


def get():
    if _database is None:
        raise RuntimeError("graph_core is not configured with a database")
    return _database
