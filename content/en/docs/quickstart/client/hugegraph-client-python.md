---
title: "HugeGraph Python Client Quick Start"
linkTitle: "Python Client"
weight: 2
---

`hugegraph-python-client` is the Python SDK for HugeGraph. It manages schemas, reads and writes graph data, and executes Gremlin queries. HugeGraph-LLM and HugeGraph-ML also use this client.

The module lives in the [hugegraph-ai](https://github.com/apache/hugegraph-ai) repository under `hugegraph-python-client/`. The import name is `pyhugegraph`.

## Requirements

- The client and HugeGraph-AI workspace require Python 3.12 or later; CI runtime versions follow the HugeGraph-AI workspace configuration.
- HugeGraph Server 1.5.0 or later. The client refuses to connect to older servers; use client v1.3.x for those.
- `uv` (recommended) or `pip`

Runtime dependencies are `decorator`, `requests`, `urllib3` and `rich`.

## Installation

The released package is published on PyPI as `hugegraph-python`:

```bash
uv pip install hugegraph-python
# Alternatively: pip install hugegraph-python
```

These commands do not pin a version and install the latest release; see [PyPI](https://pypi.org/project/hugegraph-python/). The source directory is `hugegraph-python-client`, while the distribution is `hugegraph-python`. Install from the HugeGraph-AI workspace for master code.

To use the latest repository code, sync the workspace from the root of the HugeGraph-AI repository. `hugegraph-python-client` is a workspace member exposed through the `python-client` extra, so plain `uv sync` does not pull it in:

```bash
git clone https://github.com/apache/hugegraph-ai.git
cd hugegraph-ai
uv sync --extra python-client
source .venv/bin/activate
```

## Connect and Write Data

```python
from pyhugegraph.client import PyHugeClient

client = PyHugeClient(
    url="http://127.0.0.1:8080",
    graph="hugegraph",
    user="admin",
    pwd="admin",
    graphspace=None,
)

schema = client.schema()
schema.property_key("name").as_text().if_not_exist().create()
schema.property_key("birthDate").as_text().if_not_exist().create()
schema.vertex_label("Person").properties("name", "birthDate") \
      .use_primary_key_id().primary_keys("name").if_not_exist().create()
schema.vertex_label("Movie").properties("name") \
      .use_primary_key_id().primary_keys("name").if_not_exist().create()
schema.edge_label("ActedIn").source_label("Person").target_label("Movie") \
      .if_not_exist().create()

graph = client.graph()
person = graph.add_vertex(
    "Person", {"name": "Al Pacino", "birthDate": "1940-04-25"}
)
movie = graph.add_vertex("Movie", {"name": "The Godfather"})
edge = graph.add_edge("ActedIn", person.id, movie.id, {})

print(graph.get_vertex_by_id(person.id))
print(graph.get_edge_by_id(edge.id))
```

### Client Parameters

`PyHugeClient(url, graph, user, pwd, graphspace=None, timeout=None, *, token=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Base URL of HugeGraph Server. If the value has no scheme, `http://` is prepended, so `127.0.0.1:8080` also works. |
| `graph` | `str` | required | Graph name. This is the second positional parameter. |
| `user` | `str` | required | Username, sent as HTTP basic auth. |
| `pwd` | `str` | required | Password, sent as HTTP basic auth. |
| `graphspace` | `str` or `None` | `None` | GraphSpace name. See below for how `None` is resolved. |
| `timeout` | `float`, `tuple[float, float]` or `None` | `None` | Positive `(connect, read)` timeouts in seconds, or one value for both. `None` becomes `(0.5, 15.0)`. |
| `token` | `str` or `None` | `None` | Explicit Bearer token for version probing and subsequent requests; overrides Basic auth. |

Idempotent requests may retry 500, 502 and 504 responses up to three times with a 0.1 backoff factor. Task waiting disables automatic HTTP retries and redirects to respect the remaining waiting budget.

### Server Version and GraphSpace

The client resolves GraphSpace at construction time:

- A non-empty `graphspace` string turns GraphSpace mode on directly.
- Otherwise the client sends `GET {url}/versions` and reads `versions.core`.
- A server older than 1.5.0 raises `RuntimeError` asking you to upgrade the server or use client v1.3.x.
- Server 1.7+ selects graphspace `DEFAULT`; server 1.5/1.6 keeps legacy routes.
- If the probe fails, initialization raises an error instead of guessing the server profile.

The mode decides the request prefix: `/graphspaces/<graphspace>/graphs/<graph>/...` when GraphSpace is on, `/graphs/<graph>/...` when it is off.

### Managers on the Client

Accessors cache their managers; all managers share the HTTP session owned by the client.

| Accessor | Manager | Covers |
|----------|---------|--------|
| `client.schema()` | `SchemaManager` | Property keys, vertex labels, edge labels, index labels |
| `client.graph()` | `GraphManager` | Vertex and edge CRUD, batch writes, paging |
| `client.gremlin()` | `GremlinManager` | Gremlin execution |
| `client.graphs()` | `GraphsManager` | Graph list, graph info, config, clear data |
| `client.traverser()` | `TraverserManager` | Traversal and path algorithms |
| `client.variable()` | `VariableManager` | Graph variables |
| `client.task()` | `TaskManager` | Async task list, query, cancel, delete |
| `client.auth()` | `AuthManager` | Users, groups, targets, belongs, accesses |
| `client.metrics()` | `MetricsManager` | Server metrics |
| `client.version()` | `VersionManager` | Server version |

Use `client.rank()`, `client.rebuild()` and `client.olap()` directly. See the [Python API reference](/docs/clients/hugegraph-python-client/).

## Common Operations

### Build the Schema

The schema builders are fluent. Call `create()` last, or `append()`, `eliminate()` and `remove()` to change an existing definition.

```python
schema = client.schema()

# Property keys: as_text/as_int/as_long/as_float/as_double/as_bool/as_byte/as_blob/as_date/as_object
# cardinality: value_single/value_list/value_set
# aggregation: calc_max/calc_min/calc_sum/calc_old
schema.property_key("age").as_int().value_single().if_not_exist().create()

# Vertex labels: use_automatic_id/use_customize_string_id/use_customize_number_id/use_primary_key_id
schema.vertex_label("person").properties("name", "age", "city") \
      .primary_keys("name").nullable_keys("city").if_not_exist().create()

# Edge labels: link() is shorthand for source_label() plus target_label()
schema.edge_label("knows").link("person", "person").multi_times() \
      .properties("date", "city").sort_keys("date").nullable_keys("city") \
      .if_not_exist().create()

# Index labels: on_v/on_e, then secondary/range/search/shard/unique
schema.index_label("personByCity").on_v("person").by("city") \
      .secondary().if_not_exist().create()
```

### Query the Schema

```python
schema = client.schema()
print(schema.get_schema())            # whole schema as native server JSON
print(schema.get_property_keys())
print(schema.get_vertex_labels())
print(schema.get_edge_labels())
print(schema.get_index_labels())

# Single definitions
print(schema.get_property_key("name"))
print(schema.get_vertex_label("person"))
print(schema.get_edge_label("knows"))
print(schema.get_index_label("personByCity"))

# Edge label links, formatted as "Person--ActedIn-->Movie"
print(schema.get_relations())
```

### Read, Update and Delete Graph Data

The graph API takes property dictionaries, not chained property builders:

```python
graph = client.graph()
graph.append_vertex(person.id, {"birthDate": "1940-04-25"})    # add properties
graph.eliminate_vertex(person.id, {"birthDate": "1940-04-25"}) # drop properties
graph.append_edge(edge.id, {"city": "Beijing"})
graph.eliminate_edge(edge.id, {"city": "Beijing"})
graph.remove_edge_by_id(edge.id)
graph.remove_vertex_by_id(person.id)
```

`add_vertex` returns a `VertexData` with `id`, `label`, `type` and `properties`. `add_edge` returns an `EdgeData` with `id`, `label`, `type`, `out_v`, `out_v_label`, `in_v`, `in_v_label` and `properties`.

Vertex ids passed to the client may be strings, integers or `uuid.UUID` values. Booleans are rejected, and integers must fit the Java signed long range.

### Batch Writes

`add_vertices` takes `(label, properties)` pairs, and `add_edges` takes `(label, out_id, in_id, out_label, in_label, properties)` tuples. Both return objects that carry only the generated ids.

```python
graph = client.graph()
vertices = graph.add_vertices([
    ("person", {"name": "Alice", "age": 20}),
    ("person", {"name": "Bob", "age": 23}),
])
edges = graph.add_edges([
    ("knows", vertices[0].id, vertices[1].id, "person", "person", {"date": "2012-01-10"}),
])
```

### Paging and Conditional Queries

```python
graph = client.graph()

# Returns (vertices, next_page); pass next_page back in to continue
vertices, next_page = graph.get_vertex_by_page("person", limit=10)
vertices, next_page = graph.get_vertex_by_page("person", limit=10, page=next_page)

# Server-side property predicates
older = graph.get_vertex_by_condition("person", properties={"age": "P.gt(29)"})

# Edges by page. When vertex_id is given, direction is required
edges, next_page = graph.get_edge_by_page(label="knows", limit=10)
edges, next_page = graph.get_edge_by_page(vertex_id=person.id, direction="OUT", limit=10)

# Batch lookup by id
graph.get_vertices_by_id([v1.id, v2.id])
graph.get_edges_by_id([e1.id, e2.id])
```

### Execute Gremlin

```python
gremlin = client.gremlin()
result = gremlin.exec("g.V().limit(5)")
print(result)
```

`exec` binds the `graph` and `g` aliases for you, based on the graph name and the resolved GraphSpace, and returns the `result` field of the server response. A response missing `requestId`, `status` or `result` raises `ResponseParseError`.

### Traverse the Graph

`TraverserManager` wraps the server traverser endpoints. Its methods use snake_case.

```python
traverser = client.traverser()

traverser.k_out(marko_id, 2)
traverser.k_neighbor(marko_id, 2)
traverser.same_neighbors(marko_id, josh_id)
traverser.jaccard_similarity(marko_id, josh_id)
traverser.shortest_path(marko_id, ripple_id, 3)
traverser.all_shortest_paths(marko_id, ripple_id, 3)
traverser.weighted_shortest_path(marko_id, ripple_id, "weight", capacity=10000)
traverser.single_source_shortest_path(marko_id, weight="weight", limit=10)
traverser.multi_node_shortest_path([marko_id, josh_id], max_depth=2)
traverser.paths(marko_id, josh_id, 2)
traverser.crosspoints(marko_id, josh_id, 2)
traverser.rings(marko_id, 3)
traverser.rays(marko_id, 2)
traverser.vertices([marko_id])
traverser.edges([edge_id])
```

The POST-based variants take request bodies: `advanced_paths`, `customized_paths`, `template_paths`, `customized_crosspoints` and `fusiform_similarity`.

### Graph Variables

```python
variable = client.variable()
variable.set("owner", "mary")
print(variable.get("owner"))
print(variable.all())
variable.remove("owner")
```

### Async Tasks

```python
task = client.task()
print(task.list_tasks(status="success", limit=10))
print(task.get_task(task_id))
task.cancel_task(task_id)
task.delete_task(task_id)
```

### Server Metrics and Graph Info

The legacy graph shortcuts `get_all_graphs()`, `get_version()` and `get_graph_info()` return JSON strings.
For parsed dictionaries, use `client.graphs().list()`, `client.version().version()` or `client.graphs().get(graph_name)` without `json.loads(...)`.

```python
metrics = client.metrics()
metrics.get_all_basic_metrics()
metrics.get_gauges_metrics()
metrics.get_counters_metrics()
metrics.get_histograms_metrics()
metrics.get_meters_metrics()
metrics.get_timers_metrics()
metrics.get_statistics_metrics()
metrics.get_system_metrics()
metrics.get_backend_metrics()

graphs = client.graphs()
graphs.get_all_graphs()
graphs.get_version()
graphs.get_graph_info()
graphs.get_graph_config()
graphs.clear_graph_all_data()   # deletes every vertex, edge and schema entry

print(client.version().version())
```

### Authentication and Authorization

`AuthManager` follows the server routing: users, targets, belongs and accesses are mounted under `/graphspaces/{graphspace}/auth/...`, while groups stay at the server-level `/auth/groups`. On HugeGraph 1.7.0 and later a graphspace must be resolved, otherwise these calls raise `ValueError` before any request is sent.

```python
auth = client.auth()

user = auth.create_user("test_user", "password")
auth.modify_user(user["id"], user_email="hugegraph@apache.org")
auth.get_user(user["id"])
auth.list_users(limit=10)

group = auth.create_group("test_group", "read only")
auth.modify_group(group["id"], group_description="updated")
auth.list_groups()

target = auth.create_target("target1", "hugegraph", "127.0.0.1:8080", [])
auth.update_target(target["id"], "target1", "hugegraph", "127.0.0.1:8080", [])
auth.list_targets()

belong = auth.create_belong(user["id"], group["id"])
auth.update_belong(belong["id"], "description")
auth.list_belongs()

access = auth.grant_accesses(group["id"], target["id"], "READ")
auth.modify_accesses(access["id"], "description")
auth.list_accesses()
auth.revoke_accesses(access["id"])
auth.delete_belong(belong["id"])
auth.delete_target(target["id"])
auth.delete_group(group["id"])
auth.delete_user(user["id"])
```

## Method Naming

New code uses `snake_case`. Existing public CamelCase method/property names remain direct aliases.
Check the migration notes for parameter and return-value changes that affect both spellings.

## Error Handling

Exceptions live in `pyhugegraph.utils.exceptions`:

| Exception | Raised when |
|-----------|-------------|
| `NotAuthorizedError` | The server answers 401 |
| `NotFoundError` | The server answers 404 |
| `ServerError` | Any other non-2xx response, with the server message attached |
| `ResponseParseError` | A successful response cannot be parsed into the expected shape |
| `ServiceUnavailableError` | The server reports `ServiceUnavailableException` |
| `InvalidParameterError`, `CreateError`, `RemoveError`, `UpdateError`, `DataFormatError` | Raised by individual builders and structures |

Request and response bodies are logged with password, token and secret values redacted.

```python
from pyhugegraph.utils.exceptions import NotFoundError

try:
    graph.get_vertex_by_id("no-such-id")
except NotFoundError:
    print("vertex missing")
```

API parameters may change with the HugeGraph REST API version. If an interface is incompatible, first check the REST API documentation for the current server version and the client test cases.

## Development Checks

Run formatting and static checks from the root of the HugeGraph-AI repository:

```bash
uv run --extra dev ruff format --check .
uv run --extra dev ruff check .
uv run --extra dev ty check hugegraph-python-client/src/pyhugegraph
```

Run the tests the same way CI does:

```bash
# Unit and contract tests, no server needed
uv run pytest hugegraph-python-client/src/tests -m "unit or contract"

# Integration tests against a running server
HUGEGRAPH_URL=http://127.0.0.1:8080 \
HUGEGRAPH_GRAPH=hugegraph \
HUGEGRAPH_USER=admin \
HUGEGRAPH_PASSWORD=admin \
uv run pytest hugegraph-python-client/src/tests -m "integration and hugegraph"
```

Use upstream `hugegraph/hugegraph:latest` for primary integration validation and 1.7 for compatibility regression. `HUGEGRAPH_GRAPHSPACE` is also read when you need a non-default space.

The source code and tests are under `hugegraph-python-client/src/pyhugegraph/` and `hugegraph-python-client/src/tests/`. A runnable example is at `hugegraph-python-client/src/pyhugegraph/example/hugegraph_example.py`.

## OLTP or OLAP?

Use `client.traverser()` for immediate neighbourhood/path queries (OLTP).
Use `client.olap()` for whole-graph computation scheduled as an asynchronous server task.
The new interfaces below describe master source; verify availability in your installed client release.

```python
print(client.traverser().k_out(vertex_id, 2, direction="OUT", limit=100))
receipt = client.olap().count_vertex()
task = client.task().wait(receipt["task_id"], timeout=300)
print(client.task().result(task))
```

`client.olap().run("count_vertex", timeout=60)` combines submission, waiting and result decoding.
A waiting timeout does not cancel the remote job. PageRank writes computed properties to the graph.
Close the owning client, not individual managers. New code uses `snake_case`; existing public CamelCase names remain aliases.
See the [API reference and migration notes](/docs/clients/hugegraph-python-client/) for all 17 named algorithms,
the complete REST surface, server compatibility and deployment-specific extensions.

For deployments that require explicit schema preparation, declare nullable DOUBLE property `r_rank` on participating vertex labels before PageRank.

```python
client.close()
```
