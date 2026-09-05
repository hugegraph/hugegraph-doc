# HugeGraph OINK 网站改进规划

## 1. 目标与优先级

聚焦 master 上的 OINK 网站；Docusaurus 预览站只参考 Ask AI、Community 等产品设计，不读取或迁移其实现与构建方式。交互以普通鼠标、触屏和快捷键用户为主，无障碍检查仅作为防回归护栏。

| 优先级 | 评分 | 已确认事项 |
|---|---:|---|
| P0 | 10.0 | 修复侧栏分层、隐藏焦点、移动抽屉和导航交互 |
| P0 | 9.8 | 增加 1.3/1.0，重构五版本 CI 与预发发布 |
| P0 | 9.6 | OINK 原生搜索内融合可选 Kapa Ask AI |
| P0 | 9.5 | Community 增加 ASF PMC/Committers 头像墙 |
| P1 | 9.0 | 统一 OINK 主题 token，补强 summary 搜索元数据 |
| P1 | 8.6 | LLMSFULL、Backlinks、图片缩放、复制链接、社交预览图和内容组件试点 |
| P2 | 8.0 | ASF-aware 数据驱动下载页，作为第二阶段 |
| Deferred | ≤6.5 | 全文索引及其他低收益或高外部依赖能力 |

## 2. 第一阶段实现

### 2.1 OINK Shell、导航与侧栏

