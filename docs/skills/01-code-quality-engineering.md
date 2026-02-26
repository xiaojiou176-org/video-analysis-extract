---
name: 1. [💎代码]质量工程
description: 深度代码审查、安全重构协议、测试缺口分析。用于Code Review、安全评估、代码重构和测试覆盖率优化。
---

# 代码质量工程

> 合并自：深度代码审查 + 安全重构协议 + 测试缺口分析

## 概述

代码质量工程是一个综合性 Skill，覆盖代码审查、安全重构、测试缺口分析三大核心能力。适用于 Code Review、重构、测试补全等场景。

## 触发条件

- 关键词：Code Review、代码审查、Review、审查代码、上线前检查、合并前检查、代码体检。
- license: MIT
- metadata:
- version: "2.0"
- author: "Codex OS"
- category: "审查类"
- modes: ["pr", "release-audit"]
- 重构
- 重构代码
- 优化代码结构
- 清理技术债
- 提取模块
- 拆分模块
- 整理代码
- 消除坏味道
- refactor
- restructure
- technical debt
- code cleanup
- extract module
- 代码改动后评估测试覆盖
- 发现 Bug 后补充测试
- 提高测试质量
- 准备发布前检查
- PR/MR 变更驱动的缺口扫描
- inputs:
- required:
- changed_files # git diff --name-only 或指定文件列表
- optional:
- coverage_report # lcov/cobertura/jacoco 覆盖率报告路径
- test_framework # jest/pytest/go test/vitest
- critical_paths # 业务关键路径配置（支付/认证/权限）
- outputs:
- uncovered_code_list # 未覆盖代码清单
- priority_rank_with_score # 带评分的优先级排序
- test_case_suggestions # 测试用例建议
- boundary_condition_template # 边界条件测试模板
- anti_placebo_plan # 反安慰剂执行计划
- priority_scoring:
- business_impact: 0-5 # 业务影响：支付/登录/权限
- change_related: 0-4 # 变更相关：本次 diff 涉及
- coverage_signal: 0-3 # 覆盖信号：分支覆盖率
- failure_cost: 0-3 # 失败代价：资金/安全/可用性
- historical_risk: 0-2 # 历史风险：同类 bug 复发
- complexity_signal: 0-2 # 复杂度信号：多分支/状态机/并发

## 继承基座

- 代码规范基座
- 测试规范基座

---

## Part 1: 深度代码审查

> **定位**: 可执行、可推广、可降级的代码审查 SOP。PR 级别 30 分钟可完成，Release 级别 2 小时深度体检。

---

### 0. 执行模式选择 (Mode Selection)

| 模式 | 范围 | 耗时 | 适用场景 |
|------|------|------|----------|
| **PR 模式** | 改动文件 + 关联入口 + 关键依赖 | 15-30 min | 日常 PR Review |
| **Release-Audit 模式** | 全仓体检 | 1-2 h | 上线前/重构后/季度维护 |

**默认**: 未明确指定时使用 PR 模式。用户说"全面审查/深度审查/上线前检查"时切换 Release-Audit 模式。

---

### 1. 机器预检 (Automated Pre-Flight) 🤖

> **铁律**: 凡机器能测的，不许人看。Review 只关注逻辑和架构。

**执行**: 运行 `scripts/preflight.sh`（自动探测语言/框架）

```bash
# 在仓库根目录执行
bash "$(dirname "$0")/scripts/preflight.sh" --output .runtime-cache/review/preflight.json
```

**预检项** (任一失败 → BLOCKER，不进入人工审查):

- [ ] Lint 通过
- [ ] TypeCheck 通过
- [ ] 单元测试通过
- [ ] 依赖安全审计通过

**红线**: 如果 Reviewer 还在评论"缩进不对/少个分号"，说明预检流程失败了。

---

### 2. 范围算法 (Scope Selector)

#### PR 模式 - 增量审查

```yaml
scope:
  must_read:
    - changed_files  # diff 全文
  expand_if_touches:
    - "auth|token|secret|password"  # 认证相关
    - "db|model|schema|migration"   # 数据层
    - "cache|redis|memcache"        # 缓存层
    - "config|env|settings"         # 配置
    - "router|middleware|handler"   # 入口层
    - "payment|order|transaction"   # 资金相关
  expand_callchain_depth: 1  # 上下游各读 1 层
  expand_hotspots: true      # 最近 N 次改动频繁的文件
```

#### Release-Audit 模式 - 全仓体检

```yaml
scope:
  must_read: ["full_repo"]
  dimensions: "all_18+"
```

---

### 3. 审查维度 (Review Dimensions)

> 完整清单见 `references/checklist.md`。此处为精简版执行指引。

#### 3.1 基础治理 (维度 1-5)

| # | 维度 | PR必检 | Release必检 | 快速检查命令 |
|---|------|:------:|:-----------:|-------------|
| 1 | 日志统一目录 | ⚪ | ✅ | `find . -name "*.log" -not -path "./.runtime-cache/*"` |
| 2 | 日志轮转清理 | ⚪ | ✅ | 检查是否有 maxFiles/rotate 配置 |
| 3 | 架构分层 | ✅ | ✅ | 检查依赖方向、循环依赖 |
| 4 | 缓存统一目录 | ⚪ | ✅ | `find . -type d -name "cache" -not -path "./.runtime-cache/*"` |
| 5 | 缓存清理策略 | ⚪ | ✅ | 检查 TTL/过期机制 |

