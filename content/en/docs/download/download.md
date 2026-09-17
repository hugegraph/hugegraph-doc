---
title: "Download Apache HugeGraph"
linkTitle: "Download"
weight: 2
---


> Instructions:
> 
> - It is recommended to use the latest version of the HugeGraph software package. Please select Java11 for the runtime environment.
> - To verify downloads, use the corresponding hash (SHA512), signature, and [Project Signature Verification KEYS](https://downloads.apache.org/hugegraph/KEYS).
> - Instructions for checking hash (SHA512) and signatures are on the [Validate Release](/docs/contribution-guidelines/validate-release) page, and you can also refer to [ASF official instructions](https://www.apache.org/dyn/closer.cgi#verify).
> - Note: The version numbers of all components of HugeGraph have been kept consistent, and the version numbers of Maven repositories such as `client/loader/hubble/common` are the same. You can refer to these for dependency references [maven example](https://github.com/apache/hugegraph-toolchain#maven-dependencies).
> - Compatibility note: after HugeGraph graduated in January 2026, download paths moved from `/incubator/hugegraph` to `/hugegraph`. Historical release file names may still include `-incubating-`.
> - To build from source, refer to [build from source](/docs/quickstart/hugegraph/hugegraph-server).

### Latest Version

{{< asf-downloads latest >}}

---

### Archived Versions

> Note: `1.3.0` is the last major version compatible with Java8, please switch to or migrate to Java11 as soon as possible (lower versions of Java have potentially more SEC risks and performance impacts). Starting from version `1.5.0`, a Java11 runtime environment is required.

{{< asf-downloads archived >}}
