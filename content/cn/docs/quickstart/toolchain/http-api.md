---
title: "Server 与 Hubble HTTP API 示例"
linkTitle: "HTTP API 示例"
description: "选择 GraphSpace Gremlin 绑定、提交异步任务、登录 Hubble 并通过 HTTP 创建 schema。"
weight: 3
---

示例面向 Server 与 Toolchain `master`（1.8）。Server 与 Hubble 使用不同的 HTTP 监听地址和请求格式。
请替换部署地址、凭据、图名与返回的 ID。Helm Service 的查找方法见 [Helm 指南](/cn/docs/quickstart/hugegraph/hugegraph-helm/)。

## Server 路径与图选择

`GET /apis` 是资源索引。索引中的资源路径属于 Server 根地址，应使用 `/versions`、`/graphspaces` 与 `/gremlin`，不要再加 `/apis` 前缀。
旧版索引没有前导斜杠，应相对 Server 根路径解析，不能拼到索引目录下面。网关另有公开路径前缀时，保留该前缀。

`GET /graphspaces` 仅支持 PD 模式。独立模式应跳过此步骤，使用 `GET /graphs` 列出已配置的图。

```bash
curl 'http://localhost:8080/versions'
curl 'http://localhost:8080/graphspaces'
curl 'http://localhost:8080/graphspaces/DEFAULT/graphs'
```

建图使用 `POST /graphspaces/{space}/graphs/{graph}`，并提供后端要求的图配置。`POST /graphs` 不是建图接口。
旧形态 `/graphs` 能列出图，并不表示 GraphSpace API 不存在。运行 SeaTunnel 自带 sink 示例前，请按
[SeaTunnel 指南](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/seatunnel.md) 先创建 `graph_a`。

同步 Gremlin 请求通过 aliases 选择图。对于图空间 `DEFAULT` 中的图 `hugegraph`，使用以下准确名称：

```bash
curl -X POST 'http://localhost:8080/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"gremlin":"g.V().count()","aliases":{"graph":"DEFAULT-hugegraph","g":"__g_DEFAULT-hugegraph"}}'
```

绑定名区分大小写：`<space>-<graph>` 是图，`__g_<space>-<graph>` 是遍历源。多图 Server 没有隐含的全局 `g`。
`bindings` 用于查询变量，不能注册图；alias 目标也不能写成 `graph.traversal()` 表达式。
没有 GraphSpace 的旧版独立图使用 `<graph>` 与 `__g_<graph>`。Server 启用鉴权时，补充配置要求的 HTTP 凭据，例如 `-u "$HG_USER:$HG_PASSWORD"`。

## 长查询使用异步任务

同步 Gremlin 默认执行上限为 30000 毫秒，由 `gremlin-server.yaml` 的 `evaluationTimeout` 配置。
全图计数与按标签过滤计数可能走不同执行路径，不能用 `g.V().count()` 的耗时推断标签扫描耗时。
可能超过同步限制的查询应提交 Server 任务：

```bash
curl -X POST 'http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/jobs/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"gremlin":"g.V().hasLabel(\"person\").count()"}'

# 将 <task_id> 替换为提交响应中的 ID。
curl 'http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/tasks/<task_id>'
```

任务为 URL 中选定的图绑定 `graph` 与 `g`。轮询到 `task_status` 为终态后再读取 `task_result`。
`running` 不表示计数已经完成。请求使用与其他 Server API 相同的鉴权。
Hubble 客户端传输超时与 Server 执行超时是不同限制，仅调整其中一个不会移除另一个。

## Hubble 登录与查询体

鉴权模式下，登录字段使用 **snake_case**，并保存会话 cookie：

```bash
curl -c hubble.cookies -X POST 'http://localhost:8088/api/v1.3/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"user_name":"<username>","user_password":"<password>"}'
```

`userName` 与 `userPassword` 不会填入该登录模型。连续失败可能返回 HTTP 429，请修正字段与凭据后再重试。
匿名模式不使用登录接口。

集成用 Gremlin 接口当前除登录会话外，还要求请求体中的 `username` 与 `password`：

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/gremlin' \
  -H 'Content-Type: application/json' \
  -d '{"query":"g.V().count()","username":"<username>","password":"<password>"}'
