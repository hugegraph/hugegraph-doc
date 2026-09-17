---
title: "下载 Apache HugeGraph"
linkTitle: "Download"
weight: 2
search_keywords: [HugeGraph 下载, 发布包, SHA512]
search_boost: 3
---

> 指南:
> 
> - 推荐使用最新版本的 HugeGraph 软件包, 运行时环境请选择 Java11
> - 验证下载版本, 请使用相应的哈希 (SHA512)、签名和 [项目签名验证 KEYS](https://downloads.apache.org/hugegraph/KEYS)
> - 检查哈希 (SHA512)、签名的说明在 [版本验证](/docs/contribution-guidelines/validate-release/) 页面, 也可参考 [ASF 验证说明](https://www.apache.org/dyn/closer.cgi#verify)
> - 注: HugeGraph 所有组件版本号已保持一致, `client/loader/hubble/common` 等 maven 仓库版本号同理, 依赖引用可参考 [maven 示例](https://github.com/apache/hugegraph-toolchain#maven-dependencies)
> - 兼容说明: HugeGraph 于 2026 年 1 月毕业后，下载路径已从 `/incubator/hugegraph` 迁移到 `/hugegraph`。历史版本的发布文件名可能仍包含 `-incubating-`。
> - 从源码构建请参考 [编译构建说明](/docs/quickstart/hugegraph/hugegraph-server/)

### 最新版本

{{< asf-downloads latest >}}

---

### 归档版本

> 注:
>
> 1. 请大家尽早迁移到最新 Release 版本上, 社区将不再维护 `1.0.0` 前的旧版本 (非 ASF 版本)
> 2. `1.3.0` 是最后一个兼容 Java8 的主版本, 请尽早使用/迁移运行时为 Java11 (低版本 Java 有潜在更多的 SEC 风险和性能影响)
> 3. 从版本 `1.5.0` 开始，需要 Java11 运行时环境

{{< asf-downloads archived >}}
