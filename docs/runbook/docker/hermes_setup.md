# Hermes deployment moved to Watchmaker

Hermes is no longer built or operated from the Horology repository. Its Docker image, Compose file, Operator and Explorer profiles, adapted skills, browser settings, Modal configuration and private runtime data are maintained in the private [Welladino/watchmaker](https://github.com/Welladino/watchmaker) repository.

This separation keeps responsibilities clear:

- **Horology** owns the shared Pipeline workflow, canonical skills, Apps Script, document graph and restricted gateway.
- **Watchmaker** owns the always-on Hermes agent deployment and its machine-specific runtime state.

Operators with access to Watchmaker should follow its `README.md` and `docs/operations.md`. Do not recreate `hermes-data/`, a root Hermes Compose file or provider credentials in Horology.

For the shared MCP services that Hermes connects to, use [Run the local services](running_all_services.md). The integration boundary remains documented in [Hermes agent architecture](../../architecture/hermes/hermes-agents.md).
