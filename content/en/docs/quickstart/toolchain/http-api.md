---
title: "Server and Hubble HTTP API Examples"
linkTitle: "HTTP API Examples"
description: "Select GraphSpace Gremlin bindings, submit asynchronous jobs, log in to Hubble, and create schema through HTTP."
weight: 3
---

These examples target Server and Toolchain `master` (1.8). Server and Hubble have separate HTTP listeners and request contracts.
Replace the addresses, credentials, graph names and returned IDs with those from your deployment.
For Helm Service discovery, see the [Helm guide](/docs/quickstart/hugegraph/hugegraph-helm/).

## Server paths and graph selection

`GET /apis` is the resource index. Listed resource paths belong under the Server origin:
use `/versions`, `/graphspaces` and `/gremlin`, without prepending `/apis`.
Earlier indexes return paths without a leading slash; interpret those relative to the Server root, not the index directory.
When a gateway adds a public prefix, retain that prefix.

`GET /graphspaces` requires PD mode. In standalone mode, skip that step and use `GET /graphs` to list configured graphs.

```bash
curl 'http://localhost:8080/versions'
curl 'http://localhost:8080/graphspaces'
curl 'http://localhost:8080/graphspaces/DEFAULT/graphs'
```

Graph creation uses `POST /graphspaces/{space}/graphs/{graph}` and the backend's graph configuration.
`POST /graphs` is not the graph-creation endpoint. The legacy `/graphs` listing does not mean GraphSpace APIs are unavailable.
For the SeaTunnel demo, create `graph_a` before running the supplied sink job, as required by the
[SeaTunnel guide](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/seatunnel.md).

The synchronous Gremlin endpoint needs aliases for the graph selected by the caller.
For GraphSpace `DEFAULT` and graph `hugegraph`, use these exact binding names:

```bash
curl -X POST 'http://localhost:8080/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"gremlin":"g.V().count()","aliases":{"graph":"DEFAULT-hugegraph","g":"__g_DEFAULT-hugegraph"}}'
```

Bindings are case-sensitive: `<space>-<graph>` selects the graph and `__g_<space>-<graph>` selects its traversal source.
There is no implicit global `g` on a multi-graph Server. `bindings` supplies query variables;
it does not register graphs, and an alias target cannot be the expression `graph.traversal()`.
For a legacy standalone graph without a GraphSpace, the bindings are `<graph>` and `__g_<graph>`.
For an authenticated Server, add its configured HTTP credentials, for example `-u "$HG_USER:$HG_PASSWORD"`.

## Long queries use asynchronous jobs

The default synchronous Gremlin evaluation timeout is 30000 milliseconds, configured by `evaluationTimeout` in `gremlin-server.yaml`.
A whole-graph count can use a different execution path from a filtered label count. Do not infer label-scan latency from `g.V().count()`.
Submit queries that may exceed the synchronous limit as Server tasks:

```bash
curl -X POST 'http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/jobs/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"gremlin":"g.V().hasLabel(\"person\").count()"}'

# Replace <task_id> with the ID from the submission response.
curl 'http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/tasks/<task_id>'
```

The job binds `graph` and `g` for the graph in its URL. Poll until `task_status` is terminal and inspect `task_result`.
A task still marked `running` does not yet provide a completed count. Add the same authentication used by other Server requests.
A Hubble transport timeout is separate from the Server evaluation timeout; increasing only one does not remove the other.

## Hubble login and query bodies

In authenticated mode, log in with **snake_case** field names and retain the session cookie:

```bash
curl -c hubble.cookies -X POST 'http://localhost:8088/api/v1.3/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"user_name":"<username>","user_password":"<password>"}'
```

Camel-case `userName` and `userPassword` do not populate this login model. Repeated failed attempts can return HTTP 429;
correct the fields and credentials before retrying. Anonymous mode does not use the login endpoint.

