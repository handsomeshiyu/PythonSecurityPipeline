# DevSecOps 与 WAF 自动化改造学习路线

## 目标

在尽量保留原项目结构的基础上，把现有教学项目逐步改造成一条可理解、可测试、可回滚的 WAF Policy as Code 流水线：

```text
监控平台发现异常并创建 Jira
          ↓
Jira Automation 创建 GitHub 分支
          ↓
工程师修改该分支上的 WAF 策略
          ↓
GitHub Pull Request
          ↓
Jenkins 自动触发并拉取策略代码
          ↓
代码与依赖安全检查
          ↓
WAF 规则语法检查和自动化测试
          ↓
部署到 Staging 或 Count/Alert 模式
          ↓
通过 WAF 地址执行 DAST 和冒烟测试
          ↓
人工审批
          ↓
Akamai/AWS 生产发布、健康检查和失败回滚
          ↓
回写并关闭 Jira
```

## 改造原则

1. 原始 `master` 分支保持不动，所有改造在 `codex/waf-pipeline-modernization` 分支完成。
2. 每一步只解决一个问题，修改后先检查语法和差异，再进入下一步。
3. 默认不创建收费的云资源；涉及 AWS 的实际部署必须由学习者明确启动。
4. 密钥、Token、AWS 账号信息不能写入 Git，统一由 Jenkins Credentials 管理。
5. 安全检查不仅生成报告，达到阻断条件时还必须让流水线失败。
6. 本地演练默认使用 `dry-run`，只有显式选择目标平台并提供凭据后才允许真实发布。
7. Jira 负责工单和流程编排，GitHub 负责策略版本，Jenkins 负责验证和部署，WAF 平台负责执行策略。

## 当前基线

原项目的 Jenkins 流程由根目录的 `Jenkinsfile` 定义：

1. 从 GitHub 下载存在漏洞的 Python 示例应用。
2. 使用 TruffleHog 检查 Git 历史中的密钥。
3. 使用 Safety 检查 Python 依赖。
4. 使用 Bandit 进行静态代码扫描。
5. 使用 Lynis 检查 Dockerfile。
6. 使用 Ansible 在 AWS 中创建 EC2，并部署示例应用。
7. 使用 Selenium 和 Nikto 进行认证后的 DAST。
8. 使用 Lynis 审计 EC2 主机。
9. 在最后一个阶段启动 ModSecurity + OWASP CRS 容器。

## 当前基线中的关键缺口

- Jenkins 作业没有触发器，默认只能手工点击 `Build Now`。
- 应用仓库地址、AWS 区域、安全组、AMI 和子网均被硬编码。
- WAF 在 DAST 之后才部署，所以 DAST 没有验证 WAF 的拦截能力。
- 当前只是启动默认 CRS 镜像，没有管理和发布自定义 WAF 规则。
- 没有规则语法检查、正常请求测试、攻击请求测试和误报测试。
- Bandit 命令使用 `|| true`，发现问题后不会阻断流水线。
- EC2 清理逻辑被注释，运行后可能持续产生费用。
- Jenkins、Python、Ansible、AWS 模块和安全工具版本较旧。

## 分步计划

### 第 1 步：生产流程和运行边界

学习内容：Jira、GitHub、Jenkins、WAF 平台的职责边界，以及本地演练与真实部署的区别。

验收标准：

- 明确异常到工单、分支、PR、部署和关闭工单的状态流转。
- 列出真实部署所需的平台账号、CLI 和 Jenkins Credentials。
- 所有外部写操作默认关闭。

### 第 2 步：WAF 策略仓库和本地校验

学习内容：策略版本控制、目录设计、ModSecurity 规则语法。

验收标准：

- 新增独立的 `waf/aws`、`waf/akamai`、`waf/tests` 和变更元数据目录。
- 每次规则修改必须关联 Jira 工单并声明目标平台。
- 提供不依赖云账号的本地校验命令。

### 第 3 步：PR 验证和 Jenkins 门禁

学习内容：Webhook、Multibranch Pipeline、PR、正向测试、负向测试、误报和质量门禁。

验收标准：

- PR 创建或更新时自动触发 Jenkins。
- 运行策略语法、元数据、攻击请求和正常请求测试。
- PR 阶段只做验证和计划，不允许修改生产 WAF。

### 第 4 步：AWS WAF 与 Akamai 部署适配器

学习内容：Terraform plan/apply、Akamai配置版本、平台凭据和最小权限。

验收标准：

- 同一套 Jenkins 管道可以选择 `aws` 或 `akamai`。
- 没有凭据时只生成 dry-run 计划。
- AWS 和 Akamai 使用相互隔离的 Jenkins Credentials。

### 第 5 步：Staging、审批、生产发布与回滚

学习内容：部署门禁、最小权限、健康检查、回滚策略。

验收标准：

- 测试环境通过后需要人工审批才能发布生产策略。
- AWS 新策略先进入 Count，Akamai 新策略先进入 Alert/Staging，再切换到阻断模式。
- 健康检查失败时自动恢复上一版本策略。
- 无论成功失败，临时资源都能正确清理。

### 第 6 步：Jira编排与端到端演练

学习内容：Jira Automation、GitHub分支命名、状态回写、审计记录和操作手册。

验收标准：

- 提供 Jira 创建 GitHub 分支的配置说明。
- Jenkins 将验证、部署和回滚结果回写 Jira。
- 在没有外部账号时可完整演练 dry-run；接入凭据后可切换真实平台。

## 学习时如何查看每一步

每完成一个步骤，依次运行：

```bash
git status --short
git diff --check
git diff
```

重点观察：哪些文件发生变化、Jenkins 增加了哪个阶段、失败条件在哪里，以及云资源是否可能被创建。