#### 3.2 日志质量 (维度 6-7.5)

| # | 维度 | PR必检 | Release必检 | 检查要点 |
|---|------|:------:|:-----------:|----------|
| 6 | 日志颗粒度 | ✅ | ✅ | Request ID / Trace ID / 耗时 / 堆栈 |
| 7 | 日志可读性 | ✅ | ✅ | 结构化字段齐全、阶段标记清晰 |
| **7.5** | **🔥 日志审计** | ✅ | ✅ | **必须运行代码看日志！** |

**日志审计执行**:

```bash
bash scripts/log_audit.sh --dir .runtime-cache/logs --output .runtime-cache/review/log_audit.json
```

#### 3.3 代码质量 (维度 8-9)

| # | 维度 | PR必检 | Release必检 | 阈值 |
|---|------|:------:|:-----------:|------|
| 8 | 代码维护性 | ✅ | ✅ | 文件 ≤500行警告，≤1000行必拆；函数 ≤50行 |
| 9 | UI 友好性 | ✅(涉及UI时) | ✅ | 状态反馈、键盘可达、错误提示 |

#### 3.4 测试严谨性 (维度 10-13)

| # | 维度 | PR必检 | Release必检 | 关键检查 |
|---|------|:------:|:-----------:|----------|
| 10 | 测试覆盖度 | ✅ | ✅ | 覆盖率阈值（默认 80%，可配置） |
| 11 | 反安慰剂测试 | ✅ | ✅ | 反事实检查：改坏逻辑后测试是否失败？ |
| 12 | 测试效率 | ⚪ | ✅ | 并发 vs 串行、耗时分析 |
| 13 | 测试维护性 | ⚪ | ✅ | Mock 最小化、命名清晰 |

#### 3.5 配置与文档 (维度 14-15)

| # | 维度 | PR必检 | Release必检 |
|---|------|:------:|:-----------:|
| 14 | 配置集中管理 | ✅ | ✅ |
| 15 | 文档充分性 | ✅(涉及API时) | ✅ |

#### 3.6 安全与性能 (维度 16-18) ⚠️ 高风险

| # | 维度 | PR必检 | Release必检 | 关键检查 |
|---|------|:------:|:-----------:|----------|
| 16 | **安全与隐私** | ✅ | ✅ | 硬编码凭证、SQL注入、XSS、日志脱敏、越权 |
| 17 | **类型安全** | ✅ | ✅ | 禁止 any、强制 Schema、null 处理 |
| 18 | **性能与资源** | ✅ | ✅ | N+1、内存泄漏、索引、竞态条件 |

**敏感信息扫描**:

```bash
bash scripts/secrets_scan.sh --dir . --output .runtime-cache/review/secrets_scan.json
```

#### 3.7 扩展维度 (Release-Audit 专属)

| # | 维度 | 检查要点 |
|---|------|----------|
| 19 | **发布与回滚** | Feature Flag、灰度、Migration 向后兼容、回滚步骤 |
| 20 | **供应链安全** | lockfile 一致、SCA 扫描、typosquatting、最小权限 token |
| 21 | **可观测性** | Metrics/Tracing、业务指标、错误率/延迟 |
| 22 | **数据一致性** | 事务边界、幂等、重复消息处理 |
| 23 | **API 兼容性** | 版本策略、Breaking Change 检测、契约测试 |
| 24 | **可访问性 (a11y)** | WCAG 2.1 AA、键盘导航、屏幕阅读器 |

---

### 4. 证据标准 (Evidence Policy)

> **铁律**: 没有证据的 Finding 就是幻觉，必须删除。

#### 4.1 可接受的证据类型（按优先级）

| 等级 | 证据类型 | 要求 |
|------|----------|------|
| A | **CI 产物** | 测试输出 + 日志 artifact + coverage 报告 |
| B | **本地复现** | 运行命令 + 环境 + 关键日志片段（带时间戳/traceId） |
| C | **无法运行** | 必须标记为 `UNVERIFIED`，升级至少 MAJOR |

#### 4.2 Finding 必备四要素

每个 BLOCKER/MAJOR/MINOR 必须包含：

1. **Evidence（证据）**: 文件路径 + 行号 + 3-10 行代码片段
2. **Impact（影响）**: 用户可见？安全？数据完整性？性能？
3. **Proposed Fix（修复建议）**: 具体修复步骤或代码片段
4. **Verification（验证方式）**: 如何确认修复成功

**不可证实即降级规则**:

- 无法定位到具体位置 → 降级为 `QUESTION`（提问）
- 无法验证 → 标记 `UNVERIFIED` + 升级严重级别

---

### 5. 严重级别框架 (Severity Framework)

| 级别 | 定义 | 阻断规则 | Risk Score |
|------|------|----------|------------|
| **BLOCKER** | 合并前必须修复 | 阻断合并 + 阻断发布 | ≥9 |
| **MAJOR** | 应当修复，不修风险高 | 可合并但阻断发布（或明确接受风险） | 6-8 |
| **MINOR** | 改进项，低风险 | 不阻断，记录为后续任务 | 3-5 |
| **NIT** | 风格偏好 | 仅供参考 | 1-2 |
| **QUESTION** | 需要更多信息 | 等待回答后重新评级 | - |

