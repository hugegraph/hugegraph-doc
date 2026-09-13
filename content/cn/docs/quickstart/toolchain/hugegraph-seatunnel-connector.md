---
title: "使用 SeaTunnel 导入与迁移图数据"
linkTitle: "SeaTunnel 数据集成"
weight: 5
---

SeaTunnel 可以把数据库、Kafka 等数据源接入 HugeGraph，也可以在两张 HugeGraph 图之间迁移顶点和边。连接器分为两部分：**Source 负责读取，Sink 负责写入**，中间可以接 SeaTunnel 的数据转换组件。

> **版本要求：本文面向 SeaTunnel 3.0+（dev 分支）**，所有示例使用 `mappings`。SeaTunnel **2.3.13 只有 HugeGraph Sink**，使用旧的 `schema_config`，不能直接运行本文配置。

![SeaTunnel 数据导入与图迁移：3.0+ dev 支持 Source 和 Sink，2.3.13 仅支持 Sink](/cn/docs/images/seatunnel/seatunnel-data-flow-en.png)

## 1 选择工具和版本

| 你的任务 | 适合的工具 |
| --- | --- |
| 从文件、HDFS、关系库等批量导入数据，希望少部署组件 | [HugeGraph-Loader](/cn/docs/quickstart/toolchain/hugegraph-loader/) |
| 管理图、执行 Gremlin、备份恢复或图克隆 | [HugeGraph-Tools](/cn/docs/quickstart/toolchain/hugegraph-tools/) |
| 接入多种数据源、转换字段，或复用已有的批处理和流处理任务 | SeaTunnel |

新建 SeaTunnel 任务建议使用 3.0+ 的开发分支和 `mappings`。本文按 dev 提交 [`35b2716`](https://github.com/apache/seatunnel/commit/35b2716cde7d4c91a24fc618a8d9cae90e213db3) 核对；这里的 3.0+ 指开发版本，不能仅凭文档中的版本号认定某个发行包已包含这些功能。获取更新的 dev 后，请一并核对连接器配置。

| 能力 | 本文使用的 3.0+ dev | 2.3.13 |
| --- | --- | --- |
| 写入 HugeGraph | Sink，使用 `mappings` | Sink，使用 `schema_config` |
| 读取 HugeGraph 顶点和边 | 支持 Source | 不支持 |
| 自动创建缺失的图模型 | `mappings` 默认支持 | 需提前创建 |

如果暂时必须使用 2.3.13，请按 [2.3.13 Sink 文档](https://github.com/apache/seatunnel/blob/2.3.13/docs/zh/connectors/sink/HugeGraph.md) 配置，不要混用本文示例。

## 2 准备环境

### 2.1 获取 SeaTunnel dev

准备 JDK 11，并设置 `JAVA_HOME`。从开发分支获取源码，按上游[开发环境文档](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/developer/setup.md)构建发行包：

```bash
git clone --branch dev https://github.com/apache/seatunnel.git
cd seatunnel
# 复现本文配置时，固定到本次核对的提交
git checkout 35b2716cde7d4c91a24fc618a8d9cae90e213db3
./mvnw clean package -pl seatunnel-dist -am -Dmaven.test.skip=true
```

解压 `seatunnel-dist/target/` 中生成的二进制包，后续命令都在解压后的 SeaTunnel 安装目录执行。需要体验更新功能时，可以使用更新的 dev 提交；引擎与连接器插件应来自同一版本，避免混装 2.3.13 的 JAR。

本文使用 SeaTunnel 自带的 **Zeta 引擎和 local 模式**。确认安装目录的 `connectors/` 中包含 HugeGraph，以及所需的 JDBC 或 Kafka 连接器；如果自定义构建没有包含它们，需补齐同一次构建产出的插件。JDBC 示例还需要将 MySQL 驱动 JAR 放入 `lib/`，驱动类为 `com.mysql.cj.jdbc.Driver`。

### 2.2 准备 HugeGraph 和数据源

先启动 [HugeGraph Server](/cn/docs/quickstart/hugegraph/hugegraph-server/)，创建可用于测试的图。本文示例使用 `hugegraph` 图、`DEFAULT` 图空间，请按服务端实际配置修改；图空间名称区分大小写。启用了身份验证时，在 HugeGraph Source 和 Sink 中填写 `username`、`password`。

下面的图模型贯穿 JDBC 和 Kafka 示例。`mappings` 默认会创建缺失的 PropertyKey、VertexLabel 和 EdgeLabel；已有图模型必须与配置兼容。

| 图元素 | 名称与属性 |
| --- | --- |
| 属性 | `name` 为 Text，`age` 和 `since` 为 Int |
| 顶点 | `person`，主键为 `name`，属性为 `name`、`age` |
| 边 | `knows`，从 `person` 指向 `person`，属性为 `since` |

所有示例中的 `mysql`、`kafka`、`hugegraph` 都是占位主机名，需替换为 **SeaTunnel 运行环境可访问的地址**。容器中的 `127.0.0.1` 指向容器自身；同一 Docker 网络可使用服务名。`host` 只填主机名或 IP，端口单独填写。

## 3 从关系库导入（sql2graph）

用两个任务完成导入：先把 `person` 表写成顶点，再把 `knows` 表写成边。这样写边时，两个端点都已经存在。

### 3.1 导入顶点

在 MySQL 的 `demo` 数据库中准备示例数据，并让配置中的账号有读取权限：

```sql
CREATE TABLE person (
  name VARCHAR(64) PRIMARY KEY,
  age INT NOT NULL
);
INSERT INTO person VALUES ('marko', 29), ('vadas', 27);
```

保存为 `config/sql2graph-person.conf`，将数据库账号和密码替换为实际值：

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
    graph_space = "DEFAULT"
    batch_failure_fallback = false
    mappings = [
      {
        type = "VERTEX"
        label = "person"
        idStrategy = "PRIMARY_KEY"
        idFields = ["name"]
        properties = ["name", "age"]
      }
    ]
  }
}
```

```bash
./bin/seatunnel.sh --config ./config/sql2graph-person.conf -m local
```

在 Hubble 或 Gremlin 中检查结果，应能查到 `marko` 和 `vadas` 及其年龄：

```groovy
g.V().hasLabel('person').valueMap('name', 'age')
```

`idFields = ["name"]` 表示使用名字生成主键。重复导入同一个 `name` 会写到同一个顶点；`properties` 指定要写入的源字段。

### 3.2 导入边

准备关系表，其中两个端点字段对应前面导入的 `person.name`：

```sql
CREATE TABLE knows (
  source_name VARCHAR(64) NOT NULL,
  target_name VARCHAR(64) NOT NULL,
  since INT NOT NULL
);
INSERT INTO knows VALUES ('marko', 'vadas', 2010);
```

<details>
<summary>展开配置，保存为 config/sql2graph-knows.conf</summary>

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
    graph_space = "DEFAULT"
    batch_failure_fallback = false
    check_vertex = true
    mappings = [
      {
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
        fieldMapping = {
          source_name = "name"
          target_name = "name"
        }
        properties = ["since"]
      }
    ]
  }
}
```

