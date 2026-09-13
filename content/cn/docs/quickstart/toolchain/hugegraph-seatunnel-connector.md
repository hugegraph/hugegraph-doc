---
title: "HugeGraph-SeaTunnel Connector Quick Start"
linkTitle: "使用 SeaTunnel Connector 同步数据"
weight: 5
---

SeaTunnel 负责连接数据源和数据目的地。HugeGraph Connector 提供两种能力。

- `HugeGraph Sink` 把文件、数据库、Kafka 等数据写入 HugeGraph。
- `HugeGraph Source` 从 HugeGraph 读出顶点和边，本文按固定 `dev` 提交介绍，不能用于 2.3.13 发行包。

![SeaTunnel 与 HugeGraph 数据流总览](/cn/docs/images/seatunnel/seatunnel-overview.png)

## 1 先看版本

本文把发布版和开发版分开写。配置放错版本，任务会在启动阶段失败。

| 使用内容 | SeaTunnel 版本 | 配置方式 |
| --- | --- | --- |
| JDBC / Kafka 写入 HugeGraph | 2.3.13 | Sink 使用 `schema_config` |
| HugeGraph 图迁移 | dev 提交 `f1a1a0a` | HugeGraph Source + Sink `mappings` |

2.3.13 没有 HugeGraph Source，也不支持 `mappings` 和 `schema_save_mode`。本文的开发版示例固定在提交 [`f1a1a0a`](https://github.com/apache/seatunnel/commit/f1a1a0abbe24bdac8cf23307995a78f778a3f467)，使用前需要自行构建该版本。后续开发版的参数可能变化，请对照所用版本的连接器文档。

## 2 选哪个工具

先看数据从哪里来，以及任务是否已经属于一条大数据管道。

| 你的任务 | 推荐工具 | 适合原因 |
| --- | --- | --- |
| 管理图、执行 Gremlin、备份恢复、图克隆 | [HugeGraph-Tools](/cn/docs/quickstart/toolchain/hugegraph-tools) | 只操作 HugeGraph，命令直接 |
| 把本地文件、HDFS、MySQL 等数据批量导入 HugeGraph | [HugeGraph-Loader](/cn/docs/quickstart/toolchain/hugegraph-loader) | 配置简单，导入流程短 |
| 数据要经过 Kafka、JDBC、Flink、Spark 或多个外部系统 | SeaTunnel | 可以复用已有数据管道 |
| 需要流式任务、checkpoint 或统一管理多个连接器 | SeaTunnel | 支持 Source、Transform 和 Sink 组合 |
| 稳定地把一张 HugeGraph 图复制到另一张图 | Tools 优先 | 发布版工具更直接；SeaTunnel Source 仍是 dev 预览 |

只维护一张图、没有现成大数据管道时，优先从 Loader 或 Tools 开始。SeaTunnel 需要额外准备连接器插件，并使用 HOCON 配置文件。

## 3 准备工作

### 3.1 HugeGraph

本文示例使用以下图模型。

| 图元素 | 配置 |
| --- | --- |
| VertexLabel | `person`，主键为 `name` |
| PropertyKey | `name` 为 Text，`age` 和 `since` 为 Int |
| EdgeLabel | `knows`，源和目标都是 `person`；属性为 `since` 和可空的 `name` |

2.3.13 的 Sink 会按 `schema_config` 读取已有的 VertexLabel、EdgeLabel 和 PropertyKey。运行写入任务前，请先在 Hubble、REST API 或 Gremlin 中创建 Schema。

`knows` 中可空的 `name` 用于兼容 2.3.13 的启动校验：第 4.2 节把两个端点字段映射到 `name`，校验器会要求它存在于边标签中；实际写边时会跳过端点字段，因此边上只写入 `since`。

### 3.2 SeaTunnel

请按 [SeaTunnel 本地部署文档](https://seatunnel.apache.org/docs/getting-started/locally/deployment/) 获取发行包。2.2.0-beta 之后，发行包默认不带连接器依赖，需要按任务安装 JDBC、Kafka 和 HugeGraph 插件；JDBC 还需要对应数据库的驱动。

如果 SeaTunnel 与 HugeGraph 不在同一台机器，`host` 要填写 SeaTunnel 运行环境可以访问的地址。容器内的 `127.0.0.1` 指向 SeaTunnel 容器自身；同一 Docker 网络中的服务则使用 HugeGraph 的服务名。

## 4 sql2graph

JDBC 方式适合把关系库中的表或 SQL 查询结果导入 HugeGraph。下面的例子把 `person` 表写成顶点，使用 `name` 生成 HugeGraph 主键。

![关系表写入 HugeGraph](/cn/docs/images/seatunnel/seatunnel-sql2graph.png)

### 4.1 关系库到顶点

假设 MySQL 中有一张表。

```sql
CREATE TABLE person (
  name VARCHAR(64) PRIMARY KEY,
  age INT NOT NULL
);
```

在 SeaTunnel 安装目录下创建 `config/sql2graph-person.conf`。

```hocon
env {
  job.mode = "BATCH"
}

source {
  Jdbc {
    url = "jdbc:mysql://mysql:3306/demo?useSSL=false&serverTimezone=UTC"
    driver = "com.mysql.cj.jdbc.Driver"
    username = "seatunnel"
    password = "change_me"
    query = "SELECT name, age FROM person ORDER BY name"
  }
}

sink {
  HugeGraph {
    host = "hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "default"
    schema_config = {
      type = "VERTEX"
      label = "person"
      idStrategy = "PRIMARY_KEY"
      idFields = ["name"]
    }
  }
}
```

执行任务。

```bash
./bin/seatunnel.sh --config ./config/sql2graph-person.conf -m local
```

执行后可以在 HugeGraph 中检查顶点。

```groovy
g.V().hasLabel('person').valueMap('name', 'age')
```

`Jdbc` 的 `url` 和 `driver` 必填。`username` 和 `password` 按数据库认证配置填写，匿名连接时可以省略；示例中的密码需要替换。MySQL 驱动需要放到 SeaTunnel 对应引擎的插件目录，具体位置见 [JDBC Source 文档](https://seatunnel.apache.org/docs/connectors/source/Jdbc/)。

### 4.2 关系库到边

如果关系表中的端点字段已经能直接对应 `person.name`，可以再运行一个边任务。假设表结构如下。

```sql
CREATE TABLE knows (
  source_name VARCHAR(64) NOT NULL,
  target_name VARCHAR(64) NOT NULL,
  since INT NOT NULL
);
```

<details>
<summary>展开查看边任务配置</summary>

```hocon
env {
  job.mode = "BATCH"
}

source {
  Jdbc {
    url = "jdbc:mysql://mysql:3306/demo?useSSL=false&serverTimezone=UTC"
    driver = "com.mysql.cj.jdbc.Driver"
    username = "seatunnel"
    password = "change_me"
    query = "SELECT source_name, target_name, since FROM knows ORDER BY source_name, target_name"
  }
}

sink {
  HugeGraph {
    host = "hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "default"
    schema_config = {
      type = "EDGE"
      label = "knows"
      sourceConfig = {
        label = "person"
        idFields = ["source_name"]
      }
      targetConfig = {
        label = "person"
        idFields = ["target_name"]
      }
      mapping = {
        fieldMapping = {
          source_name = "name"
          target_name = "name"
        }
      }
    }
  }
}
```

</details>

先写顶点，再写边。端点字段如果只是外键，不能直接拼出 HugeGraph 顶点 ID，需要先在 SQL 中完成关联查询，或者先把端点名称写入结果集。

CDC 配置请参考 SeaTunnel 的 [MySQL CDC 文档](https://seatunnel.apache.org/docs/connectors/source/MySQL-CDC/)。

## 5 kafka2graph

Kafka 适合持续把事件写入 HugeGraph。下面的消息使用 JSON 格式，每条消息对应一个 `person` 顶点。

![Kafka 事件写入 HugeGraph](/cn/docs/images/seatunnel/seatunnel-kafka2graph.png)

Kafka topic `user-events` 中的消息示例。

```json
{"name":"marko","age":29}
```

创建 `config/kafka2graph.conf`。

```hocon
env {
  job.mode = "STREAMING"
  checkpoint.interval = 10000
}

source {
  Kafka {
    bootstrap.servers = "kafka:9092"
    topic = "user-events"
    consumer.group = "hugegraph-import"
    start_mode = "earliest"
    format = "json"
    schema = {
      fields = {
        name = "string"
        age = "int"
      }
    }
  }
}

sink {
  HugeGraph {
    host = "hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "default"
    schema_config = {
      type = "VERTEX"
      label = "person"
      idStrategy = "PRIMARY_KEY"
      idFields = ["name"]
    }
  }
}
```

```bash
./bin/seatunnel.sh --config ./config/kafka2graph.conf -m local
```

`checkpoint.interval` 用于保存任务状态。HugeGraph Sink 使用 at-least-once 写入语义，使用 `PRIMARY_KEY` 时，重复写入同一个 `name` 会落到同一个顶点，不会因为重放生成新的随机顶点 ID。

Kafka 的参数和消息格式见 [Kafka Source 文档](https://seatunnel.apache.org/docs/connectors/source/Kafka/)。写边时，把 Sink 的 `schema_config.type` 改为 `EDGE`，再补充 `sourceConfig`、`targetConfig` 和边属性。

## 6 graph2graph

以下配置仅适用于提交 [`f1a1a0a`](https://github.com/apache/seatunnel/tree/f1a1a0abbe24bdac8cf23307995a78f778a3f467) 的开发版，需要从源码构建，不能直接放进 2.3.13 发行包。

![HugeGraph 图迁移](/cn/docs/images/seatunnel/seatunnel-graph2graph.png)

`mappings` 默认会创建缺失的 Schema，已有 Schema 仍须与映射兼容。请使用独立的目标图：本节的 `person` 使用 `CUSTOMIZE_STRING`，不要复用第 3 节已经创建为 `PRIMARY_KEY` 的同名标签。先迁移顶点，再迁移边，是为了确保边的端点已经写入。

一次迁移按两个任务执行。

1. 先迁移顶点。
2. 再迁移边。

### 6.1 迁移顶点

下面的 Source 读取源图的 `person` 顶点，并自动补充 `~id` 保留列。Sink 使用 `CUSTOMIZE_STRING` 把原 ID 保存为字符串，以便边任务继续引用相同的端点。不要在 `schema.fields` 中手动声明保留列。

<details>
<summary>展开查看顶点迁移配置</summary>

```hocon
env {
  job.mode = "BATCH"
}

source {
  HugeGraph {
    host = "source-hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "DEFAULT"
    label = "person"
    label_type = "VERTEX"
    schema = {
      fields = {
        name = "string"
        age = "int"
      }
    }
  }
}

sink {
  HugeGraph {
    host = "target-hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "DEFAULT"
    mappings = [
      {
        type = "VERTEX"
        label = "person"
        idStrategy = "CUSTOMIZE_STRING"
        idFields = ["~id"]
        properties = ["name", "age"]
      }
    ]
  }
}
```

</details>

### 6.2 迁移边

Source 会为边补充 `~source_id` 和 `~target_id` 保留列。顶点任务保留了原 ID，因此 Sink 可以直接用这两列定位目标图中的端点。配置中的 `check_vertex = true` 会检查端点是否存在，避免静默写入悬空边。

<details>
<summary>展开查看边迁移配置</summary>

```hocon
env {
  job.mode = "BATCH"
}

source {
  HugeGraph {
    host = "source-hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "DEFAULT"
    label = "knows"
    label_type = "EDGE"
    schema = {
      fields = {
        since = "int"
      }
    }
  }
}

sink {
  HugeGraph {
    host = "target-hugegraph"
    port = 8080
    graph_name = "hugegraph"
    graph_space = "DEFAULT"
    check_vertex = true
    mappings = [
      {
        type = "EDGE"
        label = "knows"
        sourceConfig = {
          label = "person"
          idFields = ["~source_id"]
        }
        targetConfig = {
          label = "person"
          idFields = ["~target_id"]
        }
        properties = ["since"]
      }
    ]
  }
}
```

</details>

不要把第 6.1 节改成按 `name` 重新生成 `PRIMARY_KEY` ID 后，仍直接复用原端点 ID。HugeGraph 的主键 ID 包含顶点标签的内部 ID，两张图的标签 ID 可能不同；比如源图是 `1:marko`，目标图重新生成的可能是 `2:marko`。本例通过字符串 ID 保留端点对应关系，也适用于将源图的数字 ID 转为字符串；这会改变目标图的 ID 策略，并非完整复制原 Schema。

dev Source 的其他要点：省略 `label` 时按 `label_type` 一次读取该类型全部 label，每个 label 输出一张表（此模式不能配置 `schema` 和 `filter`）；`parallelism > 1` 分片并行需要 RocksDB / HBase / Cassandra 等可扫描后端（`memory` 后端不支持），且不能与 `filter` 同用。

## 7 常用配置

下面列出常用字段及其适用版本。

| 字段 | 适用版本 | 作用 |
| --- | --- | --- |
| `host` / `port` | 两者 | Server 主机名或 IP 与端口，分别填写 |
| `graph_name` | 两者 | 图名称 |
| `graph_space` | 两者 | 按服务端实际图空间填写，区分大小写 |
| `schema_config` | 2.3.13 | Sink 的单个顶点或边映射 |
| `mappings` | 本文固定 dev | Sink 的多映射配置 |
| `batch_size` | 2.3.13 | 单批记录数，默认 500 |
| `batch_interval_ms` | 2.3.13 | 批次刷新间隔，默认 5000 毫秒；不要据此配置后续 dev 版本 |
| `check_vertex` | 本文固定 dev | 检查边端点是否存在，本例设为 `true` |

2.3.13 的 `schema_config.properties` 不参与字段筛选，本文已省略。需要限制写入字段时，使用 Sink 的 `selected_fields` / `ignored_fields`，并保留生成顶点 ID 或边端点所需的字段。注意：这些选项不会缩小启动时的 Schema 校验范围，因此应在 SQL 查询或 Source 中移除不需要的列。

2.3.13 不支持本文 dev 示例中的 `mappings`、HugeGraph Source 和 `schema_save_mode`。遇到配置校验失败时，先检查 SeaTunnel 发行包版本和配置 API 是否对应。

dev Sink 还提供 `data_save_mode`、`check_vertex`、失败回退（`batch_failure_fallback` / `max_insert_errors` / `failure_data_path`）、`max_retries` 指数退避、`ttl`、`frequency` / `sortKeys`、`updateStrategies`、`valueMapping`、`listFormat`、`unfold*` 等选项，完整列表见第 8 节的 dev 文档链接。

## 8 参考文档

- [SeaTunnel 本地部署](https://seatunnel.apache.org/docs/getting-started/locally/deployment/)
- [HugeGraph Sink 2.3.13](https://github.com/apache/seatunnel/blob/2.3.13/docs/zh/connectors/sink/HugeGraph.md)
- [HugeGraph Sink 2.3.13（官网版本文档）](https://seatunnel.apache.org/docs/2.3.13/connectors/sink/HugeGraph/)
- [HugeGraph Sink dev（本文核对版本）](https://github.com/apache/seatunnel/blob/f1a1a0abbe24bdac8cf23307995a78f778a3f467/docs/zh/connectors/sink/HugeGraph.md)
- [HugeGraph Source dev（本文核对版本）](https://github.com/apache/seatunnel/blob/f1a1a0abbe24bdac8cf23307995a78f778a3f467/docs/zh/connectors/source/HugeGraph.md)
- [JDBC Source](https://seatunnel.apache.org/docs/connectors/source/Jdbc/)
- [Kafka Source](https://seatunnel.apache.org/docs/connectors/source/Kafka/)
- [MySQL CDC Source](https://seatunnel.apache.org/docs/connectors/source/MySQL-CDC/)
- [HugeGraph-Loader](/cn/docs/quickstart/toolchain/hugegraph-loader)
- [HugeGraph-Tools](/cn/docs/quickstart/toolchain/hugegraph-tools)
- 上游追踪：功能请求 [apache/seatunnel#10001](https://github.com/apache/seatunnel/issues/10001) · Sink PR [apache/seatunnel#10002](https://github.com/apache/seatunnel/pull/10002) · Source / 多映射 PR [apache/seatunnel#11413](https://github.com/apache/seatunnel/pull/11413) · 文档 PR [apache/seatunnel#11329](https://github.com/apache/seatunnel/pull/11329)
- [Apache SeaTunnel GitHub](https://github.com/apache/seatunnel)
- [Apache HugeGraph GitHub](https://github.com/apache/hugegraph)