#### Risk Score 计算（可选增强）

```
Risk Score = Impact(0-3) + Likelihood(0-3) + Blast Radius(0-3) + Detectability(0-3)
```

---

### 6. 审查输出结构

> 模板见 `references/report_template.md`

```markdown
## 1. 合并建议 (Merge Recommendation)
[Approve / Approve with changes / Request changes]

## 2. 合并前必修清单 (Must-Fix Before Merge)
- [ ] [BLOCKER] 问题描述 → `文件路径:行号`
- [ ] [MAJOR] 问题描述 → `文件路径:行号`

## 3. 维度打分 (Dimension Scores)
| 维度 | 状态 | 备注 |
|------|------|------|
| 日志审计 | ✅/⚠️/❌ | ... |

## 4. 问题详情 (Findings)
### [BLOCKER] 问题标题
- **Evidence**: `path/file.ts:45` + 代码片段
- **Impact**: ...
- **Proposed Fix**: ...
- **Verification**: ...

## 5. 未验证项 (What I Didn't Verify)
- [ ] 原因 + 风险说明

## 6. 止血方案 (Kill-switch / Rollback Plan)
- 回滚命令: `git revert ...`
- 降级开关: `FEATURE_X_ENABLED=false`

## 7. 测试影响 (Test Impact)
- 需新增测试: ...
- 需调整测试: ...

## 8. 证据附件 (Evidence Artifacts)
- preflight.json: `.runtime-cache/review/preflight.json`
- log_audit.json: `.runtime-cache/review/log_audit.json`
```

---

### 7. 审查者自检 (Meta-Verification)

在输出报告前必须自问：

1. **覆盖率自检**: "我是否读取了所有修改文件的完整上下文（至少前后 50 行）？"
2. **幻觉自检**: "每个 Finding 是否有具体行号/代码片段作为证据？"
3. **标准自检**: "如果是人类 Tech Lead 看到这段代码，会不会皱眉？"
4. **遗漏自检**: "是否检查了安全(16)、类型(17)、性能(18)这三个隐形风险层？"

---

### 8. 降级策略

| 场景 | 降级方案 |
|------|----------|
| 本地无法运行代码 | 要求 CI 产出日志 artifact + grep 审计结果 |
| 无 CI 日志 | 标记为 `UNVERIFIED`，升级严重级别 |
| 无测试框架 | 标记 BLOCKER: "缺少测试基础设施" |
| 时间不足 | 只做 PR 模式（必检项），记录"未审查维度" |

---

### 9. 配置覆盖 (Policy Override)

支持通过 `.codex/review-policy.yml` 覆盖默认策略：

```yaml
# .codex/review-policy.yml (可选)
mode: pr  # pr | release-audit
coverage_threshold: 0.8
logs_dir: ".runtime-cache/logs"
cache_dir: ".runtime-cache/cache"
logging_style:
  required: ["structured_fields", "request_id", "error_stack"]
  optional: ["zh_messages", "emoji_markers"]
skip_dimensions: []  # 跳过的维度编号
```

---

### Quick Reference

#### PR 模式必检清单（30分钟）

```
□ 预检通过 (lint/type/test/audit)
□ 架构分层 (维度 3)
□ 日志颗粒度 + 可读性 (维度 6-7)
□ 日志审计 (维度 7.5) ← 必须运行看日志！
□ 代码维护性 (维度 8)
□ 测试覆盖度 + 反安慰剂 (维度 10-11)
□ 安全脱敏 (维度 16)
□ 类型安全 (维度 17)
□ 性能问题 (维度 18)
```

#### Release-Audit 必检清单（2小时）

```
□ PR 模式全部 9 项
□ 日志统一目录 + 轮转 (维度 1-2)
□ 缓存治理 (维度 4-5)
□ UI 友好性 (维度 9)
□ 测试效率 + 维护性 (维度 12-13)
□ 配置集中 + 文档 (维度 14-15)
□ 发布回滚 (维度 19)
□ 供应链安全 (维度 20)
□ 可观测性 (维度 21)
□ 数据一致性 (维度 22)
□ API 兼容性 (维度 23)
□ 可访问性 (维度 24)
```

---

## Part 2: 安全重构协议

### 核心原则

1. **行为不变**: 重构改变结构，不改变行为
2. **小步前进**: 每次改动可独立回滚
3. **测试护航**: 没有测试的代码不重构
4. **持续可用**: 任何时候都能发布

---

### 行为等价边界（必须遵守）

#### ✅ 必须保持的行为

- 外部 API 响应（字段/状态码/错误格式）
- 异常类型与错误码
- 持久化数据结构与语义
- 事件消息格式
- 权限/校验逻辑结果
- 可观测性关键指标（error rate、latency p99）

#### ⚠️ 允许变化的细节

- 内部函数/变量命名
- 文件/目录组织结构
- 非关键日志文案
- 内部数据结构（不影响输出）

#### ❌ 默认禁止变化

- 公共接口契约（签名、语义）
- 数据库 Schema
- 时序语义（先后顺序依赖）
- 幂等性保证

> 🔑 判定原则：任何"调用者可观察到的输出"都算行为。