```

可信本地网络以外应使用 HTTPS；JSON 本身不会加密口令。这里的 `query` 不同于 Server 的 `gremlin` 字段，
也不同于 Hubble 工作区 `gremlin-query` 请求格式。调用者身份由会话确定，请求体凭据不能替代登录 cookie。

## Hubble schema 默认值

Hubble 在 1.8.0 及以上版本中支持以下可选字段默认值。若使用未包含该特性的旧版本，请在请求体中显式提供 `"open_label_index":true,"style":{"display_fields":["~id"]}`：

使用 Hubble 的 schema 模型创建顶点类型：

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/schema/vertexlabels' \
  -H 'Content-Type: application/json' \
  -d '{"name":"http_demo_person","id_strategy":"AUTOMATIC","properties":[]}'
```

缺少或为 null 的 `style` 使用标准样式并显示 `~id`；
缺少或为 null 的 `open_label_index` 默认为 `true`，显式 `false` 保持不变。
旧构建可显式提供 `"open_label_index":true,"style":{"display_fields":["~id"]}`，避免空值错误。
样式字段使用 snake_case（`display_fields`、`join_symbols`），不能写成 `displayFields`。
`PRIMARY_KEY` 类型还需要 `properties` 和 `primary_keys`；创建标签前应先创建属性。
Server schema 使用不同的请求模型，不要求 Hubble 的视觉样式字段。

## 图统计是近似值

Hubble 概览使用有界扫描。响应包含 `approximate:true` 与 `scan_limit:100000` 时，即使实际有数千万条数据，
顶点或边计数也可能停在 100000。这些值是扫描观测值，不能当作精确总量。
字段名依接口而定，例如 `gremlin-query` 返回 `vertexcount` / `edgecount`。精确计数应读取已完成的异步计数任务结果。

## Server 元素 ID 与更新

Server 顶点 ID 在 URL 路径中使用 JSON 值。字符串 ID `1:marko` 需要 JSON 引号，编码为 `%221%3Amarko%22`；
数值 ID 使用数值的 JSON 形式。边 ID 使用 Server 的原始边 ID 格式，转义 URL 保留字符时不要额外加 JSON 引号。
不能把顶点 ID 编码规则直接套到边 ID 上。

追加属性使用 `PUT .../vertices/{id}?action=append` 或 `PUT .../edges/{id}?action=append`，并提交对应 JSON 属性体。
删除边时按后端要求提供 `DELETE .../edges/{id}?label={label}` 的标签参数。
删除 Server 索引使用 `DELETE .../schema/indexlabels/{name}`，响应为任务 ID；当前 Server 接口没有 `delete_all` 查询参数。
重建顶点、边或索引标签使用 `PUT .../jobs/rebuild/{type}/{name}`：目标标签不存在时返回 HTTP 404；
已有标签返回 HTTP 202 与任务 ID，应轮询任务结果后再确认重建完成。

## Vermeer 服务 token 与原生 UI

Vermeer Master HTTP 遵循 Helm 模式默认值：easy 为 NodePort，strict 为 ClusterIP；RPC 与 Worker 端口保持内部访问。
原生 UI 管理员使用 `<release>-vermeer-admin` 中的密码。自动化 API 使用服务 token，放入 `Authorization: Bearer <token>`，
UI 管理密码不能当作该 token。Chart 会自动为 Hubble 配置服务 token。
原生管理与受控 token 生成步骤见 [Vermeer 指南](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/vermeer.md)。

### 通过 Hubble 提交 Vermeer 计算

使用 Chart 管理的原生集成时，`POST /api/v1.3/vermeer/task` 用于加载或重新加载图，不是计算接口。
该接口接收 `graphspace`、`graph`、`task_type:"load"` 与可选加载调优参数；等图加载完成后，再通过图级计算接口提交算法：

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/algorithms/vermeer' \
  -H 'Content-Type: application/json' \
  -d '{"params":{"compute.algorithm":"pagerank","compute.parallel":1,"compute.max_step":10,"pagerank.damping":0.85,"pagerank.diff_threshold":0.00001}}'
