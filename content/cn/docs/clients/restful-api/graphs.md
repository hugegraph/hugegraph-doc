---
title: "Graphs API"
linkTitle: "Graphs"
weight: 12
description: "Graphs（图管理）REST 接口:管理图实例的生命周期,包括创建、查询、克隆、清空和删除图数据库。"
---

### 6.1 Graphs

> [!WARNING]
> 生产环境必须启用 [Server 认证与授权](/cn/docs/config/config-authentication/)，通过 IP 白名单及最小权限控制图管理接口的访问，并保留 `audit-*.log` 审计记录。下文非鉴权配置仅用于隔离的本地测试。

> 本页介绍当前 master 的 Graphs API。历史版本的路径和请求体请切换到对应多版本页面： [1.7 版 Graphs API](https://hugegraph.apache.org/versions/1.7/cn/docs/clients/restful-api/graphs/) 或
> [1.5 版 Graphs API](https://hugegraph.apache.org/versions/1.5/cn/docs/clients/restful-api/graphs/)。

启用鉴权时，创建、克隆、删除、清空、修改图显示名、读取图配置、设置读模式和手动压缩等操作要求图空间管理权限（`space`）；管理员可按权限继承规则满足。创建或恢复快照、设置数据模式允许图空间管理者或该图所有者操作；列表、详情、数据模式读取和读模式读取按图读取权限校验。Raft API 另要求图空间成员权限。

#### 6.1.1 列出图空间中全部的图

##### Params

**路径参数说明：**

- graphspace: 图空间名称

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "graphs": [
        "hugegraph",
        "hugegraph1"
    ]
}
```

#### 6.1.2 查看某个图的信息

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "name": "hugegraph",
    "backend": "rocksdb"
}
```

#### 6.1.3 清空某个图的全部数据，包括 schema、vertex、edge 和 index 等

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

**请求参数说明：**

由于清空图是一个比较危险的操作，为避免用户误调用，我们给 API 添加了用于确认的参数：

- confirm_message: 默认为`I'm sure to delete all data`

##### Method & Url

```text
DELETE http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/clear?confirm_message=I%27m+sure+to+delete+all+data
```

##### Response Status

```javascript
204
```

#### 6.1.4 克隆一个图

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 要创建的新图名称

**请求参数说明：**

- clone_graph_name: 已有图的名称；从已有的图来克隆，用户可选择传递配置文件，传递时将替换已有图中的配置；

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/cloneGraph?clone_graph_name=hugegraph
```

##### Request Body (可选)

克隆一个非鉴权模式的图（设置 `Content-Type: application/json`）

```javascript
{
  "gremlin.graph": "org.apache.hugegraph.HugeFactory",
  "backend": "rocksdb",
  "serializer": "binary",
  "store": "cloneGraph",
  "rocksdb.data_path": "./rks-data-xx",
  "rocksdb.wal_path": "./rks-data-xx"
}
```

> Note:
> 1. Rocksdb 存储路径不能与现有图相同（需使用不同的目录）
> 2. 如需开启新图的权限系统，需替换设置 `gremlin.graph=org.apache.hugegraph.auth.HugeFactoryAuthProxy`

##### Response Status

```javascript
201
```

##### Response Body

```javascript
{
    "name": "cloneGraph",
    "nickname": "cloneGraph",
    "backend": "rocksdb",
    "description": ""
}
```

#### 6.1.5 创建一个图

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph-xx
```

##### Request Body

创建一个图（设置 `Content-Type: application/json`）

**`gremlin.graph` 配置说明：**
- 鉴权模式：`"gremlin.graph": "org.apache.hugegraph.auth.HugeFactoryAuthProxy"`（生产环境必须使用）
- 非鉴权模式：`"gremlin.graph": "org.apache.hugegraph.HugeFactory"`

**注意**：如果 backend 是 hstore，请确保 HugeGraph-Server 已正确配置 PD，参见 [HStore 配置](/cn/docs/quickstart/hugegraph/hugegraph-server/#511-分布式存储-hstore)。调度器由后端类型决定：hstore 使用分布式调度器，其他后端使用本地调度器。

**选填字段及其默认值：**
- `gremlin.graph` 默认为 `org.apache.hugegraph.HugeFactory`
- `backend` 在 PD 模式下默认为 `hstore`，否则默认为 `rocksdb`
- `serializer` 默认为 `binary`
- `store` 默认为图名称
- `nickname` 设置图的显示名，在图空间内必须唯一
- `schema` 指定初始化该图所用的 [schema 模板](./graphspace)，会被保存为 `schema.init_template`
- `description` 会原样返回在响应中

**RocksDB 示例：**

```javascript
{
  "gremlin.graph": "org.apache.hugegraph.auth.HugeFactoryAuthProxy",
  "backend": "rocksdb",
  "serializer": "binary",
  "store": "hugegraph",
  "rocksdb.data_path": "./rks-data-xx",
  "rocksdb.wal_path": "./rks-data-xx"
}
```

**HStore 示例：**

```javascript
{
  "gremlin.graph": "org.apache.hugegraph.auth.HugeFactoryAuthProxy",
  "backend": "hstore",
  "serializer": "binary",
  "store": "hugegraph2",
  "pd.peers": "127.0.0.1:8686"
}
```

> Note: Rocksdb 存储路径不能与现有图相同（需使用不同的目录）

##### Response Status

```javascript
201
```

##### Response Body

```javascript
{
    "name": "hugegraph2",
    "nickname": "hugegraph2",
    "backend": "rocksdb",
    "description": ""
}
```

#### 6.1.6 删除某个图及其全部数据

启用鉴权时需要图空间管理权限（`space`）。

删图前先停止业务写入，并在失败及重试期间持续隔离该图、保持停写。
删除失败的清理和重试完成前，所有 Server 都不得在该图空间中重建同名图。
首轮清空后端失败时，重试会再次清空后端，可能删除其他 Server 随后写入的新数据。删除接口不隔离其他请求中的图写事务。
调度器开始关闭后会拒绝新任务；删除失败不会自动重新开放已关闭的任务准入。

启用 PD 时，`DEFAULT` 中已成功加载的本地图会拒绝公开删除，不受 `graph.load_from_local_config` 影响；设为 `true` 时，还保护成功扫描到的全部配置名，
包括本地加载失败后由 PD 元数据恢复的同名图。先移除文件，再执行 reload，目录扫描成功即在分离图之前解除保护；后续阶段返回 HTTP 400 也不回滚该快照。
也可重启 Server。其他图空间的同名图不受此本地文件保护。

移除图时捕获到 `close()` 异常，若图已标记关闭，会记录异常并移除运行时绑定；若图仍未关闭，则只保留注册供继续清理和重试，不表示可以恢复业务使用。
后端数据或 PD 元数据可能已被移除。删图不是事务操作，重试不会回滚删除，也不会恢复已移除的后端数据或 PD 元数据。

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

**请求参数说明：**

由于删除图是一个比较危险的操作，为避免用户误调用，我们给 API 添加了用于确认的参数：

- confirm_message: 默认为`I'm sure to drop the graph`

##### Method & Url

```javascript
DELETE http://localhost:8080/graphspaces/DEFAULT/graphs/graphA?confirm_message=I%27m%20sure%20to%20drop%20the%20graph
```

##### Response Status

```javascript
204
```

#### 6.1.7 列出图空间中全部的图及其配置

对当前用户有读权限的每个图返回一条记录，其中包含该图的配置（形如密码、密钥、token、凭证、私钥的配置项会被过滤掉）以及下面这些字段。当前用户的默认图会排在前面。

##### Params

**路径参数说明：**

- graphspace: 图空间名称

**请求参数说明：**

- prefix: 只返回名称或显示名以该前缀开头的图

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/profile
```

##### Response Status

```javascript
200
```

##### Response Body

`default_update_time` 只在该图是当前用户的默认图时返回，`create_time` 只在该图记录了创建时间时返回。

```javascript
[
  {
    "backend": "rocksdb",
    "serializer": "binary",
    "store": "hugegraph",
    "name": "hugegraph",
    "nickname": "hugegraph",
    "graphspace_nickname": "DEFAULT",
    "default": true,
    "default_update_time": "2024-05-01 12:30:00",
    "create_time": "2024-05-01 12:00:00"
  }
]
```

#### 6.1.8 修改某个图的显示名

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

**请求参数说明：**

- action: 固定为 `update`
- update: 需要修改的字段。`name` 必填且必须与路径中的图名一致，`nickname` 是新的显示名，在图空间内必须唯一。

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph
```

##### Request Body

```javascript
{
  "action": "update",
  "update": {
    "name": "hugegraph",
    "nickname": "MyGraph"
  }
}
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "hugegraph": "updated"
}
```

#### 6.1.9 管理当前用户的默认图

默认图是按用户记录的，因此下面的接口都以调用者的身份生效。它们依赖权限系统，未开启权限的单机模式下会返回 `400` 和 `GraphSpace management is not supported in standalone mode`。

##### 设置默认图

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/default
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default_graph": [
    "hugegraph"
  ]
}
```

##### 取消默认图

##### Method & Url

```text
DELETE http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/default
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default_graph": []
}
```

##### 查看默认图

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/default
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default_graph": [
    "hugegraph"
  ]
}
```

