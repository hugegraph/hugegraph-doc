---
title: "Python 客户端 API 参考"
linkTitle: "Python API"
weight: 3
description: "Python SDK 的 OLTP 遍历、OLAP 全图计算、任务等待、完整 REST 接口与迁移说明。"
---

连接和建图示例见 [快速上手](/cn/docs/quickstart/client/hugegraph-client-python/)。
本页描述主线源码接口，对齐 server 提交 `8e327b8f3d3ffcf61547be7fea1a15d3af2de8b4`；旧发行包可能尚未包含新入口。
客户端要求 Python 3.12+。Server 1.5/1.6 的路由差异集中在适配层，1.7+ 使用 graphspace 路由。

## 选择入口

| 需求 | Python 入口 |
| --- | --- |
| 立即返回的邻居、路径查询（OLTP） | `client.traverser()` |
| 立即返回的推荐排序（OLTP） | `client.rank()` |
| 异步全图计算（OLAP） | `client.olap()` |
| 任务状态、等待、取消和删除 | `client.task()` |
| Schema 和图数据 | `client.schema()`、`client.graph()` |
| 图、图空间和 Schema 模板 | `client.graphs()`、`client.graphspaces()`、`client.schema_templates()` |
| 查询及重建作业 | `client.gremlin()`、`client.cypher()`、`client.rebuild()` |
| 完整 REST 请求及扩展接口 | `client.rest()` |

## OLAP 全图任务

```python
receipt = client.olap().count_vertex()
task = client.task().wait(receipt["task_id"], timeout=300, poll_interval=1)
result = client.task().result(task)

result = client.olap().run("count_vertex", timeout=60)
```

具名方法和 `submit(name, parameters=None)` 返回 server 原生任务回执；`run()` 返回解析后的结果。
参数透传给 server 校验，也允许新增或自定义算法名；不同算法保留各自的结果结构。
PageRank 等算法会将属性写回图中。Server 注册了 20 个实现类，但只有 17 个不同的算法名，V2 不对应额外端点：

- `count_edge`
- `count_vertex`
- `subgraph_stat`
- `betweenness_centrality`
- `closeness_centrality`
- `degree_centrality`
- `eigenvector_centrality`
- `stress_centrality`
- `cluster_coefficient`
- `k_core`
- `louvain`
- `lpa`
- `triangle_count`
- `weak_connected_component`
- `rings`
- `page_rank`
- `fusiform_similarity`

## 任务、认证和资源生命周期

`wait(id, timeout=300, poll_interval=1)` 轮询时不加载结果，完成后再读取结果并返回任务记录。
`result(task)` 对序列化 JSON 解析一次，普通文本保持文本。
任务失败或取消分别抛出 `TaskFailedError`、`TaskCancelledError`，可通过 `.task`、`.task_id` 检查上下文。
`TaskTimeoutError` 仅停止等待，不取消远端任务；HTTP 超时和等待时限是两个独立控制。
取消使用 `cancel_task(id)`；`delete_task(id, force=False)` 删除任务记录。
`list_tasks(status=None, limit=None, ids=None, page=None)` 支持批量 ID；`ids` 不可与 `status` 或 `page` 同时使用。

一个 `PyHugeClient` 拥有所有资源共享的 session；使用上下文管理或 `client.close()` 释放连接。
`client.use_token(token)` 显式选择 Bearer 认证，传 `None` 恢复 Basic；登录、验证和注销不会自动修改 session 凭据。
版本探测失败会报错；显式指定 graphspace 则直接选择该路由模式，不进行探测。

需要显式准备 Schema 的部署，应在运行 PageRank 前为参与计算的顶点标签声明可空 DOUBLE 属性 `r_rank`。

图空间管理需要部署启用相应能力；能够使用 standalone 的 graphspace 路由，并不意味着支持图空间管理。

旧版 server 可能忽略 `with_result=false`，在轮询时仍返回任务结果。