```

参数名与示例值来自当前 Hubble PageRank 表单：

| 参数 | 含义 | 示例 |
|---|---|---|
| `compute.algorithm` | 支持的算法名 | `pagerank` |
| `compute.parallel` | 计算并行度 | `1` |
| `compute.max_step` | 最大迭代步数 | `10` |
| `pagerank.damping` | PageRank 阻尼系数 | `0.85` |
| `pagerank.diff_threshold` | 收敛阈值 | `0.00001` |

当前 Hubble 接受 `pagerank`、`wcc`、`lpa`、`degree`、`closeness_centrality`、`betweenness_centrality`、`triangle_count`、`kcore` 与 `sssp`。
其他算法请使用对应表单中的参数，不能沿用 PageRank 的专属键。
直连适配器接受 `compute.*`、当前算法的 `<algorithm>.*` 与 `output.need_statistics`，具体参数值仍由 Vermeer 校验。
输出存储由 Hubble 管理，不能指定任意输出路径或传入 Server 凭据。

Hubble 响应封装的 `data.task_id` 是任务 ID，请保留正负号：原生 Vermeer 任务会映射为负数 ID。
使用同一图的 `GET /api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/async-tasks/{id}` 查询状态；
成功后通过 `GET .../async-tasks/{id}/values?cursor=0&limit=100` 读取结果分页。
不要把 Hubble ID 直接传给 Server 原生 `/tasks/{id}`。
图状态 `loaded` 只表示加载成功。计算返回 HTTP 400 时，应结合被拒绝的完整请求与响应排查定位。

### 原生 Vermeer 任务提交

原生客户端使用 `POST /api/v1/tasks/create`，请求包含 `graph`、`task_type`（`load`、`reload` 或 `compute`）
及扁平的字符串 `params` 映射。计算算法名填写 `params["compute.algorithm"]`，不是顶层 `algorithm`。
响应中的原生 `task.id` 通过 `GET /api/v1/task/{id}` 查询状态，通过 `GET /api/v1/tasks/value/{id}` 查询保留结果。
这些路径及正数 ID 不同于 Hubble 封装接口。`POST /api/v1/tasks` 不提交任务：修复后返回 HTTP 405 和 `Allow: GET`；
旧构建可能返回误导性的 `{"code":200}`，但实际并未创建任务。
详见 [原生 API 示例](https://github.com/apache/hugegraph-computer/blob/master/vermeer/README.md#api-overview)。

## Hubble 的 Cypher 与任务路由

Hubble Cypher 使用工作区查询模型，不使用集成 Gremlin 的请求模型：

```bash
curl -b hubble.cookies -X POST \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/graphs/hugegraph/cypher' \
  -H 'Content-Type: application/json' \
  -d '{"content":"MATCH (n) RETURN count(n)","preview":false}'
```

查询字段是 `content`，`query` 或嵌套的 `gremlin-query` 对象不会填入该字段；鉴权来自登录会话。
Server 必须声明支持 Cypher。`/asyncTasks` 等路径是 UI 导航路由，任务 API 使用前文所述
`/api/v1.3/graphspaces/{space}/graphs/{graph}/async-tasks` 前缀。

## 通过 Hubble 导入图元素

`POST /api/v1.3/graphspaces/{space}/graphs/{graph}/import` 接收 multipart 字段 `file`，内容是图元素 JSON。
上传内容不是 CSV，也不是 Loader 作业规格；请先创建所引用的 schema。
例如，已有使用 `CUSTOMIZE_STRING` ID、带 `name` 属性的 `person` 顶点类型，以及连接两个 `person` 的 `knows` 边类型时，
将以下内容保存为 `graph.json`：

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

两个数组都必须存在；空数组只执行空导入。请提供 schema 要求的所有非空属性，顶点 ID 必须匹配对应 ID 策略。
边端点使用 `source` 与 `target`；顶点条目中的 `file` 键不是数据源定义。该接口返回图视图，CSV 请使用独立的数据源/Loader 流程。

## 使用图空间权限预设

Server 禁用自定义图空间角色分配时，旧图空间用户 POST 会被策略拒绝。该接口为已有账号分配角色，不是注册账号。
请使用 Hubble 提供的权限预设，不要自行构造角色 ID 或关闭 Server 策略。
对于已有账号，具备授权权限的图空间管理者可这样设置预设：

```bash
curl -b hubble.cookies -X PUT \
  'http://localhost:8088/api/v1.3/graphspaces/DEFAULT/auth/users/<user_id>/preset' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<user_id>","username":"<username>","permission_preset":"GS_READ_ONLY"}'
```

支持 `GS_READ_ONLY`、`GS_READ_WRITE` 与 `GS_ADMIN`，具体授权仍受调用者权限约束。
路径与请求体中的账号身份必须匹配；匿名模式不提供账号管理能力。
