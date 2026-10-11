# Shared Horology runtime

Root-level package usable by MCP deployments and future Hermes extensions. It is not tied to MCP transport or installed into the upstream Hermes image automatically.

```text
shared-runtime/
  pyproject.toml
  horology_runtime/
    logging.py        # JSON logger configuration
    error_handling.py # safe exception categories and client errors
    settings.py       # immutable timeout policy
    operations.py     # sync/async logging and error wrapper
```

From the repository root, install for native development:

```bash
.venv/bin/python -m pip install --no-deps -e shared-runtime
```

Both MCP Dockerfiles use repository-root build context and install this package alongside their service requirements. Root .dockerignore allows only approved runtime/service sources, requirements and the public CA; private environment, policy, client credentials and Hermes data stay outside the build context. Each image copies only its own service and shared-runtime. Rebuild consuming images after changes.

The package uses the standard library, with optional HTTP/Postgres exception classifiers when httpx/psycopg2 are installed. Hermes can package it later without requiring MCP or DB dependencies. Use horology_runtime.operations.observe to instrument approved functions; integrating it into upstream Hermes behavior is separate future work.

Settings remain code constants. Existing phase/statement timeout values, sanitized error behavior and no-retry policy are preserved.