The integration Gremlin endpoint currently requires `username` and `password` in the body as well as the authenticated session:

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"query":"g.V().count()","username":"<username>","password":"<password>"}'
```

Use HTTPS outside a trusted local network: JSON does not encrypt these credentials.
This integration body differs from Server's `gremlin` field and from Hubble's workspace `gremlin-query` contract.
The session establishes the caller identity; body credentials do not replace the login cookie.

## Hubble schema defaults

Hubble 1.8.0 and later releases support the following optional-field defaults. For earlier builds,
explicitly supply `"open_label_index":true,"style":{"display_fields":["~id"]}`:

Create a vertex label through Hubble using its schema model:

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/schema/vertexlabels' \
  -H 'Content-Type: application/json' \
  -d '{"name":"http_demo_person","id_strategy":"AUTOMATIC","properties":[]}'
```

Missing or null `style` uses the standard visual style, displaying `~id`;
missing or null `open_label_index` defaults to `true`, and an explicit `false` is preserved.
On older builds, supply `"open_label_index":true,"style":{"display_fields":["~id"]}` explicitly to avoid a null-value error.
Style keys use snake_case (`display_fields`, `join_symbols`), not `displayFields`.
`PRIMARY_KEY` labels also need properties and `primary_keys`; those properties must exist before the label is created.
Server schema requests have a different model and do not require Hubble visual style fields.

## Approximate graph statistics

Hubble overview counts are bounded scans. A response with `approximate:true` and `scan_limit:100000`
can stop at 100000 vertices or edges even when the graph contains millions.
Treat these values as bounded observations, not exact totals. Field spelling depends on the endpoint
(for example, `vertexcount` / `edgecount` in `gremlin-query`). Use a completed asynchronous count task for an exact result.

## Server element IDs and updates

Server vertex IDs are JSON values in URL path parameters. A string ID such as `1:marko` includes JSON quotes:
`%221%3Amarko%22`. Numeric IDs use their numeric JSON representation.
Edge IDs use the Server's raw edge-ID format; percent-encode reserved URL characters without adding JSON quotes.
Do not reuse the vertex-ID encoding rule for an edge ID.

For property appends, use `PUT .../vertices/{id}?action=append` or `PUT .../edges/{id}?action=append`
with the corresponding JSON property body. Supply the edge label to `DELETE .../edges/{id}?label={label}` as required by the backend.
Deleting a Server index uses `DELETE .../schema/indexlabels/{name}` and returns a task ID;
the current Server endpoint has no `delete_all` query parameter.
Rebuilding a vertex, edge, or index label uses `PUT .../jobs/rebuild/{type}/{name}`: missing targets return HTTP 404;
existing labels return HTTP 202 with an asynchronous task ID; poll the task status to confirm completion.

## Vermeer service tokens and native UI

Vermeer Master HTTP follows the Helm mode default: NodePort in easy mode, ClusterIP in strict mode.
RPC and Worker ports stay internal. Native UI administrators use the password from `<release>-vermeer-admin`.
Automated Vermeer API requests use a service token with `Authorization: Bearer <token>`;
the UI administrator password is not that token. Hubble's service token is wired by the chart.
Follow the [Vermeer guide](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/vermeer.md)
for native administration and controlled token generation.

### Submit a Vermeer computation through Hubble

With the chart-managed native integration, `POST /api/v1.3/vermeer/task` loads or reloads a graph; it is not the computation endpoint.
Use `graphspace`, `graph`, `task_type:"load"` and optional loader tuning there, then wait until the graph is loaded.
Submit an algorithm using the graph-scoped computation endpoint and the Hubble login cookie:

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/algorithms/vermeer' \
  -H 'Content-Type: application/json' \
  -d '{"params":{"compute.algorithm":"pagerank","compute.parallel":1,"compute.max_step":10,"pagerank.damping":0.85,"pagerank.diff_threshold":0.00001}}'