---

### 重构前准备

#### Step 1: 确保测试存在

```bash
# 运行现有测试
npm test -- --coverage

# 如果覆盖率不足
# 先补充测试，再重构
```

**最低要求**:

- 核心功能有测试覆盖
- 关键边界条件有测试
- 能捕获行为变更

#### 测试补齐策略（按场景选择）

##### 策略 A: Characterization Tests（录现状）

**适用**: 老代码、逻辑复杂、不敢改
**做法**:

- 用 Golden Master 固定当前输出
- 覆盖正常路径 + 边界 + 异常
- 重构后对比输出一致性

##### 策略 B: Contract Tests（契约测试）

**适用**: 对外 API / SDK / 公共模块
**做法**:

- 从调用者视角定义契约
- 固定接口签名 + 响应格式 + 错误码
- 使用 Pact / OpenAPI 等工具

##### 策略 C: Seam Tests（打缝测试）

**适用**: 依赖 DB / HTTP / 时间 / 随机数
**做法**:

- 抽象外部依赖为接口
- 注入测试替身（mock/stub/fake）
- 隔离后测试核心逻辑

**选择优先级**:

1. 公共接口 → 先补 Contract Tests
2. 有外部依赖 → 先打 Seam
3. 都没有 → 用 Characterization 兜底

#### Step 2: 建立行为基线

```javascript
// 等效性测试
describe("before refactor", () => {
  const inputs = [
    { input: null, expected: [] },
    { input: [], expected: [] },
    { input: [1, 2, 3], expected: [1, 2, 3] },
    // 更多边界值
  ];

  inputs.forEach(({ input, expected }) => {
    it(`should handle ${JSON.stringify(input)}`, () => {
      expect(oldFunction(input)).toEqual(expected);
    });
  });
});
```

#### Step 3: 创建重构分支

```bash
git checkout -b refactor/xxx
```

---

### 测试入口探测（跨语言通用）

执行重构前，**必须先探测**项目的测试/构建/检查入口：

#### 探测顺序

1. **CI 配置**: `.github/workflows/*.yml` / `.gitlab-ci.yml` / `Jenkinsfile`
2. **构建文件**: `Makefile` / `Justfile` / `Taskfile.yml`
3. **包管理器**: `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `pom.xml` / `build.gradle`
4. **README**: 查找 `## Testing` / `## Development` 章节

#### 常见命令映射

| 生态          | 测试             | Lint                   | 类型检查            |
| ------------- | ---------------- | ---------------------- | ------------------- |
| Node.js       | `npm test`       | `npm run lint`         | `npm run typecheck` |
| Python        | `pytest`         | `ruff check .`         | `mypy .`            |
| Go            | `go test ./...`  | `golangci-lint run`    | (编译即检查)        |
| Rust          | `cargo test`     | `cargo clippy`         | (编译即检查)        |
| Java (Maven)  | `mvn test`       | `mvn checkstyle:check` | (编译即检查)        |
| Java (Gradle) | `./gradlew test` | `./gradlew check`      | (编译即检查)        |

#### 🔥 铁律

- **找不到入口 = 不能开始重构**
- 必须记录: "我跑了什么命令 + 结果是什么"

---

### 安全重构模式

#### 模式 1: 提取函数

**场景**: 函数过长，逻辑混杂

```javascript
// Before
function processOrder(order) {
  // 验证逻辑 (20行)
  // 计算逻辑 (30行)
  // 存储逻辑 (20行)
}

// After
function processOrder(order) {
  validateOrder(order);
  const total = calculateTotal(order);
  saveOrder(order, total);
}

function validateOrder(order) {
  /* 提取的验证逻辑 */
}
function calculateTotal(order) {
  /* 提取的计算逻辑 */
}
function saveOrder(order, total) {
  /* 提取的存储逻辑 */
}
```

**步骤**:

1. 识别可提取的代码块
2. 创建新函数，复制代码
3. 替换原位置为函数调用
4. 运行测试
5. Commit

#### 模式 2: 重命名

**场景**: 命名不清晰

```javascript
// Before
const d = new Date();
const t = calcT(d);

// After
const currentDate = new Date();
const totalAmount = calculateTotalAmount(currentDate);
```

**步骤**:

1. 使用 IDE 的重命名功能 (F2)
2. 检查所有引用
3. 运行测试
4. Commit

#### 模式 3: 移动代码

**场景**: 代码放错位置

```bash
# Before
src/utils/api.ts     # 包含 payment 相关代码

# After
src/services/payment/api.ts
```

**步骤**:

1. 创建新文件
2. 移动代码
3. 更新 import
4. 运行测试
5. Commit
6. 删除旧代码
7. 运行测试
8. Commit

#### 模式 4: 接口隔离

**场景**: 巨型类/接口

```typescript
// Before
interface UserService {
  createUser();
  updateUser();
  deleteUser();
  login();
  logout();
  resetPassword();
  sendEmail();
  // 30+ methods
}

// After
interface UserCrudService {
  createUser();
  updateUser();
  deleteUser();
}

interface AuthService {
  login();
  logout();
  resetPassword();
}

interface NotificationService {
  sendEmail();
}
```

#### 模式 5: 策略模式替代条件

**场景**: 大量 if-else / switch

