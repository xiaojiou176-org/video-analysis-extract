# Repo Next Step Plan (Detailed Blueprint)

## 1. 需求与业务目的
### 1.1 需求原文抽象
1. 以“AI 处理后文本”为主阅读对象，不以原始 RSS/视频正文为主。
2. 支持订阅源分类管理，并可按分类做邮件/通知策略。
3. 支持后续新增来源（X/论坛/RSS/更多站点），且不破坏现有链路。
4. 手机、电脑、网页三端可用，优先保证 Web 端主路径闭环。

### 1.2 业务目的
1. 降低信息噪音: 直接阅读 AI 结果，减少原文消耗。
2. 提高决策效率: 分类路由后，重要类别优先通知。
3. 降低扩展成本: 用适配器架构替代平台硬编码。
4. 增强可运营性: 明确策略、观测、回放、审计能力。

## 2. 当前仓库能力与差距
### 2.1 已有能力
1. 订阅、采集、处理、产出（`outline`/`digest`）链路可运行。
2. Web 已有 dashboard/artifacts/subscriptions/settings 页面。
3. 通知能力存在（daily/test/failure/video_digest）。

### 2.2 差距清单
1. 缺“AI 文本时间线”一等 API 与页面。
2. 订阅缺少分类字段，无法做分类统计和分类发送。
3. 通知偏全局配置，缺少 category-aware 规则引擎。
4. 来源模型平台耦合较重，不利于快速扩源。

### 2.3 关键约束
1. 不能破坏现有生产链路。
2. 改动应可分阶段灰度与回滚。
3. 每阶段必须“代码 + 测试 + 文档”同步交付。

## 3. 成功标准（KPI + DoD）
### 3.1 用户侧 KPI
1. AI Feed 首屏加载成功率 >= 99%。
2. AI Feed P95 响应时间 <= 800ms（默认分页）。
3. 分类通知误投率 < 1%。
4. 新增标准 RSS 来源接入时间 <= 0.5 天。

### 3.2 工程侧 DoD
1. 新增/改造接口均有 schema 与测试覆盖。
2. 关键路径回归通过:
   - 创建订阅 -> 触发处理 -> 生成 AI 产物 -> Feed 可读 -> 分类通知。
3. 文档同步:
   - `README.md`
   - `docs/phase3-architecture.md`
   - `ENVIRONMENT.md`（如新增环境变量）

## 4. 分阶段实施计划

## Phase 1: AI Feed API（P0）
### 4.1 目标
提供统一的“AI 文本时间线”读取接口，成为前端和外部客户端的标准入口。

### 4.2 计划改动
1. 新增路由: `GET /api/v1/feed/digests`
2. 聚合来源: `jobs + artifacts`
3. 选择规则:
   - 优先 `digest`
   - 无 `digest` 则回退 `outline`
   - 两者都无则跳过
4. 支持过滤:
   - `category`（Phase 3 完成后启用）
   - `source`
   - `since`（ISO 时间）
5. 支持分页:
   - `limit`（默认 20，上限 100）
   - `cursor`（基于时间戳 + id 的 seek 分页）

### 4.3 API 契约草案
请求:
```http
GET /api/v1/feed/digests?limit=20&cursor=2026-02-23T10:00:00Z__123&source=youtube
```

响应:
```json
{
  "items": [
    {
      "feed_id": "2026-02-23T09:58:12Z__job_abc",
      "job_id": "job_abc",
      "video_url": "https://youtube.com/watch?v=xxx",
      "title": "Example Title",
      "source": "youtube",
      "source_name": "Channel A",
      "category": "tech",
      "published_at": "2026-02-23T09:58:12Z",
      "summary_md": "## TL;DR ...",
      "artifact_type": "digest"
    }
  ],
  "next_cursor": "2026-02-22T21:11:00Z__job_xyz",
  "has_more": true
}
```

错误语义:
1. 参数非法: `400`
2. 无数据: `200 + items=[]`
3. 服务异常: `500`（带 trace_id）

### 4.4 核心改动文件
1. `apps/api/app/routers/feed.py`（新增）
2. `apps/api/app/services/feed.py`（新增）
3. `apps/api/app/schemas/feed.py`（新增）
4. `apps/api/app/main.py`（注册路由）
5. `apps/api/tests/...`（新增测试）