#### 6.1.10 重新加载图空间中的图

在图配置变更后，重新加载此 Server 持有的所有图。Reload 保留后端数据和本地配置文件。

每个图管理器中的 reload、图移除、图空间清空和移除，以及 API 建图和克隆共用生命周期协调入口。
启用 PD 时，缓存未命中的图加载从读取元数据到注册本地实例也使用该入口；已缓存图的读取不受其阻塞。
这不会隔离所有 HTTP 请求或图事务；远端图新增与移除通知也使用同一入口。
启动时加载本地图配置会等待当前生命周期操作结束，没有可配置的等待超时；中断等待会中止启动。
重叠的生命周期 API 请求仍会立即拒绝。
重叠的 reload 或图移除 REST 请求会在扫描配置或改动图之前返回 HTTP 400。
当前操作持续占用该入口直到结束，包括 reload 完整的关闭与重开过程。操作结束后，包括失败或超时，需显式重试被拒绝的 REST 请求。
操作执行期间收到的远端图新增与移除通知会延后处理，待当前操作结束后按当前 PD 配置协调。
对于从 PD 加载且不受 `DEFAULT` 本地配置保护的图，
仅在本地实例的创建信息和打开图时使用的配置仍与当前 PD 记录一致时保留该实例。
若二者不同，Server 关闭旧实例并按当前 PD 配置重新加载；图仍在 PD 中登记时，不回收其图空间配额。
受 `DEFAULT` 本地配置保护的图仍沿用下文的本地保护规则。
若创建信息和打开配置完全相同，包括复用了旧创建时间，Server 无法可靠区分旧实例和重新创建的同名图。
维护期间须持续停写，再显式 reload 或重启 Server 并确认实际加载的是预期图。
若替换图的加载或启动失败，当前 Server 可能暂时缺少该图；须持续停写，排除故障后显式 reload 或重启 Server 恢复。
下文的 reload 预检限制同样适用；这些步骤不是分布式事务。
实际关闭图失败时仍会记录异常，并需要显式重试。