```javascript
// Before
function calculatePrice(type, amount) {
  if (type === "basic") {
    return amount;
  } else if (type === "premium") {
    return amount * 0.9;
  } else if (type === "vip") {
    return amount * 0.8;
  }
}

// After
const pricingStrategies = {
  basic: (amount) => amount,
  premium: (amount) => amount * 0.9,
  vip: (amount) => amount * 0.8,
};

function calculatePrice(type, amount) {
  return pricingStrategies[type](amount);
}
```

---

### 小步重构流程

```
单次重构循环:

1. 确定最小改动范围
2. 进行改动 (< 10分钟)
3. 运行测试
4. 测试通过 → Commit
5. 测试失败 → 立即回滚，分析原因

重复以上循环，直到重构完成
```

#### 小步的量化标准

| 指标         | 阈值      | 超限处理          |
| ------------ | --------- | ----------------- |
| 单次改动行数 | ≤ 200 行  | 拆分为多次 commit |
| 单次涉及文件 | ≤ 3 个    | 拆分为多次 commit |
| 单次重构模式 | 1 种      | 一次只做一种模式  |
| 单次执行时间 | ≤ 15 分钟 | 拆分为更小步骤    |

**🔥 铁律**: 改完 → 跑测试 → 绿灯 → 立即 Commit → 再改下一步

#### Commit 粒度示例

```
refactor: extract validateOrder function
refactor: extract calculateTotal function
refactor: extract saveOrder function
refactor: rename d to currentDate
refactor: move payment code to services/payment
```

---

### 危险重构模式（避免）

#### ❌ 大爆炸重构

```bash
# 一次性改 50 个文件
# 几天都在一个分支上
# 最后才跑测试
```

#### ❌ 顺手添加功能

```javascript
// 重构时顺便
function processOrder(order) {
  // ... 重构的代码 ...

  // 新加的功能 ← 不该在重构 PR 里
  sendNotification(order);
}
```

#### ❌ 无测试重构

```bash
# "测试太慢了，先重构，回头补测试"
# 结果: Bug 上线
```

---

### 重构风险分级

#### R1 内部重排（低风险）

- **范围**: 提取函数、重命名、移动代码、简化条件
- **流程**: 标准小步重构
- **验证**: 单元测试通过即可

#### R2 边界重构（中风险）

- **范围**: 模块拆分、依赖倒置、接口隔离、层次重组
- **流程**: 小步重构 + 集成测试
- **验证**: 单测 + 集成测试 + 手动验证关键路径

#### R3 契约/数据重构（高风险）

- **范围**: API 变更、DB Schema 迁移、事件格式调整
- **流程**: Strangler Fig + 双写 + 灰度
- **验证**: 全量回归 + 性能基线 + 灰度验证 + 回滚演练

#### 🔥 分级原则

- 不确定时往高级别靠
- R3 必须有 Plan 文档
- R3 必须有回滚方案

---

### 停止条件与升级机制

#### 🛑 立即停止（触发任一即暂停）

- 测试持续失败且无法定位根因
- 改动触及公共 API / 数据库 Schema / 跨服务契约
- 需要数据迁移/回填但计划不完整
- 行为差异无法通过测试解释（非预期 diff）
- 改动范围膨胀超过原计划 200%

#### ⚠️ 升级确认（需人工决策）

- 性能指标变化超过 ±20%
- 跨团队契约变更
- 安全/权限逻辑重写
- 需要多服务协同发布

#### 📝 停止后动作

1. 记录当前状态到 Plan
2. 列出阻塞原因
3. 提出备选方案
4. 请求人工介入

---

### 重构检查清单

**开始前**:

- [ ] 现有测试通过
- [ ] 覆盖率足够
- [ ] 创建了分支
- [ ] 明确重构范围

**进行中**:

- [ ] 每次改动 < 10 分钟
- [ ] 改完立即跑测试
- [ ] 测试通过立即 Commit
- [ ] 没有混入新功能

**完成后**:

- [ ] 所有测试通过
- [ ] 行为与重构前一致
- [ ] 代码审查
- [ ] 更新文档（如需）

---

### 回滚策略

#### 单步回滚

```bash
# 最近一次 commit 有问题
git revert HEAD
```

#### 部分回滚

```bash
# 回滚特定文件
git checkout HEAD~1 -- path/to/file
```

#### 全量回滚

```bash
# 放弃整个重构分支
git checkout main
git branch -D refactor/xxx
```

---

### 并行重构（Strangler Fig 模式）

当重构风险太高时:

```
1. 新建新实现，与旧实现并存
2. 路由层控制流量分配
3. 逐步切换流量到新实现
4. 验证无误后删除旧实现
```

```javascript
// 路由层
function processOrder(order) {
  if (featureFlags.useNewProcessor) {
    return newProcessOrder(order);
  }
  return oldProcessOrder(order);
}
```

---

### 记忆锚点

```
#refactor: [目标] [模式] [影响范围]
```

示例:

```
#refactor: payment模块 提取函数 影响5个文件
#refactor: UserService 接口隔离 拆分为3个服务
```

---

## Part 3: 测试缺口分析

### 核心理念

覆盖率不等于测试质量。100% 覆盖率可能全是安慰剂测试。
目标是找出 **真正缺少测试的关键路径**，而非追求数字。

