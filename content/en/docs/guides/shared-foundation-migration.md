---
title: "Shared foundations: 1.8.0 migration"
linkTitle: "1.8.0 Java and upgrade migration"
description: "Prepare Java integrations and coordinated Server, PD and Store upgrades for the 1.8.0 shared-foundation consolidation."
weight: 8
---

This guide describes the shared-foundation consolidation planned for 1.8.0. It does not announce a release or establish release readiness.
The implementation and website documentation must be reviewed and merged together; downstream publication remains pending.
See the [implementation PR](https://github.com/apache/hugegraph/pull/3270) for the source migration document and compatibility fixtures.

## Module ownership

`hugegraph-core` remains the graph engine. `hugegraph-struct` owns the shared model and codecs, and `hugegraph-common` owns common utilities.

```text
Server core ──> struct ──> common
Store core  ──> struct
PD service  ──> common
```

These arrows show the shared-foundation boundary, not the complete dependency tree. The Server HStore adapter still needs PD and Store clients;
Store retains its network, PD client and storage dependencies. PD and Store must not depend on the graph engine,
and struct must not depend on PD clients or core.

| Capability | Owner |
|---|---|
| IDs, schema metadata, type codes, queries, base elements, property/byte codecs, index construction and analyzers | struct |
| Transactions, traversal, tasks, schema mutation, backend adapters and index update orchestration | core |
| PD-backed schema access, listeners and cache lifecycle (`SchemaGraph`/`SchemaDriver`) | Store |
| JWT signing/verification, shared auth constants and RPC configuration interfaces | common |

Core and Store implement `HugeGraphSupplier` to supply schema, configuration and clock access without introducing an engine dependency in struct.
Shared base elements own state and adjacency. `HugeVertex`/`HugeEdge` retain engine behavior and wrapper identity over that state;
core serializers delegate shared encoding while retaining backend adapters. Shared index and OLAP selection accept caller-supplied schema candidates
and result sinks; core keeps transaction writes and backend capability checks.

## Recompile Java integrations and plugins

Recompile affected applications, plugins and internal integrations against matching 1.8.0 artifacts.
Relocated types change method descriptors as well as imports. Updating source imports does not make previously compiled integrations binary-compatible,
and there is no general compatibility package for removed core classes.
The [plugin example](/docs/guides/custom-plugin/) remains a 1.7.0 example; apply the changes below when targeting the migrated API.

| Previous entry | Shared entry or required change |
|---|---|
| `org.apache.hugegraph.backend.id.*` | `org.apache.hugegraph.id.*` |
| `org.apache.hugegraph.schema.*` metadata | `org.apache.hugegraph.struct.schema.*` |
| `org.apache.hugegraph.backend.query.*` | `org.apache.hugegraph.query.*` |
| `org.apache.hugegraph.backend.store.Shard` | `org.apache.hugegraph.backend.Shard` |
| `org.apache.hugegraph.backend.store.BackendEntry.BackendColumn` | `org.apache.hugegraph.backend.BackendColumn` |
| `org.apache.hugegraph.structure.HugeIndex` | `org.apache.hugegraph.structure.Index` |
| `HugeGraph.sameAs(HugeGraph)` | `HugeGraph.sameAs(HugeGraphSupplier)` |
| Shared bytes/encoding in backend serializers | `org.apache.hugegraph.serializer.*` |
| Core `HugeException` | `org.apache.hugegraph.exception.HugeException` |
| `org.apache.hugegraph.SchemaGraph`/`SchemaDriver` | `org.apache.hugegraph.store.schema.*` |

This is an ownership map, not a blanket package replacement. Schema mutation builders and backend-specific serializers remain in core.
Client REST DTOs, including Toolchain's `org.apache.hugegraph.structure.graph.Shard`, remain separate.

External `HugeGraph` implementations must change their `sameAs` override to accept `org.apache.hugegraph.HugeGraphSupplier`; the old descriptor has no overload.
`GraphSerializer.writeIndex`/`readIndex` now accept/return shared `Index`, so custom serializer implementations and callers must update their signatures.
Custom `HugeElement` subclasses must expose shared `BaseElement` state through `element()` and adapt properties through `wrapProperty`;
do not recreate removed engine state fields or a second adjacency collection.

`org.apache.hugegraph.rpc.RpcServiceConfig4Client` and `RpcServiceConfig4Server` have one owner in common.
Their fully qualified names and signatures are unchanged, so this move requires no RPC import or configuration change.
`org.apache.hugegraph.auth.TokenGenerator` also resides in common. Callers supply the signing secret and translate JWT failures into local service responses.
JWT dependencies are optional in common; direct JWT consumers must declare their required libraries explicitly.

Replace `org.apache.hugegraph.backend.id.IdGenerator` with `org.apache.hugegraph.id.IdGenerator` in custom Gremlin `classImports` and scripts.
Check these configuration-only references by starting the packaged Gremlin service as well as compiling Java sources.

### Downstream exceptions and classpaths

| Previous downstream entry | Required change |
|---|---|
| Hubble `org.apache.hugegraph.exception.HugeException` | `org.apache.hugegraph.exception.HubbleException` |
| Java client `org.apache.hugegraph.exception.NotSupportException` | `org.apache.hugegraph.exception.ClientNotSupportException` |
| Hubble's copy of `org.apache.hugegraph.license.MachineInfo` | Retain the import and use the common implementation |

Update imports, constructor calls and catch clauses. `HubbleException` retains its `RuntimeException` parent and string constructor;
`ClientNotSupportException` retains its `ClientException` parent and message/cause and message/arguments constructors.
Computer's `HgkvDirImpl` is an affected client-exception caller. Struct's similarly named exceptions have different contracts and are not substitutes.
Loader's REST boundary and independent client DTOs need no wholesale conversion to struct.

These Toolchain and Computer adjustments require matching downstream publication, builds and packaged-classpath checks
before migration readiness can be claimed.
A source scan alone cannot establish that shipped jars have no stale or transitive class collisions.

## Coordinated service upgrade

Upgrade Server, PD and Store together to matching release artifacts. Mixed-version rolling upgrades are not supported for this migration.
Back up graph data using the existing [backup and restore procedure](/docs/guides/backup-restore/), and preserve deployment configuration before upgrading.
Verify historical data reads and packaged service startup in a validation environment before production use.
The consolidation introduces no automatic data rewrite.

Existing type codes, ID/property bytes, ordinary Server-created index keys, TTL formats and configuration defaults are preserved.
String IDs now consistently use Java UTF-16 ordering, including IDs loaded from UTF-8 bytes; persisted ID bytes are unchanged.
Historical Java names in query JSON and supported Kryo values still need legacy decoding after relocation.

Schema map decoding keeps existing wire fields and ID identity. It now preserves primary-key and edge sort-key list order and duplicates,
accepts matching redundant endpoint metadata and legacy endpoint-only maps, and rejects conflicting or malformed endpoints.
Base-element classification also retains the producer context: storage treats `~variables` as task data;
engine elements treat `~server` and `~role_data` as server data and `~variables` as ordinary vertex data. Both retain `~task` and `~taskresult` as task data.

### Assess legacy index rows

The previous Store-side `IndexBuilder` shortened long text values to 20 characters, while Server queries used the full value and its hash.
The shared builder now uses the Server contract. Old shortened rows remain decodable but do not automatically match full-value queries.
If an installation used Store-side index rebuilding, assess affected indexes and rebuild them from graph data where necessary.
The migration does not automatically rebuild indexes or recover missing historical entries.

Ordinary schema indexes retain the Server key/name-TTL layout. Store SYSTEM-label indexes with positive expiry retain stable keys and their legacy
13-byte value envelope; the core SYSTEM-label writer remains unchanged. The label reader recognizes that bounded envelope.
This does not add TTL suffixes to those keys, change prefix deletion, or enable previously unsupported index-only element reconstruction.

### HStore OLAP physical keys

New OLAP rows use `[property ID][vertex ID]` keys rather than a vertex ID alone, allowing several OLAP properties on one vertex to coexist.
Existing row values remain readable. Readers first try the requested property's compound key, then use a legacy vertex-only row only if its value contains
the matching property ID. Deleting one property removes its compound row and a matching legacy row while preserving other properties.
Properties already overwritten by the old vertex-only writer cannot be recovered by this repair.

Upgrade all Server and Store writers together before resuming writes. An old writer can update a legacy row while a new reader still prefers an existing
compound row; mixed-version OLAP writes are outside the supported upgrade contract.

### Keep the PD metadata namespace consistent

Store's `pd.cluster` setting defaults to `hg`. In Store `application.yml`, configure:

```yaml
pd:
  cluster: hg
```

The environment equivalent is `PD_CLUSTER`. Match Server's `cluster` when `usePD=true`, or the graph's `pd.cluster` when `usePD=false`.
This namespace covers schema, graph configuration, cache watches and TTL-cleaner metadata.
One Store process cannot share a schema driver across conflicting namespaces.
Keep existing backend `graphspace/store/table` names, such as `DEFAULT/hugegraph/g`; the REST identity `DEFAULT-hugegraph` is not a metadata key.

## Before adopting the migration

Validate historical ID/schema/property/index samples, pagination, TTL and OLAP behavior, and affected Java/SPI integrations.
Check RocksDB and HStore execution, authentication, Store schema/filter behavior and shared element state propagation.
Inspect resolved dependencies and packaged distributions for forbidden module dependencies and duplicate HugeGraph classes,
then start the actual packaged services without classpath-ordering workarounds.
Use the [contribution guidance](/docs/contribution-guidelines/contribute/) for build and dependency-inventory prerequisites.
Documentation, source compilation and skipped-test builds do not establish release readiness; coordinate implementation, website and downstream publication.