通过预检且未启用 PD 时，reload 会重扫启动图配置目录中的所有当前文件，即使 `graph.load_from_local_config=false`。
启用 PD 且该选项为 `false` 时，只恢复之前成功加载且配置文件仍存在的本地图，不加载新增本地文件；设为 `true` 时还会发现新增本地文件。
先加载本地配置，再从 PD 元数据加载尚未恢复的图。新加载的图在启用 RPC 时先等待就绪，再完成启动和任务调度初始化，然后恢复 Gremlin 图与遍历绑定。

目录扫描成功后，会在关闭图之前更新本地来源记录；启用 PD 时，也会更新本地图删除保护。扫描失败时会在关闭任何图之前返回 HTTP 400，保留现有图和保护状态。
启用 PD 时，`DEFAULT` 中已成功加载的本地图在配置文件仍存在时会拒绝公开删除，不受 `graph.load_from_local_config` 影响，无论删除是否要求清空数据。
其他图空间的同名图不受该本地文件保护。启用 PD 且设为 `true` 时，保护还覆盖成功扫描到的全部配置名，即使本地加载失败后由 PD 元数据恢复同名图也受保护。
启用 PD 且设为 `false` 时，从未加载的新增本地文件仍被忽略，也不会建立删除保护。移除配置文件后，reload 中的目录扫描成功即在分离图之前清除对应来源和保护。
后续打开或启动失败、整个 reload 返回 HTTP 400，也不会回滚已成功扫描的快照。旧实例成功关闭并分离后，若 PD 元数据中仍有该图，则可恢复并公开删除；
否则移除其运行时注册，但保留后端数据。关闭尝试后图仍未关闭时，保留旧注册供显式重试。
图已标记关闭后捕获到关闭异常时，会记录异常并移除运行时绑定。本地启动来源已移除，下次重启不会再从已删除的文件加载该图。
来源记录跟随实际注册的图实例；旧实例移除不会清除新的本地替代实例。公开删除 `DEFAULT` 中的图时，仅在删除完成后清除对应的来源记录。
未启用 PD 时，公开删除图仍会清空数据并移除本地配置，上述 PD 删除保护不适用。