---

### 输入契约

#### 必需输入

| 输入            | 来源                   | 说明         |
| --------------- | ---------------------- | ------------ |
| `changed_files` | `git diff --name-only` | 变更文件列表 |

#### 可选输入

| 输入              | 路径/格式            | 说明         |
| ----------------- | -------------------- | ------------ |
| `coverage_report` | `coverage/lcov.info` | 覆盖率报告   |
| `test_framework`  | jest/pytest/vitest   | 测试框架     |
| `critical_paths`  | 配置文件/列表        | 业务关键模块 |

#### 降级策略

| 缺少输入       | 降级策略                                        |
| -------------- | ----------------------------------------------- |
| 无覆盖率报告   | 用静态启发式分析（分支复杂度/错误处理块）       |
| 无 diff 范围   | 全量扫描关键目录 (`src/services/`, `src/core/`) |
| 无测试框架信息 | 自动检测 (`package.json`/`pytest.ini`/`go.mod`) |

#### 上下文收集

```bash
# 使用上下文收集脚本（自动检测 diff 和覆盖率）
python3 scripts/collect_context.py collect

# 指定 base branch
python3 scripts/collect_context.py collect --base origin/develop

# 输出到文件
python3 scripts/collect_context.py collect --output context.json --pretty
```

---

### 可计算优先级评分

#### 评分维度

| 维度           | 分值 | 例子                                |
| -------------- | ---- | ----------------------------------- |
| **业务影响**   | +5   | 支付流程/登录认证/数据写入/权限控制 |
| **变更相关**   | +4   | 本次 diff 涉及到的函数/模块         |
| **覆盖信号**   | +3   | 分支覆盖 < 80% / 行覆盖 < 90%       |
| **失败代价**   | +3   | 会导致资金损失/安全漏洞/服务不可用  |
| **历史风险**   | +2   | 同类 bug 曾复发 / hotfix 记录       |
| **复杂度信号** | +2   | 多分支(>5)/状态机/并发/递归         |

#### 优先级等级

| 总分 | 等级  | 行动                       |
| ---- | ----- | -------------------------- |
| ≥12  | 🔴 P0 | **必须立即补测**，阻断发布 |
| 8-11 | 🟠 P1 | 本次 PR 必须修复           |
| 4-7  | 🟡 P2 | 建议修复，可延后           |
| <4   | 🟢 P3 | 可选修复                   |

#### 评分示例

```markdown
## processPayment() 缺口评分

| 维度       | 分值   | 理由                   |
| ---------- | ------ | ---------------------- |
| 业务影响   | +5     | 支付核心流程           |
| 变更相关   | +4     | 本次 diff 修改了此函数 |
| 覆盖信号   | +3     | 分支覆盖仅 45%         |
| 失败代价   | +3     | 可能导致重复扣款       |
| 历史风险   | +2     | 上月有同类 bug         |
| 复杂度信号 | +1     | 有 3 个条件分支        |
| **总分**   | **18** | 🔴 P0 必须立即补测     |
```

---

### 测试质量信号（安慰剂检测）

#### 🚨 高风险安慰剂模式

| 模式           | 检测方法                           | 风险              |
| -------------- | ---------------------------------- | ----------------- |
| **弱断言**     | 只有 `should not throw` 不验证输出 | 🔴 测试无意义     |
| **Mock 过度**  | 把被测对象也 mock 掉               | 🔴 测试无效       |
| **常量断言**   | `expect(true).toBe(true)`          | 🔴 恶意欺骗       |
| **不变量缺失** | 金额/权限/幂等无性质测试           | 🟠 关键属性未验证 |
| **快照滥用**   | 任意输出都 snapshot                | 🟡 变更就通过     |

#### 检测命令

```bash
# 搜索弱断言
rg "expect\(.*\)\.not\.toThrow\(\)" --glob "*.test.*" -l

# 搜索常量断言
rg "expect\(true\)\.toBe\(true\)" --glob "*.test.*"

# 搜索过度 Mock
rg "jest\.mock\(.*/被测模块" --glob "*.test.*"
```

#### 断言强度检查清单

```markdown
□ 有具体返回值断言（不只是"不抛错"）
□ 错误场景有具体错误类型/消息断言
□ Mock 仅用于外部依赖，不 mock 被测对象
□ 关键业务属性有不变量测试（金额不变/幂等/权限边界）
```

---

### 常见缺口模式

#### 1. 错误处理缺口

```javascript
try {
  await riskyOperation();
} catch (error) {
  // ⚠️ 测试覆盖这个分支了吗？
}
```

**检测**: `rg "catch\s*\(" --glob "*.ts" -l`

#### 2. 条件分支缺口

```javascript
if (condition) {
  // true 分支
} else {
  // ⚠️ false 分支 - 容易漏测
}
```

**检测**: 分支覆盖率 < 行覆盖率

#### 3. 早返回缺口

```javascript
function process(input) {
  if (!input) return null; // ⚠️ 测了吗？
  if (!input.valid) return { error: "invalid" }; // ⚠️ 这里呢？
}
```

**检测**: `rg "return\s+\w+;" -B2 --glob "*.ts"`

#### 4. 异步失败缺口

```javascript
const result = await fetch(url); // ⚠️ 网络失败呢？
```

