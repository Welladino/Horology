"""The shared access lookup: who may use which MCP server and workspace, cached (5-minute LRU). No database."""
import asyncio

import pytest

from horology_runtime.access import Account, AccessDenied, Directory


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeDirectory(Directory):
    """The real cache and rules over an in-memory table; counts lookups."""

    def __init__(self, accounts, server="document-graph", **options):
        self.clock_ = Clock()
        super().__init__(None, server, clock=self.clock_, **options)
        self.accounts, self.fetches = accounts, 0

    async def _fetch(self, email):
        self.fetches += 1
        return self.accounts.get(email)


def account(servers=("document-graph",), workspaces=("welladino",), active=True):
    return Account(1, active, frozenset(servers), tuple(workspaces))


def run(coro):
    return asyncio.run(coro)


def test_an_allowed_account_gets_its_workspaces_and_is_cached():
    directory = FakeDirectory({"me@x.com": account(workspaces=("client-x", "welladino"))})
    assert run(directory.workspaces("Me@X.com ")) == ["client-x", "welladino"]
    assert run(directory.check("me@x.com", "welladino")) == "welladino"
    assert run(directory.check("me@x.com")) is None  # a server with no workspaces (the gateway)
    assert directory.fetches == 1


@pytest.mark.parametrize("entry, reason", [
    (None, "unknown email"),
    (account(active=False), "disabled user"),
    (account(servers=("gateway",)), "no grant for this server"),
])
def test_refused_accounts(entry, reason):
    directory = FakeDirectory({"me@x.com": entry} if entry else {})
    with pytest.raises(AccessDenied):
        run(directory.check("me@x.com"))


def test_workspace_rules():
    one = FakeDirectory({"me@x.com": account()})
    assert run(one.check("me@x.com", "")) == "welladino"  # an old token without a workspace: the only one
    with pytest.raises(AccessDenied, match="member"):
        run(one.check("me@x.com", "client-x"))
    two = FakeDirectory({"me@x.com": account(workspaces=("a", "b"))})
    with pytest.raises(AccessDenied, match="reconnect"):
        run(two.check("me@x.com", ""))


def test_entries_expire_after_five_minutes_and_misses_after_one():
    directory = FakeDirectory({"me@x.com": account()})
    run(directory.check("me@x.com"))
    directory.clock_.now += 299
    run(directory.check("me@x.com"))
    assert directory.fetches == 1
    directory.accounts["me@x.com"] = account(active=False)  # disabled with the admin script
    directory.clock_.now += 2
    with pytest.raises(AccessDenied):
        run(directory.check("me@x.com"))  # re-read after 5 minutes
    assert directory.fetches == 2

    with pytest.raises(AccessDenied):
        run(directory.check("new@x.com"))
    directory.accounts["new@x.com"] = account()  # added a moment later
    directory.clock_.now += 61
    assert run(directory.check("new@x.com")) is None


def test_least_recently_used_entries_are_dropped_beyond_the_size():
    directory = FakeDirectory({f"u{i}@x.com": account() for i in range(4)}, size=2)
    for email in ("u0@x.com", "u1@x.com", "u0@x.com", "u2@x.com"):  # u1 is now the least recent
        run(directory.check(email))
    assert list(directory._cache) == ["u0@x.com", "u2@x.com"]
    run(directory.check("u1@x.com"))
    assert directory.fetches == 4


def test_forget_drops_cached_entries():
    directory = FakeDirectory({"me@x.com": account()})
    run(directory.check("me@x.com"))
    directory.forget("ME@x.com")
    run(directory.check("me@x.com"))
    assert directory.fetches == 2
