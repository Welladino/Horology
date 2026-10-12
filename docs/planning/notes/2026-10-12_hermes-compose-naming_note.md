# Hermes Compose naming

Date: 2026-10-12

The root Compose project is now `horology-hermes`; its existing container name remains `horology-hermes`, and the official upstream image is locally tagged `horology-hermes:latest`. The external `horology_default` network preserves MCP overlay connectivity independently of the project name. Hermes state remains bind-mounted from `hermes-data`.

Startup instructions and the full-stack fixture were updated for the explicit image tag and external network. All 78 tests passed. Hermes was temporarily started for checks and restored to its prior stopped state; the disposable PostgreSQL test container was removed. No cloud changes, commit or push.