- 将 `#532fc9` 迁移为 `ui.theme_color`，导航、侧栏、焦点、选中态、搜索和 Ask AI 共用 OINK 明暗色 token，删除可替代的硬编码颜色。
- 顶部保留 `Documentation / Download / Blog / Community`：
  - Documentation 下拉改为“开始、组件、开发、运维、参考”五组图标入口。
  - 仅保留右侧 branch 图标作为版本选择器，消除重复版本菜单。
  - 采用 [OINK 官方站](https://oink.pgsty.com/)原生手感：hover/focus 展开、移出延迟关闭、点击标题进入文档首页、↓ 进入菜单、Esc 关闭。
- 侧栏收起后完全离开布局和交互树，删除左缘 hover 浮层；只能点击显式按钮恢复。
- 默认只展开当前页面祖先；用户手动展开的节点可持久化。
- 折叠状态全站共享；节点状态使用 `oink.sidebar.v1.<version>.<locale>` 隔离，只保存稳定节点 ID，active path 始终优先，失效 ID 自动清理；localStorage 不可用时退化为当前祖先展开。
- 移动抽屉关闭时隔离内部交互、恢复触发按钮、解除滚动锁；同时修复汉堡按钮低对比度。

### 2.2 本地搜索与 Ask AI

本地搜索继续采用 `summary`，不会因 AI 服务替换、延迟或失效。

- 为 latest 中英文 12 组核心入口补充克制的 `search_keywords/search_boost/search_exclude`：
  - Introduction、Server、HStore、PD、Computer、Loader、Hubble、Clients、REST、Config、Authentication、Download。
  - 用固定中英文查询集验证目标页进入前列，禁止全站机械堆词。
- 明确区分“无匹配结果”和“索引加载失败”；失败态提供本地重试。
- 有非空普通查询时，在本地结果末尾追加 Ask AI 行；空查询、命令模式和 choice 模式不显示。
- 保留全站浮动 launcher；移动端使用紧凑尺寸和 safe-area，不遮挡正文。
- launcher 打开空白 AI 会话；搜索结果中的 Ask AI 自动提交当前查询。
- 只向 Kapa 发送裁剪后的查询字符串，不发送当前 URL、页面内容、版本信息或本地结果。
- 历史版本入口和面板明确标注“回答基于 latest 文档”；第三方服务说明只在 AI 面板中显示。
- Kapa 脚本仅在用户点击后加载；5 秒未完成脚本加载或 render 即进入非阻塞错误态，保留入口和本地结果并允许重试。迟到响应不得自动弹窗。
- launcher 与搜索行共用 `idle/loading/ready/error` 状态机，防止双击、重复脚本和并发打开。
- Kapa 不接管 `Cmd/Ctrl+K`；关闭 AI 后焦点返回真实触发入口。

配置契约：

```yaml
params:
  ai_search:
    enabled: true
    provider: kapa
    website_id: 0b277570-4740-451e-96fa-1e4ac1ac5e88
    source_groups:
      en: "<reviewed-latest-en-source-group-id>"
      cn: "<reviewed-latest-cn-source-group-id>"
```

- `enabled=false` 时不输出 launcher、适配脚本或任何 Kapa 请求。
- 开启时 provider、website ID 和两种语言 source group 缺一即构建失败；这些均为公开浏览器标识，不使用 secret。
- bundle URL、5 秒超时和隐私策略固定在适配器中，不允许配置任意脚本地址。
- 固定关闭 Kapa launcher、搜索模式、Command-K、consent、匿名 Cookie 和 fingerprint；保留现有 hCaptcha 防滥用。
- Kapa 面板按 OINK token 完整覆盖字体、颜色、边框、圆角和浅/深色，禁止使用旧版红粉 UI。实现参考 [Kapa Functions](https://docs.kapa.ai/integrations/website-widget/javascript-api/functions)、[Theming](https://docs.kapa.ai/integrations/website-widget/configuration/theming) 和 [User Tracking](https://docs.kapa.ai/integrations/website-widget/features/user-tracking)。
- 不复制 OINK 的完整 command palette 脚本；先利用现有 manual-init 与 model/registry 注入实现薄适配，并向 OINK 上游提交通用 `registerExtension({ placement: "search-tail", rows, activate })` API。上游发布后删除本站包装层。
- CSP 仅允许 staging 实测确认的 Kapa、hCaptcha 和必要代理精确主机，不使用通配域名；生成 HTML 仍不得静态嵌入第三方 active resource。

### 2.3 Kapa 知识库

- latest EN/CN 文档根启用 OINK `LLMSFULL`，分别生成 `/docs/llms-full.txt` 和 `/cn/docs/llms-full.txt`。
- Kapa 只摄取这两个 LLMSFULL 文件，不同时爬 HTML，避免重复引用。
- 英文页面只启用 EN source group，中文页面只启用 CN source group。
- Kapa 后台必须完成：
  - 排除历史和旧 Docusaurus global sources。
  - 配置生产、OINK staging 两个允许域名。
  - 完成首次抓取并核对来源时间。
- 初始 corpus、source group 与 CSP 未通过 staging 验证前保持 AI 关闭；通过后同一配置在 staging 和 production 启用，不做长期分阶段开关。

### 2.4 五版本与路由

版本菜单固定为：

```text
latest / 1.7 / 1.5 / 1.3 / 1.0
```

- 跳过 1.2；中英文使用相同短标签和顺序。
- 历史内容分别取自 `release-1.7.0`、`release-1.5.0`、`release-1.3.0`、`release-1.0.0`。
- 配置只展示分支名；每次运行开始时仍解析一次 SHA 并在该次任务中固定，避免矩阵任务读取不同提交。
- 以 `versions.json` 为版本、顺序、ref、发布路径的单一真源，其他菜单和校验数据由它派生。
- 增加版本化 route-map：
  - 1.3/1.0 在构建 overlay 中迁移到当前五组信息架构。
  - 旧扁平 URL 生成静态 alias/redirect，canonical 指向迁移后的同版本路径。
  - 版本切换按逻辑页面 ID 查找等价页；成功时保留 query/hash，目标不存在时跳至目标版本文档根并丢弃无效 query/hash，同时显示一次说明。
  - 1.0 中文确实缺失的页面不补译、不展示英文伪中文页；语言切换回到该版本中文根。
  - 仅在真实等价双语页面间输出 hreflang。
- 1.7/1.5/1.3/1.0 输出 `noindex,follow` 并从 sitemap 排除；保留自 canonical、直达 URL、归档提示和切换 latest 的入口。

### 2.5 Community PMC/Committers

结合 [Issue #468](https://github.com/apache/hugegraph-doc/issues/468)，在“参与社区”之后、成熟度 CTA 之前加入 Project members：

- 角色权威来源：
  - [committee-info.json](https://whimsy.apache.org/public/committee-info.json) 交叉校验 Chair/PMC。
  - [public_ldap_projects.json](https://whimsy.apache.org/public/public_ldap_projects.json) 提供 owners/members。
  - [public_ldap_people.json](https://whimsy.apache.org/public/public_ldap_people.json) 提供公开姓名。
- `PMC = owners`；`Committers = members - owners`，禁止重复。Chair 第一，其余按 ASF 公开姓名 Unicode casefold 排序。
- 中英文共用 `data/community/roster.json`；人工审核的 ASF ID→GitHub 映射放在 `data/community/github-map.json`，记录 numeric GitHub user ID，禁止按姓名、邮箱或提交记录猜账号。
- 页面仅显示：
  - 已映射：本地头像和 `@GitHub ID`，整卡链接 GitHub。
  - 未映射：姓名首字母和 ASF ID，链接 ASF phonebook。
  - ASF 姓名只用于排序和非视觉链接名称。
- 复用 OINK Contributors token/class，但通过 site-local partial 直接读取嵌套数据；不依赖原生 shortcode 对嵌套路径的支持。
- 固定 5/3/2 列：桌面 ≥1200px、平板 768–1199px、手机 <768px。
- 头像使用同源 128×128 WebP、剥离元数据、懒加载；initials 先渲染，图片失败时无需 JavaScript 即可回退。
- HTML、Print 和 Markdown 输出必须包含相同角色集合、顺序及 profile 链接。

提供：

```bash
python3 scripts/community_roster.py refresh
python3 scripts/community_roster.py validate --warn-after-days 90
```

- `refresh` 仅由维护者本地运行，生成普通 PR；不增加定时任务、机器人提交或直推。
- 候选头像使用内容寻址文件名：先安装并验证新头像，最后原子替换 roster，再清理孤立旧头像；任何失败保持 last-good bundle。
- `validate` 完全离线，检查 schema、集合、唯一 Chair、排序、映射闭集、账号/user ID 唯一性、头像 MIME/尺寸/hash 和渲染产物。
- 90 天依据成功抓取的 `retrieved_at` 判断，只输出 Python/Actions warning，不进入 Hugo warning；未来日期或结构错误阻断构建。

### 2.6 其他已采纳 OINK 能力

- latest 文档启用 Backlinks，默认显示 5 条，超过后“查看全部”。
- Docs 与 Blog 在五个版本中启用按需图片缩放。
- Blog 页尾只提供“复制链接”，不增加社交平台跳转。
- 使用现有 HugeGraph 品牌资产生成一张经人工审阅的 1200×630 默认社交预览图，为 Docs、Community 和 Blog 提供 fallback。
- 仅在以下三组 latest 双语页面试点 OINK 原生内容组件：
  - Server Quickstart：步骤、命令 filename/wrap/collapse。
  - Config Guide：长配置文件名、折叠与复制。
  - REST Vertex：字段锚点、宽表和请求/响应代码块。
- 不机械改写其他页面或任何历史版本。

## 3. CI/CD 与交付并行

### 3.1 事件模型

| 事件 | 构建 | 发布 |
|---|---|---|
| PR | 五版本、production origin | 不发布 |
| master push | 五版本、production origin | 完整发布 `asf-site` |
| dispatch `staging-next/latest` | 指定 ASF 分支的 latest | 发布 `asf-staging-oink`；历史菜单指向 production |
| dispatch `staging-next/full` | 候选 latest + 四个历史版本 | 完整发布 `asf-staging-oink` |
| dispatch `production-history-refresh` | master shell + 五版本 | 完整发布 `asf-site` |

- dispatch 仅能从 master 工作流启动；候选只接受 ASF 仓库普通分支，拒绝 fork、tag、裸 SHA 和输出分支。
- staging 与 production 分别要求固定确认词；origin、profile 和目标分支全部由枚举映射，不接受自由文本。
- 默认权限 `contents: read`；只有发布 job 使用 `contents: write`。发布 job 不 checkout 或执行候选分支代码，只下载本次 run/attempt 的明确 artifact。
- 不新增 GitHub Environment；依靠最小权限、可信 ref、确认词、目标硬编码、新鲜度检查和 ASF `whoami`。
- 保留 required check 名称 `deploy`；它只检查 prepare/build/aggregate/E2E 成功，不持有写权限。
- 移除 `version × site` 笛卡尔矩阵：
  - PR/master/full staging 最多 5 个并行版本构建。
  - 默认 latest staging 只运行 1 个构建。
- 不缓存历史最终 artifact；保留现有 Go/Hugo 编译缓存。
- resolved manifest/可发布 aggregate/E2E 报告保留 7 天，中间版本与 PR aggregate 保留 1 天。
- 超时：prepare 10 分钟、单版本 build 20、aggregate 15、Chromium E2E 20、visual 15、deploy gate 5、publish 10。

### 3.2 PR 分组

采用两条并行第一阶段加一个第二阶段：

1. **PR-A：OINK 核心平台**
   - Shell、导航、侧栏、主题 token、搜索错误态、Ask AI、LLMSFULL、Backlinks、图片缩放、复制链接、社交卡片。
   - 五版本、route-map、CI/CD、Node/Playwright/Chromium 与发布安全。
   - 因共享 `hugo.yaml`、布局、样式、CSP、测试基座和 workflow，这些强依赖内容合入同一 PR；内部可按 UI/AI、versioning/CI、E2E 三个文件所有权 lane 并行开发。

2. **PR-B：Community 与内容体验**
   - PMC/Committers 数据链路、独立 scoped 样式和三种输出。
   - 12 组搜索元数据、3 组双语内容组件试点。
   - 不修改 PR-A 所有的共享配置、shell 样式或 workflow，可与 PR-A 完全并行。

3. **PR-C：ASF 下载页第二阶段**
   - 在第一阶段稳定后，把中英文下载事实收敛到单一数据源。
   - 复用 OINK 下载/checksum UI，明确支持 ASF mirror、正式 source artifact、ASC 和 SHA512；不得把 GitHub 自动 source archive 表述为 ASF 正式发行物。

### 3.3 Issue 与上游归档

- [Issue #467](https://github.com/apache/hugegraph-doc/issues/467)：
  - 先追加三套 Ask AI 视觉方案对比、选择结论和“旧红粉 UI 禁止复用”说明。
  - staging 验证后再追加最终浅/深色、桌面/移动截图和验证结论。
- PR-B 使用 `Closes #468`。
- 另建全文搜索 Issue，记录 summary 现状、content 模式约 233–243 KiB gzip/语言/版本的估算及性能预算；本轮不实现。
- 向 OINK 上游分别提交通用 palette extension 和侧栏交互修复；上游工作不阻塞本站交付。

## 4. 测试与验收

- 保留现有 Python/链接/产物验证；补齐五版本顺序、1.2 缺席、route-map、aliases、noindex/sitemap、canonical/hreflang、1.0 语言缺页和 staging 跨 origin 菜单合同。
- Node 24 只用于 `tests/e2e/`；提交锁文件，并在 `.gitignore` 中仅放行该目录的 lockfile。Hugo 生产构建不执行 npm。
- Chromium 阻断测试：
  - latest 中英文完整覆盖搜索、导航、侧栏、版本切换、Community 和 AI mock。
  - 四个历史版本中英文覆盖菜单、关键路由、归档、noindex、AI latest 提示及键盘冒烟。
  - AI 覆盖禁用零请求、结果尾 CTA、点击前零第三方请求、精确 query/locale、500、超时、CSP、迟到响应、双击和重试。
  - Community 覆盖 1440/900/390/320px 的 5/3/2 列、明暗色、长账号、缺 GitHub mapping、空 Committers、HTML/Print/Markdown 一致性。
- axe WCAG 2.2 AA、隐藏侧栏零可聚焦元素、焦点恢复及颜色对比只作为回归护栏。
- 视觉回归永久 advisory，不进入 `deploy` gate；固定导航、搜索、侧栏、Community 的桌面/移动和浅/深色状态，并要求 PR 提供 before → after 截图。
- 部署后真实 Kapa smoke 只验证 bundle、CSP、render 和面板可打开，不提交问题；失败仅告警，不回滚或阻止原生站点发布。
- 发布验收要求：
  - production 与 staging 原生搜索在 Kapa 故障时完整可用。
  - 所有外部请求只在用户点击 Ask AI 后出现。
  - 五版本 URL、旧链接和语言切换无 404。
  - Community 页面无访客侧 GitHub/Whimsy 请求。
  - PR-A 与 PR-B 合并后运行一次完整五版本集成构建再发布。

## 5. 明确延期与默认假设

- 延期：全文本地索引、反馈、OpenAPI/Redoc、Giscus、analytics、Authors/Series/taxonomy、Custom commands、Translation notice、Reading time、PlantUML、Draw.io、Markmap、Asciinema、KaTeX、ECharts、PDF/EPUB、PWA、导航自动隐藏、Blog 视图切换、GitHub stars 及其他展示型 Landing。
- Ask AI 是可选增强，任何外部故障均不得改变本地搜索结果、CI 核心结论或网站可发布性。
- 历史版本只保留原始事实，不补译、不修饰为当前行为。
- Community 只展示当前 ASF 官方角色，不按仓库贡献次数、组织成员或公司归属推断身份。
- 所有新界面沿用当前 OINK/HugeGraph 视觉系统，不复刻 Docusaurus 旧 UI。