**检测**: 搜索所有 `await`，确认有 reject 场景测试

#### 5. 🆕 并发/幂等/重试缺口

```javascript
// 支付重复扣款场景
async function chargeUser(orderId, amount) {
  // ⚠️ 并发调用会重复扣款吗？
  // ⚠️ 重试时幂等吗？
}
```

**检测**: 关键操作无幂等键/锁机制

#### 6. 🆕 时间与时区缺口

```javascript
if (expireAt < new Date()) {
  // ⚠️ 跨天边界？跨时区？
}
```

**检测**: 搜索 `new Date()` / `Date.now()` / `.getTime()`

#### 7. 🆕 权限与鉴权细分缺口

```javascript
if (user.role === "admin") {
  // ⚠️ RBAC 边界：admin vs superadmin？
  // ⚠️ ABAC 边界：资源所有权？
}
```

**检测**: 权限检查只测 happy path，未测边界

#### 8. 🆕 数据一致性缺口

```javascript
await db.transaction(async (tx) => {
  await tx.debit(accountA, amount);
  await tx.credit(accountB, amount); // ⚠️ 这里失败呢？
});
```

**检测**: 事务边界/部分失败/回滚场景

#### 9. 🆕 序列化/兼容性缺口

```javascript
const data = JSON.parse(payload);
// ⚠️ 字段缺失？类型变化？版本兼容？
```

**检测**: 无 schema 验证 / 无向后兼容测试

#### 10. 🆕 可观测性路径缺口

```javascript
logger.error("Payment failed", { amount, userId });
// ⚠️ 错误打点正确吗？requestId 有吗？
// ⚠️ 敏感信息泄露了吗？
```

**检测**: 日志/metrics 路径无测试

---

### 反安慰剂执行法

#### 🔥 Mutation Test 优先

```bash
# JavaScript/TypeScript
npx stryker run --files "src/services/payment.ts"

# Python
mutmut run --paths-to-mutate=src/services/

# 分析存活突变体
# Survived: payment.ts:42 - Changed > to >=
# → 说明边界值测试不足
```

#### 无工具时：手动突变注入

**步骤**:

1. 手动注入 1-2 个等价但错误的变更
2. 运行测试
3. **测试必须红**，否则测试无效

```javascript
// 原代码
if (amount > 0) { ... }

// 手动突变
if (amount >= 0) { ... }  // 边界变化

// 运行测试 → 必须失败！
```

#### 关键路径：故障注入测试

```javascript
// 支付流程：至少 1 个故障注入测试
it("should handle gateway timeout gracefully", async () => {
  gateway.charge.mockImplementation(
    () =>
      new Promise((_, reject) =>
        setTimeout(() => reject(new TimeoutError()), 5000),
      ),
  );

  const result = await processPayment(order);
  expect(result.status).toBe("pending_retry");
  expect(alertService.notify).toHaveBeenCalled();
});
```

---

#### 突变测试集成 (Mutation Testing Integration)

> 覆盖率 ≠ 测试质量。突变测试验证测试是否真正检测到代码变更。

**工具链**:

- Python: `mutmut` → `mutmut run --paths-to-mutate=src/`
- JavaScript/TypeScript: `stryker` → `npx stryker run`

**阈值**:

| 指标 | 目标 | 不合格 |
|------|------|--------|
| Mutation Score | ≥ 80% | < 60% |
| 关键模块 Mutation Score | ≥ 90% | < 75% |
| 存活突变体数 | 持续下降趋势 | 持续上升 |

**检测安慰剂测试**:

1. 运行 `mutmut` / `stryker` 生成突变体
2. 存活突变体 = 测试未检测到的逻辑变更
3. 每个存活突变体必须：增加测试覆盖 或 标记为等价突变体

#### 性能审查检查清单 (Performance Review Checklist)

| 类别 | 信号 | 严重级别 |
|------|------|---------|
| **CPU/分支** | 热路径中的间接调用、缺少分支预测提示 | MAJOR |
| **内存** | 无界分配、Goroutine/Promise 未绑定上下文 | BLOCKER |
| **并发** | 大临界区、无背压的工作队列 | BLOCKER |
| **数据库** | 缺失索引、N+1 查询、全表扫描 | MAJOR |
| **证据要求** | CPU/Heap profile、P95/P99 延迟对比、GC 停顿时间 | — |

---

### 结构化输出 Schema

