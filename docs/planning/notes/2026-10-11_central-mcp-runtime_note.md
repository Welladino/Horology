# Central MCP runtime

Created the locally installed horology-mcp-runtime package under mcp-servers/runtime. Both servers import a single observability implementation and timeout policy; removed service-local copies. Existing timeout values and retry/authorization/quota behavior remain. Supabase statement timeout is now set through parameterized set_config using the central millisecond value.

Docker build contexts moved to mcp-servers so both independently deployable images install the same package. A common .dockerignore explicitly allows runtime and service Python source, requirements and the public CA, while excluding local secrets/policy/client data. Removed obsolete service .dockerignore files. Native development uses an editable package install documented in runtime README and the test runbook.

Validation: 48 full repository/gateway tests passed; both images built and restarted; authenticated seventeen-tool gateway smoke and seven-tool document graph discovery passed. Both running containers imported the shared package with identical timeout policies, and no private .env/.env.local or client.local.json was present in their application paths. No paid calls or database writes are needed.
