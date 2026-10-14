# Monitoring: dashboard and logs

## Dashboard

[Horology services](https://console.cloud.google.com/monitoring/dashboards/builder/db07a8ab-5016-4c93-a272-e4199b20ed6b?project=horology-dev) (Cloud Monitoring, project `horology-dev`). Charts:

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

The log-based metrics count entries from their creation (2026-10-13) onward; there is no backfill.

## Logs Explorer queries

| Query | Link |
| --- | --- |
| Every tool call, with duration and outcome | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%28%22mcp-gateway%22%20OR%20%22document-graph%22%29%0AjsonPayload.event%3D%22runtime_operation%22;duration=PT24H?project=horology-dev) |
| Tool errors only | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%28%22mcp-gateway%22%20OR%20%22document-graph%22%29%0AjsonPayload.event%3D%22runtime_operation%22%0AjsonPayload.outcome%3D%22error%22;duration=PT24H?project=horology-dev) |
| Slow tool calls (over 2 seconds) | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%28%22mcp-gateway%22%20OR%20%22document-graph%22%29%0AjsonPayload.event%3D%22runtime_operation%22%0AjsonPayload.duration_ms%3E2000;duration=PT24H?project=horology-dev) |
| Cold starts | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%28%22mcp-gateway%22%20OR%20%22document-graph%22%29%0A%28textPayload%3A%22Starting%20new%20instance%22%20OR%20textPayload%3A%22Application%20startup%20complete%22%29;duration=PT24H?project=horology-dev) |
| Requests that reached Cloud Run (method, status, latency) | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%28%22mcp-gateway%22%20OR%20%22document-graph%22%29%0Alog_id%28%22run.googleapis.com%2Frequests%22%29;duration=PT24H?project=horology-dev) |
| Sync job runs (summary lines) | [open](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_job%22%0Aresource.labels.job_name%3D%22document-graph-sync%22%0A%28textPayload%3A%22sync%20finished%22%20OR%20textPayload%3A%22row%20%22%20OR%20severity%3E%3DWARNING%29;duration=PT24H?project=horology-dev) |
| Everything for one call (replace REQUEST_ID) | [open](https://console.cloud.google.com/logs/query;query=jsonPayload.request_id%3D%22REQUEST_ID%22;duration=PT24H?project=horology-dev) |

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
trace="projects/horology-dev/traces/TRACE_ID" OR jsonPayload.trace_id="TRACE_ID"
```

## Latency table (Log Analytics)

Two SQL queries join each tool log to its Cloud Run request log by trace id:

- `ops/gcp/monitoring/latency_calls.sql`: one row per tool call over the last 24 hours, with total server time, time in our code, the remainder, and a rule-based reason.
- `ops/gcp/monitoring/latency_summary.sql`: per tool over 7 days, with call and error counts, typical and slow totals, and typical time in our code.
- `ops/gcp/monitoring/graph_warnings.sql`: document-graph warnings and errors over 7 days, from the service and the sync job: failed rows and documents, topic placement, AI retries (`AI request retry 1 of 2 after timeout`), each with its safe error category. Only logs written after the 2026-10-15 JSON logging change appear.

Paste one into **Logging → Log Analytics** (console.cloud.google.com/logs/analytics?project=horology-dev), run it, then **Save** it to keep it in the console. Queries are free. Times are measured at the server, so they leave out the network leg between the caller and Iowa; the live check below measures that. Tool calls made before the trace-id release have no match and say so.

The `_Default` bucket was upgraded to Log Analytics on 2026-10-13 (free; it can't be undone). Only logs from about 14:35 UTC that day onward are queryable here; older logs remain in Logs Explorer. The upgrade command, for reference:

```bash
gcloud --configuration=horology-admin logging buckets update _Default --location=global --enable-analytics --project=horology-dev
```

## Error Reporting

**Error Reporting** (console.cloud.google.com/errors?project=horology-dev) groups uncaught exceptions and Python tracebacks from the service logs automatically, with no setup or cost. Tool errors that are handled show up as `error_category` in tool logs, not here, so anything listed is an unexpected crash worth a look.

## Live end-to-end check

`scripts/ops/live_check.py` signs in as a real MCP client and calls free tools twice, to show cold and warm timing. It then matches each call to the services' tool logs. The first run opens a browser sign-in for each service; tokens stay in the git-ignored `.auth/` folder (owner-only files) and refresh on later runs. Results append to the git-ignored `reports/live-checks.jsonl`.

```bash
.venv/bin/python scripts/ops/live_check.py
```

Add `--search` (one paid embedding) or `--sync` (starts the sheet sync job) to include those calls. In the table:

- **total ms:** what the client waited;
- **tool ms:** time inside our code;
- **other ms:** network, token check, MCP overhead and any cold start.

First run, 2026-10-13 (warm instances, client in Singapore): `gateway_status` 1.3 s warm; `list_documents` 2.3 s warm (1.04 s inside the tool); `supabase_list_schema` 5.1 s (3.7 s inside). The services run in `us-central1`, while Neon (`ap-southeast-1`) and the Supabase pooler (`ap-southeast-1`) are in Singapore. Each database round trip crosses the Pacific.

## Recreate or update

Infrastructure changes use `horology-admin`. To change a metric:

```bash
gcloud --configuration=horology-admin logging metrics update horology_tool_duration_ms --project=horology-dev --config-from-file=ops/gcp/monitoring/tool_duration_metric.yaml
```

```bash
gcloud --configuration=horology-admin logging metrics update horology_tool_calls --project=horology-dev --config-from-file=ops/gcp/monitoring/tool_calls_metric.yaml
```

To change the dashboard, edit `dashboard.json`. Updates need the current etag, so the simplest path is to delete and recreate:

```bash
gcloud --configuration=horology-admin monitoring dashboards delete projects/366292507424/dashboards/db07a8ab-5016-4c93-a272-e4199b20ed6b --project=horology-dev --quiet
```

```bash
gcloud --configuration=horology-admin monitoring dashboards create --project=horology-dev --config-from-file=ops/gcp/monitoring/dashboard.json
```

A recreated dashboard gets a new id: update the link above.