### 4.5 技术细节
1. 使用 seek pagination，避免 offset 在大表退化。
2. 为 `jobs.created_at`、`artifacts.job_id`、`subscriptions.category` 建索引。
3. 输出字段固定化，禁止前端猜字段。

### 4.6 验收
1. 连续翻页不重复、不丢项。
2. 1000+ 数据量下响应稳定。
3. 空数据与异常数据可解释。

## Phase 2: Web Feed 页面（P0）
### 4.7 目标
在现有 Web 站点新增 AI Feed 页面，直接形成跨端可用入口。

### 4.8 计划改动
1. 新增页面: `apps/web/app/feed/page.tsx`
2. 新增 API client:
   - `apps/web/lib/api/client.ts` 增加 `getDigestFeed()`
3. UI 结构:
   - 顶部筛选（来源/分类）
   - 时间线卡片（标题、时间、来源、摘要）
   - 加载更多/空状态/错误状态

### 4.9 交互规范
1. 首屏默认展示最新 20 条。
2. 保持过滤器状态（querystring）。
3. 支持跳转到 artifact/job 详情页。

### 4.10 验收
1. 手机 Safari、桌面 Chrome/Edge 可用。
2. Markdown 渲染稳定，无样式错乱。
3. 异常提示可理解，可重试。

## Phase 3: 订阅分类模型（P1）
### 4.11 目标
让订阅具备分类能力，支持检索、统计、通知路由。

### 4.12 数据模型改动
新增字段（`subscriptions`）:
1. `category` `VARCHAR(32)` `NOT NULL DEFAULT 'misc'`
2. `tags` `JSONB` `NOT NULL DEFAULT '[]'`
3. `priority` `SMALLINT` `NOT NULL DEFAULT 50`（可选）

约束:
1. `category IN ('tech','creator','macro','ops','misc')`（首版）
2. `tags` 最大长度 20，单 tag 长度 <= 32

### 4.13 迁移步骤
1. 新增列并写默认值。
2. 历史数据回填:
   - `youtube` -> `creator`
   - `bilibili` -> `creator`
   - 其他 -> `misc`
3. 建索引:
   - `idx_subscriptions_category`
   - `idx_subscriptions_category_priority`
4. 发布后执行数据校验 SQL。

### 4.14 API 改动
1. `POST /api/v1/subscriptions` 支持 `category/tags/priority`
2. `GET /api/v1/subscriptions` 支持 `category` 过滤
3. 新增批量接口:
   - `POST /api/v1/subscriptions/batch-update-category`

### 4.15 验收
1. 新旧数据都能正常读写。
2. 分类过滤查询稳定。
3. 批量改分类可回放（记录操作日志）。

## Phase 4: 通知分类路由（P1）
### 4.16 目标
从全局通知升级为按分类策略通知。

### 4.17 规则模型
新增配置结构（示例）:
```json
{
  "default_rule": {"enabled": true, "cadence": "daily", "channel": "email"},
  "category_rules": {
    "tech": {"cadence": "daily", "hour": 8, "channel": "email"},
    "macro": {"cadence": "weekly", "weekday": 1, "hour": 7, "channel": "email"},
    "ops": {"cadence": "instant", "channel": "email", "min_priority": 80}
  }
}
```

### 4.18 路由优先级
1. 分类规则命中
2. 全局默认规则兜底
3. 关闭规则则不发送

### 4.19 幂等与重试
1. 发送任务生成 `dispatch_key` 防止重复投递。
2. 可重试错误（网络/超时）走指数退避。
3. 不可重试错误（模板错误/参数错误）直接告警。

### 4.20 验收
1. 同一批内容按分类进入不同发送节奏。
2. 日志可追踪“命中哪条规则、为何发送/不发送”。

## Phase 5: 来源适配器（P2）
### 4.21 目标
将来源接入从平台硬编码迁移到可扩展适配器层。

### 4.22 适配器接口
```python
class SourceAdapter(Protocol):
    def normalize(self, raw_input: dict) -> NormalizedSource: ...
    def fetch(self, source: NormalizedSource) -> list[RawEntry]: ...
    def parse(self, entry: RawEntry) -> ParsedEntry: ...
```