配置了 `auth.authenticator` 时，请求会在关闭任何图之前返回 HTTP 400，因为鉴权服务保留了图引用。此类部署需要重启 Server 应用图配置变化，
被拒绝的 reload 不会改动原有图、数据或配置。

关闭尝试后仍未关闭的图会保留注册，供显式重试；重载启动失败后，清理时仍未关闭的对象也会保留。其他可恢复的图可能先完成重载，再汇报打开或启动失败。不完整的 reload 会返回 HTTP 400，
部分图恢复成功不能作为整个请求成功的依据。排除故障后重试。

受管理的图已注册图/Schema 缓存通知 RPC 服务时，reload 同样会在关闭任何图之前返回 HTTP 400。这些服务的安全重绑尚未实现，需要重启 Server
应用变化；该拒绝会保留原有图、数据和配置。此类热重载需要在 Linux 高性能机器的分布式部署中完成修复与验证后再使用。
未触发上述预检限制时，PD/本地配置的来源选择规则仍然适用，但不代表完整的分布式热重载支持。

##### Params

**路径参数说明：**

- graphspace: 图空间名称

**请求参数说明：**

- action: 固定为 `reload`

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/manage
```

##### Request Body

```javascript
{
  "action": "reload"
}
```

##### Response Status

```javascript
200
```

HTTP 400 表示配置了鉴权器、图/Schema 缓存通知 RPC 服务已注册、重叠的 reload/图移除请求、目录扫描失败，或图重载未完整完成。
HTTP 200 表示允许执行的图重载步骤未汇报失败。

##### Response Body

```javascript
{
  "graphs": "reloaded"
}
```

### 6.2 Conf

#### 6.2.1 查看某个图的配置

##### Method & Url

```javascript
GET
http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/conf
```

##### Response Status

```javascript
200
```

##### Response Body

```properties
# gremlin entrence to create graph
gremlin.graph=org.apache.hugegraph.HugeFactory
# cache config
#schema.cache_capacity=1048576
#graph.cache_capacity=10485760
#graph.cache_expire=600

# schema illegal name template
#schema.illegal_name_regex=\s+|~.*

#vertex.default_label=vertex

backend=rocksdb
serializer=binary

store=hugegraph
...=
```

### 6.3 Mode

合法的图模式包括：NONE，RESTORING，MERGING，LOADING

- None 模式（默认），元数据和图数据的写入属于正常状态。特别的：
    - 元数据（schema）创建时不允许指定 ID
    - 图数据（vertex）在 id strategy 为 Automatic 时，不允许指定 ID
- LOADING：批量导入数据时自动启用，特别的：
    - 添加顶点/边时，不会检查必填属性是否传入

Restore 时存在两种不同的模式：Restoring 和 Merging

- Restoring 模式，恢复到一个新图中，特别的：
    - 元数据（schema）创建时允许指定 ID
    - 图数据（vertex）在 id strategy 为 Automatic 时，允许指定 ID
- Merging 模式，合并到一个已存在元数据和图数据的图中，特别的：
    - 元数据（schema）创建时不允许指定 ID
    - 图数据（vertex）在 id strategy 为 Automatic 时，允许指定 ID

正常情况下，图模式为 None，当需要 Restore 图时，需要根据需要临时修改图模式为 Restoring 模式或者 Merging 模式，并在完成 Restore 时，恢复图模式为 None。

#### 6.3.1 查看某个图的模式

启用鉴权时需要图读取权限（`space_member` 或该图的所有者）。

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/mode
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "mode": "NONE"
}
```

