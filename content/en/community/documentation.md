---
title: "Documentation site preview"
linkTitle: "Documentation site preview"
description: "Preview and check the Hugo documentation site with the pinned OINK module."
type: docs
weight: 20
outputs: [HTML, print, markdown]
---

## Check the local toolchain

Use the tool versions pinned in the repository's `go.mod` and CI configuration. From the documentation repository root, check the tools and theme:

```bash {filename="check-docs-theme.sh" wrap=true}
hugo version
go version
hugo mod graph
```

The recording below captures these three read-only commands on 2026-10-11 with Hugo 0.165 Extended, Go 1.27.1 and OINK 1.2.0.
Playback runs at 0.1 times the recorded speed to make the short output easier to read. The cast is served locally with the site.

{{< asciinema file="/casts/oink-upgrade-check.cast" title="Recorded documentation toolchain and theme check" speed="0.1" rows="24" >}}

[Download the original recording](/casts/oink-upgrade-check.cast).

## Preview and validate

1. Start the local preview from the repository root:

   ```bash
   scripts/hugo.sh server
   ```

2. Open [the local site](http://localhost:1313/) and inspect both language versions of the changed page.
3. Run the warning-strict build:

   ```bash
   scripts/hugo.sh build
   ```
{.steps}

The wrapper generates version-navigation settings before starting Hugo. A different preview port can be passed with `-p`,
for example `scripts/hugo.sh server -p 8080`.

For the complete contribution checks and theme upgrade workflow, see the repository's
[contribution guide](https://github.com/apache/hugegraph-doc/blob/master/contribution.md) and
[OINK upgrade guide](https://github.com/apache/hugegraph-doc/blob/master/scripts/oink-upgrade.md).