## 迁移

公共方法及对象属性统一为 `snake_case`，不保留 CamelCase 别名。
例如 `propertyKey` → `property_key`、`asText` → `as_text`、`addVertex` → `add_vertex`、`outV` → `out_v`。
Server JSON 字段仍使用原格式，例如 `outV`；`get_all_graphs()` 返回 `{"graphs": [...]}`。
关闭操作改为由 client 统一负责。加权及单源最短路径不再接受 server 本就不支持的 `max_depth`，请使用相应容量、度数或结果数参数。

## 完整 REST 与扩展能力

需要完整 server 请求体和响应时，直接使用显式资源方法：

```python
rest = client.rest()
print(rest.vertex.list(label="person", offset=0, limit=20))
print(rest.task.list(status="success", page="", limit=20))
# Requires graphspace management support in the deployment:
# print(client.graphspaces().list())
```

JSON、文本响应保留原生结构，HTTP 204 返回空字典。
Raft、Arthas、IP 白名单、异常追踪和外部 Computer 作业提交使用独立资源，需要相应配置和权限；REST 封装本身不部署外部服务。
旧 Services 模块面向定制部署，不属于固定 server 提交的标准端点；Property CAS 也不宣称为已实现的 REST 功能。
图配置导出返回源文本，需要图具有本地配置文件来源。

下表与 Python REST 资源来自同一份契约。在 HugeGraph-AI 中运行 `python scripts/client_api.py --check` 检查同步，
使用 `python scripts/client_api.py --openapi server-openapi.json` 对比 server 导出的 OpenAPI；算法名需额外核对 server 注册表。
Jersey 自动生成的 WADL 元数据不计入 SDK 操作。

### REST 操作参考

