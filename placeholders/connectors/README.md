# Parked gateway connectors

GitHub and Google Drive/Docs/Sheets adapters are retained here for possible reuse. They are not imported by the gateway, packaged in its runtime image, uploaded to Cloud Build or tested as active capabilities. Native platform connectors are the preferred path for GitHub and Google workflow tasks.

`github/` preserves the GitHub integration and a snapshot of the mixed gateway tests before extraction. `google_drive/` preserves its integration, provider authorization script, write-receipt helper, register tests, policy snapshots and the unshipped operations migration. Relative imports/scripts assume their original gateway location; this is source preservation, not an independently runnable service.

The ignored `.env.local` preserves retired provider credentials privately. No credentials are committed. Google OAuth identity login remains in the active gateway under `shared/oauth/`; it is separate from Google document access.

To restore, review permissions, migrate only the required persistence, reconnect imports and tests and deliberately authorize a new release. Do not copy old policies or credentials blindly. No cloud configuration was changed by parking these adapters.
