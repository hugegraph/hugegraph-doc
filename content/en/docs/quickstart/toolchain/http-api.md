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
the current Server endpoint has no `delete_all` query parameter. Check the task result before treating deletion as complete.

## Vermeer service tokens and native UI

Vermeer Master HTTP follows the Helm mode default: NodePort in easy mode, ClusterIP in strict mode.
RPC and Worker ports stay internal. Native UI administrators use the password from `<release>-vermeer-admin`.
Automated Vermeer API requests use a service token with `Authorization: Bearer <token>`;
the UI administrator password is not that token. Hubble's service token is wired by the chart.
Follow the [Vermeer guide](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/vermeer.md)
for native administration and controlled token generation.