> 合法的图模式包括：NONE，RESTORING，MERGING，LOADING

#### 6.3.2 设置某个图的模式

启用鉴权时需要图空间管理权限（`space`）或该图所有者权限；管理员可按权限继承规则满足。

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/mode
```

##### Request Body

```text
"RESTORING"
```

> 合法的图模式包括：NONE，RESTORING，MERGING，LOADING

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "mode": "RESTORING"
}
```

#### 6.3.3 查看某个图的读模式

启用鉴权时需要图读取权限（`space_member` 或该图的所有者）。

##### Params

- name: 图的名称

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/graph_read_mode
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "graph_read_mode": "ALL"
}
```

#### 6.3.4 设置某个图的读模式

启用鉴权时需要图空间管理权限（`space`）；管理员可按权限继承规则满足。

##### Params

- name: 图的名称

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/graph_read_mode
```

##### Request Body

```text
"OLTP_ONLY"
```

> 合法的读模式包括：ALL，OLTP_ONLY。传入 OLAP_ONLY 时接口会报错 `Graph-read-mode could be ALL or OLTP_ONLY`。

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "graph_read_mode": "OLTP_ONLY"
}
```

### 6.4 Snapshot

#### 6.4.1 创建快照

启用鉴权时需要图空间管理权限（`space`）或该图所有者权限；管理员可按权限继承规则满足。

##### Params

- name: 图的名称

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/snapshot_create
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "hugegraph": "snapshot_created"
}
```

#### 6.4.2 快照恢复

启用鉴权时需要图空间管理权限（`space`）或该图所有者权限；管理员可按权限继承规则满足。

##### Params

- name: 图的名称

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/snapshot_resume
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "hugegraph": "snapshot_resumed"
}
```

### 6.5 Compact

#### 6.5.1 手动压缩图

启用鉴权时需要图空间管理权限（`space`）；管理员可按权限继承规则满足。

##### Params

- name: 图的名称

##### Method & Url

```text
PUT http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/compact
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
    "nodes": 1,
    "cluster_id": "local",
    "servers": {
        "local": "OK"
    }
}
```

### 6.6 Raft

以下接口只在图运行于 raft 模式时可用，参见 [配置项](/cn/docs/config/config-option/) 中的 `raft.mode`。未开启 raft 模式的图会返回 `400` 和 `Allowed <operation> operation only when working on raft mode`。

启用鉴权时需要图空间成员权限（`space_member`）；管理员可按权限继承规则满足。

##### Params

**路径参数说明：**

- graphspace: 图空间名称
- graph: 图名称

**请求参数说明：**

- group: raft 组名称，默认为 `default`
- endpoint: 节点地址，形如 `host:port`。`transfer_leader`、`set_leader`、`add_peer` 和 `remove_peer` 必填。

#### 6.6.1 查看 raft 组的成员列表

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/list_peers
```

##### Response Status

```javascript
200
```

##### Response Body

返回对象的 key 是 raft 组名称。

```javascript
{
  "default": [
    "127.0.0.1:8281",
    "127.0.0.1:8282",
    "127.0.0.1:8283"
  ]
}
```

#### 6.6.2 查看 raft 组的 leader

##### Method & Url

```text
GET http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/get_leader
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default": "127.0.0.1:8281"
}
```

#### 6.6.3 转移 raft 组的 leader

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/transfer_leader?endpoint=127.0.0.1:8282
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default": "127.0.0.1:8282"
}
```

#### 6.6.4 指定 raft 组的 leader

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/set_leader?endpoint=127.0.0.1:8282
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "default": "127.0.0.1:8282"
}
```

#### 6.6.5 向 raft 组添加成员

该操作会创建一个异步任务，参见 [Task API](./task)。

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/add_peer?endpoint=127.0.0.1:8284
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "task_id": 1
}
```

#### 6.6.6 从 raft 组移除成员

该操作会创建一个异步任务，参见 [Task API](./task)。

##### Method & Url

```text
POST http://localhost:8080/graphspaces/DEFAULT/graphs/hugegraph/raft/remove_peer?endpoint=127.0.0.1:8284
```

##### Response Status

```javascript
200
```

##### Response Body

```javascript
{
  "task_id": 2
}
```
