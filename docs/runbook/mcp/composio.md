# Composio MCP for Hermes

Composio gives Hermes access to selected external services through one hosted
MCP connection per profile. Horology currently uses separate Composio sessions
for Coordinator and Operator so that their permissions stay different:

- **Coordinator** receives read-only tools for inspecting Pipeline, Locations,
  registers, Drive and Docs before routing work.
- **Operator** receives only the read and write tools needed to perform approved
  Google Workspace work.
- **Explorer** has no Composio connection. Keep credentials and business data
  out of its disposable code-execution environment.

The Composio dashboard defines what a session is allowed to use. Hermes stores
the returned MCP URL in its tracked profile configuration and reads the
Composio API key from the profile's ignored `.env` file.

## Before adding a service

In the Composio dashboard:

1. Add the service or toolkit.
2. Create its auth config and connect the intended account.
3. Add the toolkit or selected tools to the appropriate **Session Config**.
4. Review the resulting permissions:
   - keep Coordinator read-only;
   - give Operator write access only where it is needed;
   - exclude destructive or unrelated tools.

Use the same stable Composio `user_id` that owns the existing connected
accounts. A different user ID may not be able to see those connections.

## Important: Session Configs are snapshots

Editing a saved Session Config does not automatically change a Tool Router
session that was created from it. After changing a Session Config, choose one
of these approaches:

1. **Create a new session.** This is the simplest approach. Composio returns a
   new MCP URL, which you place in the relevant Hermes `config.yaml`.
2. **Update the existing session.** Reapply the Session Config to its existing
   `trs_...` session. Its MCP URL remains unchanged.

## Enter the API key safely

Do not paste the API key directly into a command because the command may be
saved in shell history. In `zsh`, enter it without echoing it:

```bash
read -s "COMPOSIO_API_KEY?Composio API key: "
export COMPOSIO_API_KEY
echo
```

The key must be allowed to manage sessions and execute session tools. Keep it
out of Git and do not include it in screenshots or copied command output.

## Option 1: Create a new session and MCP URL

Replace `YOUR_STABLE_USER_ID` and `sc_YOUR_CONFIG_ID`. The Session Config ID is
shown by Composio and begins with `sc_`.

```bash
curl --fail-with-body --silent --show-error \
  --request POST \
  "https://backend.composio.dev/api/v3.1/tool_router/session" \
  --header "x-api-key: ${COMPOSIO_API_KEY}" \
  --header "Content-Type: application/json" \
  --data '{
    "user_id": "YOUR_STABLE_USER_ID",
    "experimental": {
      "session_config_id": "sc_YOUR_CONFIG_ID"
    }
  }'
```

The response contains a session ID and MCP URL:

```json
{
  "session_id": "trs_...",
  "mcp": {
    "type": "http",
    "url": "https://.../mcp"
  }
}
```

Copy the exact value returned in `mcp.url`. Do not construct or guess the URL.

## Option 2: Update an existing session

Use this when the profile should retain its current MCP URL. Replace both IDs:

```bash
curl --fail-with-body --silent --show-error \
  --request PATCH \
  "https://backend.composio.dev/api/v3.1/tool_router/session/trs_YOUR_SESSION_ID" \
  --header "x-api-key: ${COMPOSIO_API_KEY}" \
  --header "Content-Type: application/json" \
  --data '{
    "experimental": {
      "session_config_id": "sc_YOUR_CONFIG_ID"
    }
  }'
```

This applies the latest saved policy to that live session. The existing MCP
URL continues to identify the same `trs_...` session.

## Add the connection to Hermes

For a new session, replace the existing `url` under the relevant connection:

- Coordinator: `hermes/coordinator/config.yaml`, under
  `mcp_servers.Composio Coordinator`.
- Operator: `hermes/operator/config.yaml`, under
  `mcp_servers.Composio Operator`.

The connection should retain this structure:

```yaml
Composio Operator:
  url: https://URL-RETURNED-BY-COMPOSIO/mcp
  headers:
    x-api-key: ${COMPOSIO_HOROLOGY}
  enabled: true
```

Put the real API key in the appropriate ignored credential file:

- Coordinator: `hermes/.env`
- Operator: `hermes/operator/.env`

```dotenv
COMPOSIO_HOROLOGY=your-real-api-key
```

Do not put the key in `config.yaml`, `.env.example` or documentation. If both
profiles use the same key, it must still be present in each profile's `.env`
because Hermes loads profile environments separately.

## Apply and verify

From the repository root, apply the tracked configuration and ignored local
credentials:

```bash
./scripts/ops/hermes/bootstrap.sh
```

Then list the profile's MCP connections:

```bash
docker exec --user hermes horology-hermes \
  /opt/hermes/.venv/bin/hermes mcp list

docker exec --user hermes horology-hermes \
  /opt/hermes/.venv/bin/hermes -p operator mcp list
```

Start a new Hermes session or run `/reload-mcp`. Test a narrow, harmless read
before testing writes. For Operator writes, name the target file, folder or
Sheet range explicitly and inspect the result.

Finally, remove the temporary shell variable:

```bash
unset COMPOSIO_API_KEY
```

## Troubleshooting

- **The new toolkit is blocked:** confirm it is allowed by the Session Config,
  then create a new session or reapply that config to the existing session.
- **The account cannot be found:** confirm the session uses the same stable
  `user_id` as the connected account and that the intended auth config is
  enabled.
- **Hermes shows the old tools:** run `/reload-mcp` or open a new session after
  applying the configuration.
- **The request returns 401 or 403:** check the API key and its Composio session
  management and execution permissions. Do not print the key while debugging.
- **A new session works but Hermes does not:** verify that the returned MCP URL
  is in the correct profile config and that `COMPOSIO_HOROLOGY` exists in that
  profile's `.env`.

Composio reference: [Sessions](https://docs.composio.dev/reference/api-reference/tool-router)
and [saved Session Configs](https://docs.composio.dev/docs/session-configs).