</details>

确认顶点任务成功后，再执行边任务：

```bash
./bin/seatunnel.sh --config ./config/sql2graph-knows.conf -m local
```

下面的查询应返回 `marko` 到 `vadas` 的 `knows` 边，属性 `since` 为 `2010`：

```groovy
g.V().has('person', 'name', 'marko').outE('knows').where(inV().has('name', 'vadas')).valueMap()
```

`sourceConfig` 和 `targetConfig` 指定端点字段，`fieldMapping` 将它们对应到顶点主键 `name`，`properties = ["since"]` 只写边属性。示例启用 `check_vertex = true`，并关闭失败后逐条跳过的回退（`batch_failure_fallback = false`）；端点不存在或写入失败时，任务会报错。

如果关系表只有数字外键，而图的主键使用姓名，请先在 SQL 中关联出姓名，再交给 Sink。MySQL CDC 接入方式见 [MySQL CDC Source](https://seatunnel.apache.org/docs/connectors/source/MySQL-CDC/)。

## 4 从 Kafka 导入（kafka2graph）

Kafka 适合持续接收事件。先创建 `user-events` topic，再写入以下 JSON 消息，每条消息对应一个 `person` 顶点：

```json
{"name":"marko","age":29}
```

保存为 `config/kafka2graph.conf`：

```hocon
env {
  job.mode = "STREAMING"
  checkpoint.interval = 10000
  sink.flush.interval = 5000
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
    graph_space = "DEFAULT"
    batch_failure_fallback = false
    mappings = [
      {
        type = "VERTEX"
        label = "person"
        idStrategy = "PRIMARY_KEY"
        idFields = ["name"]
        properties = ["name", "age"]
      }
    ]
  }
}
```

```bash
./bin/seatunnel.sh --config ./config/kafka2graph.conf -m local
```

用第 3.1 节的 Gremlin 查询检查数据。流式任务会持续运行；`checkpoint.interval` 每 10 秒保存一次任务状态，`sink.flush.interval` 让 Zeta 每 5 秒触发一次刷新，避免少量消息一直等到批次填满。

HugeGraph Sink 是 **at-least-once（至少一次）** 写入，故障恢复可能重放记录。使用 `PRIMARY_KEY` 能让相同 `name` 落到同一个顶点，但不等于所有更新操作都具备 exactly-once 语义。定时刷新由 Zeta 提供，不适用于 Spark 或 Flink 引擎。

## 5 迁移 HugeGraph 图（graph2graph）

下面从源图迁移 `person` 顶点和 `knows` 边。请使用独立的目标图：本节采用 `CUSTOMIZE_STRING` 保留顶点 ID，不要复用前面已经创建为 `PRIMARY_KEY` 的 `person` 标签。

这两个任务只迁移指定标签和属性，不会完整复制源图的索引、TTL 等全部 Schema 配置。运行期间应暂停源图写入，避免两个任务读到不同时间的数据；完成后核对顶点、边数量及抽样属性。

### 5.1 先迁移顶点

Source 自动补充 `~id` 保留列，Sink 把原 ID 作为字符串保存。无需在 `schema.fields` 中声明 `~id`，手动声明保留列会被拒绝。

<details>
<summary>展开配置，保存为 config/graph2graph-person.conf</summary>

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
    batch_failure_fallback = false
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

```bash
./bin/seatunnel.sh --config ./config/graph2graph-person.conf -m local
```

### 5.2 再迁移边

确认顶点任务成功后，使用 Source 自动补充的 `~source_id` 和 `~target_id` 定位端点。因为上一任务保留了原 ID，这两列可以直接引用目标图中的顶点。

<details>
<summary>展开配置，保存为 config/graph2graph-knows.conf</summary>

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
    batch_failure_fallback = false
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

```bash
./bin/seatunnel.sh --config ./config/graph2graph-knows.conf -m local
```

本例打开端点检查，并让写入错误直接导致任务失败。默认的 `check_vertex = false` 不保证最终一致：缺少端点可能产生悬空边，因此不能用任务成功代替迁移结果检查。

> **为什么保留 ID？** HugeGraph 的 `PRIMARY_KEY` ID 包含顶点标签的内部 ID，两张图可能不同。例如源图顶点是 `1:marko`，目标图重新按主键生成的可能是 `2:marko`。如果重新生成顶点 ID 后仍复用源图的边端点，边就会连错。本例将原 ID 保存为字符串，因此会改变目标图的 ID 策略。

若要一次读取全部标签，省略 Source 的 `label` 后会按 `label_type` 为每个标签输出一张表；这时需用 `source_table` 将各 Sink 映射绑定到对应表，不能直接套用本节的单标签配置。其他限制见 [HugeGraph Source 文档](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/connectors/source/HugeGraph.md)。

## 6 常用配置与排错

下表适用于本文核对的 **3.0+ dev**：

| 配置 | 用途 |
| --- | --- |
| `host`、`port` | 分别指定 HugeGraph 主机和端口 |
| `graph_name`、`graph_space` | 选择已创建的图与图空间 |
| `mappings` | 定义输入字段如何生成顶点或边 |
| `properties` | 每个 mapping 内要写入的源字段列表 |
| `schema_save_mode` | `mappings` 默认自动创建缺失的 Schema；已有 Schema 仍需兼容 |
| `batch_size` | 单批记录数，默认 500 |
| `env.sink.flush.interval` | Zeta 定时刷新间隔，单位毫秒 |
| `check_vertex` | 写边时检查端点，本文的边任务设为 `true` |
| `batch_failure_fallback` | 默认 `false`，批量失败会使任务失败；设为 `true` 才启用逐条回退并允许跳过失败记录 |

遇到问题时可按下面检查：

- **不识别 `mappings` 或找不到 HugeGraph Source**：检查是否误用了 2.3.13 发行包或旧插件。
- **连接失败**：检查主机、端口、图空间、认证信息，以及 SeaTunnel 所在环境能否访问服务。
- **Schema 不兼容**：检查标签的 ID 策略、属性类型和边端点。自动创建不会把已有 `PRIMARY_KEY` 标签改成 `CUSTOMIZE_STRING`。
- **Kafka 少量数据未及时出现**：确认使用 Zeta，并在 `env` 中设置 `sink.flush.interval`。当前 dev 的 `batch_interval_ms` 仅为兼容保留，不能代替它。

## 7 参考文档

- [HugeGraph Sink（本文核对的 dev）](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/connectors/sink/HugeGraph.md)
- [HugeGraph Source（本文核对的 dev）](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/connectors/source/HugeGraph.md)
- [JDBC Source（本文核对的 dev）](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/connectors/source/Jdbc.md)
- [Kafka Source（本文核对的 dev）](https://github.com/apache/seatunnel/blob/35b2716cde7d4c91a24fc618a8d9cae90e213db3/docs/zh/connectors/source/Kafka.md)
- [SeaTunnel 本地部署](https://seatunnel.apache.org/docs/getting-started/locally/deployment/)
