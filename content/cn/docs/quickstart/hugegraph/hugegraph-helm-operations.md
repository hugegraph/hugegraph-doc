---
title: "HugeGraph Kubernetes 运维"
linkTitle: "Kubernetes 运维"
weight: 5
search_keywords: [HugeGraph Helm 运维, local PV, NetworkPolicy, PD, Store]
---

本文配合 [Helm 部署](./hugegraph-helm.md)使用。生命周期检查和恢复说明见
[运维参考](https://github.com/apache/hugegraph/blob/master/helm/hugegraph/docs/operations.md)，所有参数说明见 chart 的 `values.yaml`。
命令假设 release 和 namespace 都是 `hugegraph`，覆盖名称时请替换实际工作负载名。

## 1 存储和内网镜像 {#1-storage-and-private-images}

默认安装需要七个持久卷。动态存储需要正常的 provisioner，静态 local 存储需要预建目录和绑定节点的匹配 PV。
[完整例子](https://github.com/apache/hugegraph/tree/master/helm/hugegraph/examples)包含七个 local PV、`WaitForFirstConsumer`、镜像仓库和 GitOps Secret。
`WaitForFirstConsumer` 的 PVC 初期 Pending 可以是正常等待；持续 Pending 应检查 PVC/Pod 事件和 PV 匹配。
PVC 已绑定但目录不存在或权限不匹配时可能挂载失败，不能把故障 PVC 静默替换成临时目录。

```bash
kubectl -n hugegraph get pvc,pods
kubectl -n hugegraph describe pvc <claim-name>
kubectl -n hugegraph describe pod <pod-name>
kubectl get pv,storageclass
```

出现 `ImagePullBackOff` 时检查 Pod 事件、仓库连通性和拉取凭据。默认只需四个组件镜像，等待 Store/Helm test 复用已包含 curl 的组件镜像。
如显式覆盖 helper 镜像，该镜像也需要同步到内网仓库。

## 2 端口和健康检查 {#2-ports-and-health}

PD 端口为 REST 8620、gRPC 8686、Raft 8610；Store 为 REST 8520、gRPC 8500、Raft 8510；Server HTTP 为 8080；Hubble HTTP 为 8088。
客户端 Service 隐藏 Pod 地址，NodePort 是节点上另外分配的端口，与应用监听端口不同。
PD `/v1/ready` 需要 Raft leader，`/v1/health` 只说明监听器已启动，Store 等待多数 PD peer ready 后启动。
Server 等待存储的默认上限为 300 秒，可以用 `server.storageWaitTimeoutSeconds` 调整。
本地模板渲染不能验证集群连通性、卷挂载或 JVM 运行容量。

## 3 调度 {#3-scheduling}

默认 `preferred` 反亲和允许节点少于副本数时调度；`values-cluster.yaml` 对 PD/Store 设置 required 反亲和，因此需要至少三个可调度节点。
显式 affinity 优先于预设。local PV 节点亲和必须匹配工作负载位置约束，PV 容量声明不等于文件系统配额。
持久化 PD/Store 的 Raft 主机名和端口会记录为成员身份，不能作为普通配置随意变更。

## 4 分区副本 {#4-partition-sharding}

首次初始化时，Store 至少三个则默认每个分区三副本，否则一副本。
PD 会持久化分区设置，初始化后修改 chart 值不会覆盖已有元数据，应使用 PD 配置 API 并协调分区巡检。
显式 shard 数必须为奇数且不超过 Store 数，操作在线集群前参照 README 的完整过程。

## 5 NetworkPolicy {#5-networkpolicy}

easy 模式及普通集群预设默认关闭，strict 模式默认开启；显式 `networkPolicy.enabled` 在任何模式都优先。
集群网络插件必须支持策略执行，才有实际隔离效果。
生成策略允许组件间通信和 DNS，外部客户端、Ingress 控制器需要适当的 `networkPolicy.<component>.extraIngress`，
外部发现地址可能还需要 `extraEgress`。空列表合法但可能阻止外部访问；支持 Kubernetes 原生规则，包括允许全部的 `{}`，不要求额外来源确认。
按实际来源地址或 selector 配置，并考虑 NodePort SNAT 和控制器行为。

```yaml
networkPolicy:
  enabled: true
  server:
    extraIngress:
      - from:
          - ipBlock:
              cidr: 10.20.0.0/16
        ports:
          - protocol: TCP
            port: 8080
  hubble:
    extraIngress:
      - from:
          - ipBlock:
              cidr: 10.20.0.0/16
        ports:
          - protocol: TCP
            port: 8088
```

## 6 逐个升级 Store {#6-rolling-store-images-safely}

集群预设使用 `store.updateStrategy.type=OnDelete` 便于维护时控制逐个替换。
每次只删除一个 Store Pod，下一次删除前确认上一个 Pod Ready、Store 心跳新鲜，并从 PD leader 查询每个 shard group 都有完整成员及唯一 leader。
PD 的 `Up` 状态本身不证明 shard 恢复完成。PDB 限制主动驱逐，不限制 StatefulSet 控制器更新。
按 README 完整检查 shard 状态，发现缺副本或无 leader 时停止继续替换。

## 7 灾难恢复 {#7-disaster-recovery}

保留原卷、claim 身份和 PD 成员关系，不通过删除 RocksDB lock 文件恢复，也不把持久化成员配置替换为全新的节点。
Store 丢盘需要按 shard 替换/恢复流程处理，新建空 PVC 并不自动恢复数据。
local 磁盘不能在节点故障时自动迁移文件。备份应放在这些 PV 之外，并单独验证恢复；chart 不提供自动备份和自动恢复。
破坏性变更前先按 README 的恢复顺序检查。

## 8 扩缩容 {#8-scaling}

Server 副本可以常规变更，HPA 还需要 CPU requests。Store 扩容需要协调存储和 shard。
PD 扩缩容及 Store 缩容不能仅修改副本数，需要先更新持久化 Raft/shard 成员关系。
chart 对已初始化 StatefulSet 检查不支持的身份和成员变更，首次安装不执行升级专用查询。
按生命周期流程扩缩容，避免直接 `kubectl scale` 使 Hubble 的 Store metrics 配置过期。

## 9 集群外的 Hubble {#9-running-hubble-outside-the-cluster}

direct 模式只需要可达的 Server URL；PD discovery 还需要集群外可达的 PD gRPC，PD 注册的 Server 地址也必须可达。
必要时用 `server.advertiseUrl` 注册共享 Server 地址，这会影响所有 discovery 客户端，包括集群内 Hubble。
chart 内置 Hubble 已配置内部服务发现，不需要公开 PD 入口。
HTTP 可以直接使用，TLS 终止可选。Hubble 仍是单副本，当前登录依赖 Server 鉴权。

## 10 Gremlin 报 Could not rebind {#10-when-gremlin-fails-with-could-not-rebind}

PD 滚动更新期间，Server 可能 Ready、能响应 REST，但 Gremlin binding 失败。
执行 `helm test hugegraph -n hugegraph --logs --timeout 5m` 检查每个 Server Pod 的鉴权图查询；PD 稳定后替换失败 Pod 并再次验证。
只查询 `/versions` 不证明图绑定成功，还应检查 Hubble 新登录和图查询。

出现 `ERROR: missing required env 'HG_PD_AUTH_SECRET_KEY'` 时，检查 PD Pod 的 Secret 引用和对应 key，不要把 Secret 值输出到日志。
chart 正常情况下自动注入共享 PD REST 凭据，自定义容器或 manifest 必须向 PD 和客户端提供同一值。
GitOps 先创建外部 Secret 再调谐工作负载，普通 Helm 保留自动创建的 release Secret。
