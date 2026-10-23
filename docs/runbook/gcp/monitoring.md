# Monitoring: dashboard and logs

These instructions use the default Horology Cloud Run names: `mcp-gateway`, `document-graph` and `document-graph-sync`. If you renamed a service or job, replace those names in the queries and dashboard definition.

Before using this page:

1. Select your own project in the Google Cloud console. Do not use a project ID copied from this repository's history.
2. Make sure the signed-in account can view logs and metrics in that project. `Logging Viewer` and `Monitoring Viewer` are the usual read-only roles; creating the metrics and dashboard requires a project operator with configuration permissions.
3. Send at least one request to each deployed service. Logs Explorer needs no Horology-specific installation, but an empty project has no results to show.

For the commands below, set your project once in the current shell:

```bash
export HOROLOGY_GCP_PROJECT="your-project-id"
```

## Create the dashboard

The dashboard depends on the two log-based metrics in `ops/gcp/monitoring/`. Create the metrics first, from the repository root:

```bash
gcloud logging metrics create horology_tool_duration_ms --project="$HOROLOGY_GCP_PROJECT" --config-from-file=ops/gcp/monitoring/tool_duration_metric.yaml
gcloud logging metrics create horology_tool_calls --project="$HOROLOGY_GCP_PROJECT" --config-from-file=ops/gcp/monitoring/tool_calls_metric.yaml
```

Then create the dashboard:

```bash
gcloud monitoring dashboards create --project="$HOROLOGY_GCP_PROJECT" --config-from-file=ops/gcp/monitoring/dashboard.json
```

Open **Monitoring → Dashboards** in the selected project and choose **Horology services**. The dashboard ID is created for that project, so a dashboard URL from another installation will not work.

The dashboard contains:

- requests per service, by response class;
- request latency p95;
- cold-start (container startup) latency p95;
- running instances;
- tool time p95 and p50 per tool;
- tool calls by outcome;
- tool errors by category;
- sync job executions by result;
- billable instance time;
- a live panel of errors and warnings.

