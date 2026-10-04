---
title: "共享基础模块：1.8.0 迁移指南"
linkTitle: "1.8.0 Java 与升级迁移"
description: "准备 1.8.0 共享基础模块整合所需的 Java 集成调整，以及 Server、PD、Store 同步升级。"
weight: 8
---

本文说明计划用于 1.8.0 的共享基础模块整合，不代表版本已发布或已满足发布条件。
实现与网站文档需要配套审查、协调合并；下游发布仍待完成。
源迁移说明和兼容性样本见[实现 PR](https://github.com/apache/hugegraph/pull/3270)。

## 模块职责

`hugegraph-core` 继续作为图引擎。`hugegraph-struct` 统一维护共享模型和编解码，`hugegraph-common` 维护通用工具。

```text
Server core ──> struct ──> common
Store core  ──> struct
PD service  ──> common
```

图中展示共享基础模块边界，不是完整依赖树。Server 的 HStore 适配器仍需要 PD、Store 客户端；Store 保留网络、PD 客户端和存储依赖。
PD、Store 不应依赖图引擎，struct 不应依赖 PD 客户端或 core。

| 能力 | 维护模块 |
|---|---|
| ID、schema 元数据、类型码、查询、基础元素、属性与字节编解码、索引构建和分词器 | struct |
| 事务、遍历、任务、schema 修改、后端适配器和索引更新编排 | core |
| 基于 PD 的 schema 访问、监听器和缓存生命周期（`SchemaGraph`/`SchemaDriver`） | Store |
| JWT 签名与校验、共享认证常量和 RPC 配置接口 | common |

Core、Store 实现 `HugeGraphSupplier`，向共享代码提供 schema、配置和时钟访问能力，避免 struct 引入图引擎依赖。
共享基础元素统一持有状态和邻接关系；`HugeVertex`/`HugeEdge` 保留引擎行为以及基于同一状态的包装对象身份。
Core 序列化器保留后端适配逻辑并委托共享编解码。共享索引与 OLAP 选择接收调用方提供的 schema 候选和结果接收器；
事务写入及后端能力检查仍由 core 负责。

## 重新编译 Java 集成和插件

使用配套的 1.8.0 artifacts 重新编译受影响的应用、插件和内部集成。类型迁移同时改变 import 和方法描述符，
只调整源码 import 不能让旧的已编译集成具备二进制兼容性。被移除的 core 类没有通用兼容包。
[插件示例](/cn/docs/guides/custom-plugin/)仍以 1.7.0 为例；接入迁移后的 API 时，需应用以下调整。

| 原入口 | 共享入口或必要调整 |
|---|---|
| `org.apache.hugegraph.backend.id.*` | `org.apache.hugegraph.id.*` |
| `org.apache.hugegraph.schema.*` 元数据 | `org.apache.hugegraph.struct.schema.*` |
| `org.apache.hugegraph.backend.query.*` | `org.apache.hugegraph.query.*` |
| `org.apache.hugegraph.backend.store.Shard` | `org.apache.hugegraph.backend.Shard` |
| `org.apache.hugegraph.backend.store.BackendEntry.BackendColumn` | `org.apache.hugegraph.backend.BackendColumn` |
| `org.apache.hugegraph.structure.HugeIndex` | `org.apache.hugegraph.structure.Index` |
| `HugeGraph.sameAs(HugeGraph)` | `HugeGraph.sameAs(HugeGraphSupplier)` |
| 后端序列化器中的共享字节与编码逻辑 | `org.apache.hugegraph.serializer.*` |
| Core `HugeException` | `org.apache.hugegraph.exception.HugeException` |
| `org.apache.hugegraph.SchemaGraph`/`SchemaDriver` | `org.apache.hugegraph.store.schema.*` |

表格描述职责迁移，不能直接批量替换整个包。Schema 修改 builder 和后端专用序列化器仍在 core。
客户端 REST DTO 保持独立，包括 Toolchain 的 `org.apache.hugegraph.structure.graph.Shard`。

外部 `HugeGraph` 实现需要将 `sameAs` override 参数改为 `org.apache.hugegraph.HugeGraphSupplier`，没有保留旧描述符的重载。
`GraphSerializer.writeIndex`/`readIndex` 改为接收或返回共享 `Index`，自定义序列化器和调用方需同步修改签名。
自定义 `HugeElement` 子类需通过 `element()` 提供共享 `BaseElement` 状态，通过 `wrapProperty` 适配属性；
不要恢复已移除的引擎状态字段或维护第二套邻接集合。

`org.apache.hugegraph.rpc.RpcServiceConfig4Client` 和 `RpcServiceConfig4Server` 统一由 common 维护。
全限定类名和签名不变，这项迁移无需调整 RPC import 或配置。
`org.apache.hugegraph.auth.TokenGenerator` 也位于 common，调用方提供签名密钥，并将 JWT 失败转换为各服务原有的响应。
Common 中的 JWT 依赖为 optional，直接使用 JWT 的模块需显式声明所需库。

自定义 Gremlin `classImports` 和脚本需将 `org.apache.hugegraph.backend.id.IdGenerator` 改为 `org.apache.hugegraph.id.IdGenerator`。
除编译 Java 源码外，还需启动发行包中的 Gremlin 服务，验证这些仅存在于配置中的引用。

### 下游异常和 classpath

| 原下游入口 | 必要调整 |
|---|---|
| Hubble `org.apache.hugegraph.exception.HugeException` | `org.apache.hugegraph.exception.HubbleException` |
| Java client `org.apache.hugegraph.exception.NotSupportException` | `org.apache.hugegraph.exception.ClientNotSupportException` |
| Hubble 自带的 `org.apache.hugegraph.license.MachineInfo` | 保留 import，使用 common 的实现 |

同步修改 import、构造调用和 catch。`HubbleException` 保留 `RuntimeException` 父类和字符串构造器；
`ClientNotSupportException` 保留 `ClientException` 父类及 message/cause、message/arguments 构造器。
Computer 的 `HgkvDirImpl` 是受影响的 client 异常调用方。Struct 中名称相近的异常具有不同契约，不能替代这些下游异常。
Loader 的 REST 边界和独立 client DTO 不需要整体改为 struct。

这些 Toolchain、Computer 调整仍需配套下游发布、构建和发行包 classpath 检查，才能确认迁移就绪。
只扫描源码不能证明发行 jar 中没有残留或传递依赖引入的同名类冲突。

## 同步升级服务

将 Server、PD、Store 一起升级到配套发行版本，本次迁移不支持混合版本滚动升级。
升级前按照已有[备份恢复流程](/cn/docs/guides/backup-restore/)备份图数据，并保留部署配置。
先在验证环境中检查历史数据读取和发行包服务启动，再用于生产。本次整合不提供自动数据重写操作。

既有类型码、ID 与属性字节、普通 Server 创建的索引 key、TTL 格式和配置默认值保持不变。
字符串 ID 统一按 Java UTF-16 顺序比较，包括从 UTF-8 字节加载的 ID；持久化 ID 字节不变。
类型迁移后，查询 JSON 中的历史 Java 类名及受支持的 Kryo 数据仍需要兼容解码。

Schema map 解码保留原 wire 字段和 ID 身份，并修复主键、edge sort-key 列表的顺序及重复项丢失问题。
匹配的冗余端点元数据和旧版仅含端点字段的 map 可以读取；冲突或格式错误的端点元数据会被拒绝。
基础元素分类也保留生产方上下文，storage 将 `~variables` 视为任务数据；engine 将 `~server`、`~role_data` 视为服务端数据，
将 `~variables` 视为普通顶点数据。两者都将 `~task`、`~taskresult` 视为任务数据。

### 检查旧索引行

旧 Store `IndexBuilder` 将长文本截短为 20 个字符，而 Server 查询使用完整值及其 hash。共享 builder 现在采用 Server 契约。
旧的截短索引行仍可解码，但不会自动匹配完整值查询。若部署曾通过 Store 重建索引，应评估受影响索引，必要时从图数据重新构建。
本次迁移不会自动重建索引，也不会补回缺失的历史索引项。

普通 schema 索引保留 Server 的 key/name-TTL 布局。Store 中带正过期时间的 SYSTEM-label 索引保留稳定 key 及旧版 13 字节 value 封装，
core 的 SYSTEM-label writer 保持不变。Label reader 仅识别这个有明确边界的旧封装；这不意味着给 key 增加 TTL 后缀、改变前缀删除行为，
或启用原本不支持的仅凭索引重建元素功能。

### HStore OLAP 物理 key

新 OLAP 行使用 `[property ID][vertex ID]` key，替代仅有 vertex ID 的 key，使同一顶点的多个 OLAP 属性可以共存。
旧行的 value 仍可读取。Reader 优先读取请求属性的组合 key，仅当旧 vertex-only 行的 value 包含匹配的 property ID 时才回退读取。
删除某个属性时，移除其组合行和匹配的旧行，保留其他属性。旧 writer 已经覆盖丢失的属性无法通过本次修复恢复。

恢复写入前，必须同步升级所有 Server、Store writer。旧 writer 可能更新旧行，而新 reader 仍优先读取已经存在的组合行；
混合版本 OLAP 写入不在支持的升级契约内。

### 保持 PD 元数据命名空间一致

Store 的 `pd.cluster` 默认值为 `hg`，在 Store `application.yml` 中配置：

```yaml
pd:
  cluster: hg
```

对应环境变量为 `PD_CLUSTER`。`usePD=true` 时与 Server 的 `cluster` 一致，`usePD=false` 时与图配置的 `pd.cluster` 一致。
命名空间用于 schema、图配置、缓存 watch 和 TTL cleaner 元数据。同一个 Store 进程不能在冲突命名空间之间共享 schema driver。
保留既有 backend `graphspace/store/table` 名称，例如 `DEFAULT/hugegraph/g`；REST 标识 `DEFAULT-hugegraph` 不是元数据 key。

## 采用迁移前的验证

验证历史 ID、schema、属性和索引样本、分页、TTL、OLAP 行为，以及受影响的 Java/SPI 集成。
检查 RocksDB、HStore 执行、认证、Store schema 与过滤行为，以及共享元素状态传播。
核查解析后的依赖与发行包，排除禁止的模块依赖和重复 HugeGraph 类，再启动实际发行包中的服务，不依赖 classpath 顺序规避冲突。
构建与依赖清单的前置条件见[贡献指南](/cn/docs/contribution-guidelines/contribute/)。
文档、源码编译或跳过测试的构建不能证明已满足发布条件；实现、网站和下游发布需要协调完成。