<!-- BEGIN REST CONTRACT -->
| Python REST entry | Method | Path | Query parameters |
| --- | --- | --- | --- |
| `rest.access.create()` | POST | `/graphspaces/{graphspace}/auth/accesses` | — |
| `rest.access.delete()` | DELETE | `/graphspaces/{graphspace}/auth/accesses/{id}` | — |
| `rest.access.get()` | GET | `/graphspaces/{graphspace}/auth/accesses/{id}` | — |
| `rest.access.list()` | GET | `/graphspaces/{graphspace}/auth/accesses` | group, target, limit |
| `rest.access.update()` | PUT | `/graphspaces/{graphspace}/auth/accesses/{id}` | — |
| `rest.adamic_adar.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/adamicadar` | vertex, other, direction, label, max_degree, limit |
| `rest.algorithm.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/jobs/algorithm/{name}` | — |
| `rest.all_shortest_paths.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/allshortestpaths` | source, target, direction, label, max_depth, max_degree, skip_degree, with_vertex, with_edge, capacity |
| `rest.arthas.start_arthas()` | PUT | `/arthas` | — |
| `rest.belong.create()` | POST | `/graphspaces/{graphspace}/auth/belongs` | — |
| `rest.belong.delete()` | DELETE | `/graphspaces/{graphspace}/auth/belongs/{id}` | — |
| `rest.belong.get()` | GET | `/graphspaces/{graphspace}/auth/belongs/{id}` | — |
| `rest.belong.list()` | GET | `/graphspaces/{graphspace}/auth/belongs` | user, group, limit |
| `rest.belong.update()` | PUT | `/graphspaces/{graphspace}/auth/belongs/{id}` | — |
| `rest.computer.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/jobs/computer/{name}` | — |
| `rest.count.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/count` | — |
| `rest.crosspoints.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/crosspoints` | source, target, direction, label, max_depth, max_degree, capacity, limit |
| `rest.customized_crosspoints.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/customizedcrosspoints` | — |
| `rest.customized_paths.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/customizedpaths` | — |
| `rest.cypher.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/cypher` | — |
| `rest.cypher.query()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/cypher` | cypher |
| `rest.edge.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges` | — |
| `rest.edge.create_batch()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges/batch` | check_vertex |
| `rest.edge.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges/{id}` | label |
| `rest.edge.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges/{id}` | — |
| `rest.edge.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges` | vertex_id, direction, label, properties, keep_start_p, offset, page, limit |
| `rest.edge.update_batch()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges/batch` | — |
| `rest.edge.update_by_id()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/graph/edges/{id}` | action |
| `rest.edge_existence.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/edgeexist` | source, target, label, sort_values, limit |
| `rest.edge_label.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/schema/edgelabels` | — |
| `rest.edge_label.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/schema/edgelabels/{name}` | — |
| `rest.edge_label.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/edgelabels/{name}` | — |
| `rest.edge_label.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/edgelabels` | names |
| `rest.edge_label.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/schema/edgelabels/{name}` | action |
| `rest.edges.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/edges` | ids |
| `rest.edges.scan()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/edges/scan` | start, end, page, page_limit |
| `rest.edges.shards()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/edges/shards` | split_size |
| `rest.exception_trace.get()` | GET | `/exception/trace` | — |
| `rest.exception_trace.trace()` | PUT | `/exception/trace` | — |
| `rest.fusiform_similarity.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/fusiformsimilarity` | — |
| `rest.graph_space.check_default_role()` | GET | `/graphspaces/{graphspace}/role` | user, role, graph |
| `rest.graph_space.create()` | POST | `/graphspaces` | — |
| `rest.graph_space.delete()` | DELETE | `/graphspaces/{name}` | — |
| `rest.graph_space.delete_default_role()` | DELETE | `/graphspaces/{graphspace}/role` | user, role, graph |
| `rest.graph_space.get()` | GET | `/graphspaces/{graphspace}` | — |
| `rest.graph_space.list()` | GET | `/graphspaces` | — |
| `rest.graph_space.list_profile()` | GET | `/graphspaces/profile` | prefix |
| `rest.graph_space.manage()` | PUT | `/graphspaces/{name}` | — |
| `rest.graph_space.set_default_role()` | POST | `/graphspaces/{graphspace}/role` | — |
| `rest.graph_space_group.create()` | POST | `/graphspaces/{graphspace}/auth/groups` | — |
| `rest.graph_space_group.delete()` | DELETE | `/graphspaces/{graphspace}/auth/groups/{id}` | — |
| `rest.graph_space_group.get()` | GET | `/graphspaces/{graphspace}/auth/groups/{id}` | — |
| `rest.graph_space_group.list()` | GET | `/graphspaces/{graphspace}/auth/groups` | limit |
| `rest.graph_space_group.update()` | PUT | `/graphspaces/{graphspace}/auth/groups/{id}` | — |
| `rest.graphs.clear()` | DELETE | `/graphspaces/{graphspace}/graphs/{name}/clear` | confirm_message |
| `rest.graphs.clone_schema()` | POST | `/graphspaces/{graphspace}/graphs/{name}/schema-clone` | source |
| `rest.graphs.compact()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/compact` | — |
| `rest.graphs.create()` | POST | `/graphspaces/{graphspace}/graphs/{name}` | clone_graph_name |
| `rest.graphs.create_by_text()` | POST | `/graphspaces/{graphspace}/graphs/{name}` | clone_graph_name |
| `rest.graphs.create_snapshot()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/snapshot_create` | — |
| `rest.graphs.drop()` | DELETE | `/graphspaces/{graphspace}/graphs/{name}` | confirm_message |
| `rest.graphs.get()` | GET | `/graphspaces/{graphspace}/graphs/{name}` | — |
| `rest.graphs.get_conf()` | GET | `/graphspaces/{graphspace}/graphs/{name}/conf` | — |
| `rest.graphs.get_default()` | GET | `/graphspaces/{graphspace}/graphs/default` | — |
| `rest.graphs.graph_read_mode_get()` | GET | `/graphspaces/{graphspace}/graphs/{name}/graph_read_mode` | — |
| `rest.graphs.graph_read_mode_set()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/graph_read_mode` | — |
| `rest.graphs.list()` | GET | `/graphspaces/{graphspace}/graphs` | — |
| `rest.graphs.list_profile()` | GET | `/graphspaces/{graphspace}/graphs/profile` | prefix |
| `rest.graphs.loading_mode_get()` | GET | `/graphspaces/{graphspace}/graphs/{name}/mode/owners` | — |
| `rest.graphs.loading_mode_set()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/mode/owners` | — |
| `rest.graphs.manage()` | PUT | `/graphspaces/{graphspace}/graphs/{name}` | — |
| `rest.graphs.mode_get()` | GET | `/graphspaces/{graphspace}/graphs/{name}/mode` | — |
| `rest.graphs.mode_set()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/mode` | — |
| `rest.graphs.reload()` | PUT | `/graphspaces/{graphspace}/graphs/manage` | — |
| `rest.graphs.resume_snapshot()` | PUT | `/graphspaces/{graphspace}/graphs/{name}/snapshot_resume` | — |
| `rest.graphs.set_default()` | POST | `/graphspaces/{graphspace}/graphs/{name}/default` | — |
| `rest.graphs.unset_default()` | DELETE | `/graphspaces/{graphspace}/graphs/{name}/default` | — |
| `rest.gremlin.get()` | GET | `/gremlin` | — |
| `rest.gremlin.post()` | POST | `/gremlin` | — |
| `rest.gremlin_job.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/jobs/gremlin` | — |
| `rest.group.create()` | POST | `/auth/groups` | — |
| `rest.group.delete()` | DELETE | `/auth/groups/{id}` | — |
| `rest.group.get()` | GET | `/auth/groups/{id}` | — |
| `rest.group.list()` | GET | `/auth/groups` | limit |
| `rest.group.update()` | PUT | `/auth/groups/{id}` | — |
| `rest.index_label.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/schema/indexlabels` | — |
| `rest.index_label.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/schema/indexlabels/{name}` | — |
| `rest.index_label.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/indexlabels/{name}` | — |
| `rest.index_label.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/indexlabels` | names |
| `rest.index_label.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/schema/indexlabels/{name}` | action |
| `rest.jaccard_similarity.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/jaccardsimilarity` | vertex, other, direction, label, max_degree |
| `rest.jaccard_similarity.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/jaccardsimilarity` | — |
| `rest.kneighbor.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/kneighbor` | source, direction, label, max_depth, count_only, max_degree, limit |
| `rest.kneighbor.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/kneighbor` | — |
| `rest.kout.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/kout` | source, direction, label, max_depth, nearest, count_only, max_degree, capacity, limit |
| `rest.kout.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/kout` | — |
| `rest.login.login()` | POST | `/auth/login` | — |
| `rest.login.logout()` | DELETE | `/auth/logout` | — |
| `rest.login.verify_token()` | GET | `/auth/verify` | — |
| `rest.manager.check_default_role()` | GET | `/graphspaces/{graphspace}/auth/managers/default` | role, graph |
| `rest.manager.check_role()` | GET | `/graphspaces/{graphspace}/auth/managers/check` | type |
| `rest.manager.create_manager()` | POST | `/graphspaces/{graphspace}/auth/managers` | — |
| `rest.manager.delete()` | DELETE | `/graphspaces/{graphspace}/auth/managers` | user, type |
| `rest.manager.get_roles_in_gs()` | GET | `/graphspaces/{graphspace}/auth/managers/role` | user |
| `rest.manager.list()` | GET | `/graphspaces/{graphspace}/auth/managers` | type |
| `rest.metrics.all()` | GET | `/metrics` | type |
| `rest.metrics.backend()` | GET | `/metrics/backend` | — |
| `rest.metrics.counters()` | GET | `/metrics/counters` | — |
| `rest.metrics.gauges()` | GET | `/metrics/gauges` | — |
| `rest.metrics.histograms()` | GET | `/metrics/histograms` | — |
| `rest.metrics.meters()` | GET | `/metrics/meters` | — |
| `rest.metrics.statistics()` | GET | `/metrics/statistics` | type |
| `rest.metrics.system()` | GET | `/metrics/system` | — |
| `rest.metrics.timers()` | GET | `/metrics/timers` | — |
| `rest.multi_node_shortest_path.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/multinodeshortestpath` | — |
| `rest.neighbor_rank.neighbor_rank()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/neighborrank` | — |
| `rest.paths.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/paths` | source, target, direction, label, max_depth, max_degree, capacity, limit |
| `rest.paths.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/paths` | — |
| `rest.personal_rank.personal_rank()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/personalrank` | — |
| `rest.profile.get_profile()` | GET | `/` | — |
| `rest.profile.show_all_ap_is()` | GET | `/apis` | — |
| `rest.project.create()` | POST | `/graphspaces/{graphspace}/auth/projects` | — |
| `rest.project.delete()` | DELETE | `/graphspaces/{graphspace}/auth/projects/{id}` | — |
| `rest.project.get()` | GET | `/graphspaces/{graphspace}/auth/projects/{id}` | — |
| `rest.project.list()` | GET | `/graphspaces/{graphspace}/auth/projects` | limit |
| `rest.project.update()` | PUT | `/graphspaces/{graphspace}/auth/projects/{id}` | action |
| `rest.property_key.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/schema/propertykeys` | — |
| `rest.property_key.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/schema/propertykeys/{name}` | — |
| `rest.property_key.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/propertykeys/{name}` | — |
| `rest.property_key.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/propertykeys` | names |
| `rest.property_key.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/schema/propertykeys/{name}` | action |
| `rest.raft.add_peer()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/raft/add_peer` | group, endpoint |
| `rest.raft.get_leader()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/raft/get_leader` | group |
| `rest.raft.list_peers()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/raft/list_peers` | group |
| `rest.raft.remove_peer()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/raft/remove_peer` | group, endpoint |
| `rest.raft.set_leader()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/raft/set_leader` | group, endpoint |
| `rest.raft.transfer_leader()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/raft/transfer_leader` | group, endpoint |
| `rest.rays.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/rays` | source, direction, label, max_depth, max_degree, capacity, limit, with_vertex, with_edge |
| `rest.rebuild.edge_label_rebuild()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/jobs/rebuild/edgelabels/{name}` | — |
| `rest.rebuild.index_label_rebuild()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/jobs/rebuild/indexlabels/{name}` | — |
| `rest.rebuild.vertex_label_rebuild()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/jobs/rebuild/vertexlabels/{name}` | — |
| `rest.resource_allocation.create()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/resourceallocation` | vertex, other, direction, label, max_degree, limit |
| `rest.rings.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/rings` | source, direction, label, max_depth, source_in_ring, max_degree, capacity, limit, with_vertex, with_edge |
| `rest.same_neighbors.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/sameneighbors` | vertex, other, direction, label, max_degree, limit |
| `rest.same_neighbors.same_neighbors()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/sameneighbors` | — |
| `rest.same_neighbors_batch.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/sameneighborsbatch` | — |
| `rest.schema.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema` | — |
| `rest.schema_template.create()` | POST | `/graphspaces/{graphspace}/schematemplates` | — |
| `rest.schema_template.delete()` | DELETE | `/graphspaces/{graphspace}/schematemplates/{name}` | — |
| `rest.schema_template.get()` | GET | `/graphspaces/{graphspace}/schematemplates/{name}` | — |
| `rest.schema_template.list()` | GET | `/graphspaces/{graphspace}/schematemplates` | — |
| `rest.schema_template.update()` | PUT | `/graphspaces/{graphspace}/schematemplates/{name}` | — |
| `rest.shortest_path.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/shortestpath` | source, target, direction, label, max_depth, max_degree, skip_degree, with_vertex, with_edge, capacity |
| `rest.single_source_shortest_path.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/singlesourceshortestpath` | source, direction, label, weight, max_degree, skip_degree, with_vertex, with_edge, capacity, limit |
| `rest.target.create()` | POST | `/graphspaces/{graphspace}/auth/targets` | — |
| `rest.target.delete()` | DELETE | `/graphspaces/{graphspace}/auth/targets/{id}` | — |
| `rest.target.get()` | GET | `/graphspaces/{graphspace}/auth/targets/{id}` | — |
| `rest.target.list()` | GET | `/graphspaces/{graphspace}/auth/targets` | limit |
| `rest.target.update()` | PUT | `/graphspaces/{graphspace}/auth/targets/{id}` | — |
| `rest.task.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/tasks/{id}` | force |
| `rest.task.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/tasks/{id}` | with_result |
| `rest.task.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/tasks` | status, ids, limit, page |
| `rest.task.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/tasks/{id}` | action |
| `rest.template_paths.post()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/traversers/templatepaths` | — |
| `rest.user.create()` | POST | `/graphspaces/{graphspace}/auth/users` | — |
| `rest.user.delete()` | DELETE | `/graphspaces/{graphspace}/auth/users/{id}` | — |
| `rest.user.get()` | GET | `/graphspaces/{graphspace}/auth/users/{id}` | — |
| `rest.user.list()` | GET | `/graphspaces/{graphspace}/auth/users` | name, limit |
| `rest.user.role()` | GET | `/graphspaces/{graphspace}/auth/users/{id}/role` | — |
| `rest.user.update()` | PUT | `/graphspaces/{graphspace}/auth/users/{id}` | — |
| `rest.variables.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/variables/{key}` | — |
| `rest.variables.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/variables/{key}` | — |
| `rest.variables.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/variables` | — |
| `rest.variables.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/variables/{key}` | — |
| `rest.version.list()` | GET | `/versions` | — |
| `rest.vertex.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices` | — |
| `rest.vertex.create_batch()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices/batch` | — |
| `rest.vertex.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices/{id}` | label |
| `rest.vertex.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices/{id}` | — |
| `rest.vertex.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices` | label, properties, keep_start_p, offset, page, limit |
| `rest.vertex.update_batch()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices/batch` | — |
| `rest.vertex.update_by_id()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/graph/vertices/{id}` | action |
| `rest.vertex_label.create()` | POST | `/graphspaces/{graphspace}/graphs/{graph}/schema/vertexlabels` | — |
| `rest.vertex_label.delete()` | DELETE | `/graphspaces/{graphspace}/graphs/{graph}/schema/vertexlabels/{name}` | — |
| `rest.vertex_label.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/vertexlabels/{name}` | — |
| `rest.vertex_label.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/schema/vertexlabels` | names |
| `rest.vertex_label.update()` | PUT | `/graphspaces/{graphspace}/graphs/{graph}/schema/vertexlabels/{name}` | action |
| `rest.vertices.list()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/vertices` | ids |
| `rest.vertices.scan()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/vertices/scan` | start, end, page, page_limit |
| `rest.vertices.shards()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/vertices/shards` | split_size |
| `rest.weighted_shortest_path.get()` | GET | `/graphspaces/{graphspace}/graphs/{graph}/traversers/weightedshortestpath` | source, target, direction, label, weight, max_degree, skip_degree, with_vertex, with_edge, capacity |
| `rest.white_ip_list.list()` | GET | `/whiteiplist` | — |
| `rest.white_ip_list.update_status()` | PUT | `/whiteiplist` | status |
| `rest.white_ip_list.update_white_i_ps()` | POST | `/whiteiplist` | — |
{.wide}

<!-- END REST CONTRACT -->