"Tool time" is measured inside our code (`duration_ms` in the services' JSON logs). Request latency is what Cloud Run saw, including cold starts. The gap between the two is startup, sign-in checks and MCP overhead.

The definitions are versioned in `ops/gcp/monitoring/`:

- `tool_duration_metric.yaml`: the `horology_tool_duration_ms` distribution;
- `tool_calls_metric.yaml`: the `horology_tool_calls` counter, with an `error_category` label;
- `dashboard.json`.

Log-based metrics start counting after they are created; they do not backfill older entries.

## Logs Explorer queries

Open [Logs Explorer](https://console.cloud.google.com/logs/query), confirm that the project selector shows your project, paste one query below into the query editor, choose a time range and select **Run query**. Saving a query is optional and saves it only in your own Google Cloud environment.

Each tool log line carries a `request_id`. A failed call returns only a safe error category plus that id to the client. Search the id to find the matching log line. Arguments, results and secrets are never logged.

**Every tool call, with duration and outcome**

```
resource.type="cloud_run_revision"
resource.labels.service_name=("mcp-gateway" OR "document-graph")
jsonPayload.event="runtime_operation"
```

**Tool errors only**

```
resource.type="cloud_run_revision"
resource.labels.service_name=("mcp-gateway" OR "document-graph")
jsonPayload.event="runtime_operation"
jsonPayload.outcome="error"
```

**Slow tool calls (over 2 seconds)**

```
resource.type="cloud_run_revision"
resource.labels.service_name=("mcp-gateway" OR "document-graph")
jsonPayload.event="runtime_operation"
jsonPayload.duration_ms>2000
```

**Cold starts**

```
resource.type="cloud_run_revision"
resource.labels.service_name=("mcp-gateway" OR "document-graph")
(textPayload:"Starting new instance" OR textPayload:"Application startup complete")
```

**Requests that reached Cloud Run (method, status, latency)**

```
resource.type="cloud_run_revision"
resource.labels.service_name=("mcp-gateway" OR "document-graph")
log_id("run.googleapis.com/requests")
```

**Sync job runs (summary lines)**

```
resource.type="cloud_run_job"
resource.labels.job_name="document-graph-sync"
(textPayload:"sync finished" OR textPayload:"row " OR severity>=WARNING)
```

**Everything for one call (replace REQUEST_ID)**

```
jsonPayload.request_id="REQUEST_ID"
```

**Everything for one HTTP request (replace TRACE_ID, from a tool log's `trace_id`)**

```
trace="projects/YOUR_PROJECT_ID/traces/TRACE_ID" OR jsonPayload.trace_id="TRACE_ID"
```

## Latency table (Log Analytics)

Two SQL queries join each tool log to its Cloud Run request log by trace id:

- `ops/gcp/monitoring/latency_calls.sql`: one row per tool call over the last 24 hours, with total server time, time in our code, the remainder, and a rule-based reason.
- `ops/gcp/monitoring/latency_summary.sql`: per tool over 7 days, with call and error counts, typical and slow totals, and typical time in our code.
- `ops/gcp/monitoring/graph_warnings.sql`: document-graph warnings and errors over 7 days, from the service and the sync job: failed rows and documents, topic placement, AI retries (`AI request retry 1 of 2 after timeout`), each with its safe error category. Only logs written after the 2026-10-15 JSON logging change appear.

Paste one into **Logging → Log Analytics** in your project, run it, then optionally save it in your own console. Times are measured at the server, so they leave out the network leg between the caller and the Cloud Run region; the live check below measures that. Tool calls made before the trace-id release have no match and say so.

Log Analytics is optional; ordinary Logs Explorer queries work without it. If you want to run the SQL files, an administrator must upgrade the project's `_Default` log bucket first. Google does not allow that upgrade to be undone:

```bash
gcloud logging buckets update _Default --location=global --enable-analytics --project="$HOROLOGY_GCP_PROJECT"
```

Only logs written after the upgrade are available to Log Analytics. Older retained entries remain available in Logs Explorer.

## Error Reporting

Open **Error Reporting** in your selected project to see uncaught exceptions and Python tracebacks grouped from the service logs. Tool errors that are handled show up as `error_category` in tool logs, not here, so anything listed is an unexpected crash worth a look.

## Live end-to-end check

`scripts/ops/live_check.py` signs in as a real MCP client and calls free tools twice, to show cold and warm timing. It then matches each call to the services' tool logs. The first run opens a browser sign-in for each service; tokens stay in the git-ignored `.auth/` folder (owner-only files) and refresh on later runs. Results append to the git-ignored `reports/live-checks.jsonl`.

The script currently contains this repository operator's project, region and service URLs. It is an operator diagnostic, not a portable installer. Change those constants to your deployment before using it; do not expect it to discover another project automatically.

```bash
.venv/bin/python scripts/ops/live_check.py
```

Add `--search` (one paid embedding) or `--sync` (starts the sheet sync job) to include those calls. In the table:

- **total ms:** what the client waited;
- **tool ms:** time inside our code;
- **other ms:** network, token check, MCP overhead and any cold start.

## Update an existing installation

After editing a metric definition, update it in your project:

```bash
gcloud logging metrics update horology_tool_duration_ms --project="$HOROLOGY_GCP_PROJECT" --config-from-file=ops/gcp/monitoring/tool_duration_metric.yaml
```

```bash
gcloud logging metrics update horology_tool_calls --project="$HOROLOGY_GCP_PROJECT" --config-from-file=ops/gcp/monitoring/tool_calls_metric.yaml
```

To update a dashboard, first find the ID belonging to your project:

```bash
gcloud monitoring dashboards list --project="$HOROLOGY_GCP_PROJECT" --filter='displayName="Horology services"'
```

Dashboard updates use an etag to avoid overwriting someone else's change. Describe the dashboard, copy its current `etag` into a temporary copy of `ops/gcp/monitoring/dashboard.json`, and update using that temporary file:

```bash
gcloud monitoring dashboards describe DASHBOARD_ID --project="$HOROLOGY_GCP_PROJECT"
gcloud monitoring dashboards update DASHBOARD_ID --project="$HOROLOGY_GCP_PROJECT" --config-from-file=/path/to/dashboard-with-current-etag.json
```