```

These parameter names and initial values match the current Hubble PageRank form:

| Parameter | Meaning | Example |
|---|---|---|
| `compute.algorithm` | Supported algorithm name | `pagerank` |
| `compute.parallel` | Compute parallelism | `1` |
| `compute.max_step` | Maximum iteration steps | `10` |
| `pagerank.damping` | PageRank damping factor | `0.85` |
| `pagerank.diff_threshold` | Convergence threshold | `0.00001` |

Current Hubble accepts `pagerank`, `wcc`, `lpa`, `degree`, `closeness_centrality`, `betweenness_centrality`, `triangle_count`, `kcore`, and `sssp`.
Use the selected algorithm's form for its own parameters; PageRank keys do not apply to another algorithm.
The direct adapter accepts `compute.*`, the selected algorithm's `<algorithm>.*` keys and `output.need_statistics`.
Vermeer still validates the actual values. Hubble controls output storage and does not accept arbitrary output paths or Server credentials.

The response contains `data.task_id` inside the Hubble response envelope. Preserve the returned sign:
Hubble maps native Vermeer task IDs to negative IDs. Poll the same graph's
`GET /api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/async-tasks/{id}`;
read result pages through `GET .../async-tasks/{id}/values?cursor=0&limit=100` after successful completion.
Do not send that Hubble ID to Server's native `/tasks/{id}` endpoint.
A graph state of `loaded` confirms loading only. An HTTP 400 on computation requires inspecting the exact rejected request and response.

### Native Vermeer task submission

Native clients submit `POST /api/v1/tasks/create` with `graph`, `task_type` (`load`, `reload` or `compute`),
and a flat string-valued `params` map. For computation, set `params["compute.algorithm"]`, not a top-level `algorithm`.
The response contains a native `task.id`; query it at `GET /api/v1/task/{id}` and read retained values at
`GET /api/v1/tasks/value/{id}`. These paths and positive IDs differ from Hubble's wrapper.
`POST /api/v1/tasks` does not submit work: after the task-method fix it returns HTTP 405 and `Allow: GET`;
older builds can return a misleading `{"code":200}` without creating a task.
See the [native API examples](https://github.com/apache/hugegraph-computer/blob/master/vermeer/README.md#api-overview).

## Cypher and task routes in Hubble

Hubble's Cypher endpoint uses the workspace query model, not the integration Gremlin model:

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/cypher' \
  -H 'Content-Type: application/json' \
  -d '{"content":"MATCH (n) RETURN count(n)","preview":false}'
```

The query field is `content`; a `query` field or a nested `gremlin-query` object does not populate it.
The session supplies authentication. Server must advertise Cypher support.
Hubble UI routes such as `/asyncTasks` are browser navigation routes. Task API requests use the
`/api/v1.3/graphspaces/{space}/graphs/{graph}/async-tasks` prefix documented above.

## Import graph elements through Hubble

`POST /api/v1.3/graphspaces/{space}/graphs/{graph}/import` accepts multipart field `file` containing JSON graph elements.
It does not accept raw CSV or a Loader job specification. Create the referenced schema first.
For example, with a `person` vertex label using `CUSTOMIZE_STRING` IDs and a `name` property,
and a `knows` edge label linking two `person` vertices, save this as `graph.json`:

```json
{
  "vertices": [
    {"id": "alice", "label": "person", "properties": {"name": "Alice"}},
    {"id": "bob", "label": "person", "properties": {"name": "Bob"}}
  ],
  "edges": [
    {"label": "knows", "source": "alice", "target": "bob", "properties": {}}
  ]
}
```

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/import' \
  -F 'file=@graph.json;type=application/json'
```

Both arrays are required; empty arrays perform an empty import. Supply all non-nullable schema properties.
Vertex IDs must match the schema ID strategy. Edge endpoints use `source` and `target`; a `file` key inside a vertex is not a data source.
This endpoint returns a graph view. Use the separate data-source/Loader workflow for CSV ingestion.

## Use GraphSpace permission presets

When Server disables custom GraphSpace role assignments, the legacy GraphSpace user POST is rejected by policy.
That endpoint assigns roles to an existing account; it is not account registration.
Use the permission presets exposed by Hubble, rather than inventing role IDs or disabling the Server policy.
For an existing account, an authorized GraphSpace manager can assign a preset using:

```bash
curl -b hubble.cookies -X PUT \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/auth/users/<user_id>/preset' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<user_id>","username":"<username>","permission_preset":"GS_READ_ONLY"}'
```

Supported presets are `GS_READ_ONLY`, `GS_READ_WRITE` and `GS_ADMIN`, subject to the caller's grant permissions.
The account identity in the path and body must match. Anonymous mode has no account-management capability.