### 4.23 首批适配器
1. `rss_generic`（优先）
2. `youtube_channel`（兼容）
3. `bilibili_uid`（兼容）

### 4.24 兼容策略
1. 原有 `platform/source_type` 暂保留读取能力。
2. 新建字段 `adapter_type/source_url`，逐步迁移写路径。
3. 双写一段时间后切换读路径。

### 4.25 验收
1. 新增 RSS 来源不改核心 pipeline。
2. 旧来源零中断。

## 5. 任务拆分与工作包
### 5.1 工作包 WBS
1. WBS-1 Feed API（后端）
2. WBS-2 Feed 页面（前端）
3. WBS-3 订阅分类模型（后端 + migration）
4. WBS-4 通知路由引擎（后端）
5. WBS-5 适配器抽象（后端）
6. WBS-6 文档与运维手册更新

### 5.2 工时估算（开发日）
1. WBS-1: 1.5 天
2. WBS-2: 1.0 天
3. WBS-3: 1.5 天
4. WBS-4: 2.0 天
5. WBS-5: 2.5 天
6. WBS-6: 0.5 天
总计: 9.0 天（不含外部依赖阻塞）

## 6. 测试计划
### 6.1 后端测试矩阵
1. 单元测试:
   - feed 聚合逻辑优先级（digest > outline）
   - 分类规则命中顺序
   - 适配器 normalize/parse 错误处理
2. 集成测试:
   - feed 分页与过滤正确性
   - 订阅分类 CRUD + 批量更新
   - 通知幂等与重试
3. 回归测试:
   - 现有 artifacts/jobs API 不回归
   - 现有通知配置可继续运行

### 6.2 前端测试矩阵
1. 组件测试:
   - feed 列表渲染
   - 空状态/错误状态
2. 端到端（最小）:
   - 打开 `/feed` -> 拉取成功 -> 点击详情

### 6.3 验收脚本建议
1. `python scripts/check_env_contract.py --strict`
2. `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q`
3. `npm --prefix apps/web run lint`

## 7. 发布、灰度与回滚
### 7.1 发布策略
1. Phase 1/2 先行发布（用户可见价值最大）。
2. Phase 3/4 功能开关控制（默认只启用内部账号）。
3. Phase 5 适配器以白名单方式灰度。

### 7.2 回滚策略
1. API 回滚: 新路由可直接下线，不影响旧接口。
2. DB 回滚: 采用“向前兼容迁移”，避免直接删列。
3. 通知回滚: 配置层一键切回全局规则。

### 7.3 观测指标
1. feed 请求量、错误率、P95。
2. 分类规则命中率、投递成功率。
3. 每类来源采集成功率与失败码分布。

## 8. 风险与缓解
1. 风险: 分类模型设计过早固化。
   - 缓解: 先枚举 + 支持 tags，后续可迁移到可配置字典表。
2. 风险: 适配器扩展导致复杂度上升。
   - 缓解: 强制统一接口与错误码，禁止 adapter 侵入业务层。
3. 风险: 通知误发。
   - 缓解: dry-run 模式 + 审计日志 + 幂等键。
4. 风险: 前端页面体验不稳定。
   - 缓解: 首版保守实现，后续再做视觉增强。

## 9. 里程碑与里程碑交付件
1. M1（第 2 天）:
   - 交付: Feed API + 测试 + 文档
2. M2（第 3 天）:
   - 交付: `/feed` 页面 + 前端测试
3. M3（第 5 天）:
   - 交付: 订阅分类 + migration + 管理接口
4. M4（第 7 天）:
   - 交付: 分类通知路由 + 可观测
5. M5（第 9 天）:
   - 交付: 适配器抽象 + 首批 RSS adapter

## 10. 下一步执行指令（拍板）
1. 先开工 Phase 1 与 Phase 2，直接产出可见价值。
2. Phase 1/2 合并后立即切到 Phase 3（分类模型）。
3. 再做 Phase 4（分类通知），最后推进 Phase 5（来源扩展）。
4. 每个阶段完成后更新本文档的“状态栏”并补齐证据（测试结果与文件列表）。