#### JSON Schema（CI 可解析）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "meta": {
      "type": "object",
      "properties": {
        "analyzed_files": { "type": "integer" },
        "total_gaps": { "type": "integer" },
        "analysis_date": { "type": "string", "format": "date-time" }
      }
    },
    "gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "file": { "type": "string" },
          "line": { "type": "integer" },
          "function": { "type": "string" },
          "type": {
            "enum": [
              "error_handling",
              "boundary",
              "async",
              "concurrency",
              "permission",
              "time",
              "serialization"
            ]
          },
          "priority_score": { "type": "integer", "minimum": 0, "maximum": 19 },
          "priority_level": { "enum": ["P0", "P1", "P2", "P3"] },
          "description": { "type": "string" },
          "suggested_test": { "type": "string" }
        },
        "required": ["id", "file", "type", "priority_score", "priority_level"]
      }
    },
    "placebo_warnings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file": { "type": "string" },
          "line": { "type": "integer" },
          "pattern": { "type": "string" },
          "severity": { "enum": ["critical", "warning"] }
        }
      }
    }
  }
}
```

#### 输出示例

```json
{
  "meta": {
    "analyzed_files": 5,
    "total_gaps": 8,
    "analysis_date": "2024-01-15T10:30:00Z"
  },
  "gaps": [
    {
      "id": "gap-001",
      "file": "src/services/payment.ts",
      "line": 42,
      "function": "processPayment",
      "type": "concurrency",
      "priority_score": 18,
      "priority_level": "P0",
      "description": "无幂等保护，并发可能重复扣款",
      "suggested_test": "it('should be idempotent with same orderId', ...)"
    }
  ],
  "placebo_warnings": [
    {
      "file": "src/services/__tests__/payment.test.ts",
      "line": 15,
      "pattern": "weak_assertion",
      "severity": "warning"
    }
  ]
}
```

---

### 缺口报告模板

````markdown
# 测试缺口分析报告

**分析范围**: [文件/模块列表]
**分析日期**: [日期]

## 摘要

| 指标       | 数值 |
| ---------- | ---- |
| 分析文件数 | X    |
| 发现缺口数 | Y    |
| P0 缺口    | Z    |
| 安慰剂警告 | W    |

## P0 缺口 (阻断发布)

### 1. [缺口描述]

- **位置**: `file.ts:42`
- **类型**: 并发/幂等
- **评分**: 18 (业务+5, 变更+4, 覆盖+3, 代价+3, 历史+2, 复杂+1)
- **建议测试**:

```javascript
it('should be idempotent', () => { ... });
```
````

### P1 缺口 (本次 PR 修复)

...

### 安慰剂警告

...

```

---

## 适用范围

| 场景 | 适用性 | 说明 |
|------|--------|------|
| ✅ PR/变更驱动缺口扫描 | **最佳** | 有明确 diff，针对性强 |
| ✅ Bug 后补测 | 适合 | 定位到问题代码后分析 |
| ✅ 发布前检查 | 适合 | 配合覆盖率报告 |
| ⚠️ 全仓库盲扫 | **不推荐** | 无上下文，噪音大，建议缩小范围 |

---

## 记忆锚点

```

# test-gap: [模块] [P0:X P1:Y P2:Z] [安慰剂:W]

```

示例:
```

# test-gap: payment P0:2 P1:3 P2:3 安慰剂:1

# test-gap: auth P0:0 P1:1 P2:2 已全部补充

```

---

## 深度模式检查清单 (合并自: 深度审查模式)

### 自动化预检流水线 (Pre-Review Pipeline)

| 层级 | 工具 | 通过条件 | 失败处理 |
|------|------|---------|---------|
| L1 格式化 & Lint | Prettier/Ruff | 0 格式错误 | 自动修复后重新提交 |
| L2 静态安全扫描 | CodeQL/Semgrep | 0 High/Critical | 阻塞合并，手动修复 |
| L3 AI 上下文审查 | LLM Review | 标记可疑点 | 提供给人工审查者参考 |
| L4 策略门禁 | CI Policy | 覆盖率≥80%, Diff≤500行 | 阻塞合并 |

### OWASP ASVS 5.0 安全验证 (14 类别)

| 类别 | 关键检查 | 严重级别 |
|------|---------|---------|
| 认证 | 密码策略、MFA、凭证存储 | BLOCKER |
| 会话管理 | Token 熵值、生命周期、固定攻击 | BLOCKER |
| 访问控制 | RBAC/ABAC、权限提升、IDOR | BLOCKER |
| 输入验证 | 注入预防、白名单、编码 | BLOCKER |
| 密码学 | 算法强度、密钥管理 | BLOCKER |
| 错误处理 | 安全日志、审计追踪 | MAJOR |
| 数据保护 | 密钥管理、PII 处理 | BLOCKER |
| 通信安全 | TLS、证书固定 | BLOCKER |
| API 安全 | 限流、认证、Schema 验证 | BLOCKER |
| 文件/资源 | 上传验证、路径遍历 | MAJOR |
| 业务逻辑 | 工作流完整性、竞态 | MAJOR |
| 配置 | 安全加固、默认值 | MAJOR |
| 恶意代码 | 供应链、后门 | BLOCKER |
| 架构 | 安全设计模式 | MAJOR |

### 性能回归检测

**触发条件**: 改动涉及数据库查询 / API 端点 / 循环逻辑 / 数据结构

| 指标 | 阈值 | 级别 |
|------|------|------|
| P99 延迟恶化 | > 10% | MAJOR |
| P99 延迟恶化 | > 30% | BLOCKER |
| 内存持续增长 | 30 分钟无收敛 | BLOCKER |
| Bundle Size 增长 (前端) | > 5% | MAJOR |
| Bundle Size 增长 (前端) | > 20% | BLOCKER |

### 评论前缀规范

- `BLOCKER:` — 必须修复，阻塞合并
- `MAJOR:` — 应该修复，强烈建议
- `MINOR:` — 建议修复，可下次迭代
- `NIT:` — 可选美化
- `FYI:` — 信息分享，无需行动
- `Q:` — 提问，需要作者回答
