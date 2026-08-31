# 生产式 WAF Policy as Code 流程

## 1. 系统职责

| 系统 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| 监控/SIEM | 发现攻击、异常流量和误报 | 不直接修改生产策略 |
| Jira | 记录事件、责任人、审批和状态 | 不保存 WAF 策略正文 |
| GitHub | 保存策略、分支、PR和审计历史 | 不持有生产平台长期密钥 |
| Jenkins | 校验、测试、生成计划、审批和发布 | 不绕过PR直接修改源策略 |
| Akamai/AWS | 执行已审批的 WAF 策略 | 不作为策略唯一事实来源 |

GitHub 中的策略代码是期望状态。Akamai或AWS中的实际配置是运行状态。Jenkins负责比较并将运行状态推进到已审批的期望状态。

## 2. 标准变更流程

1. 监控平台或安全人员发现异常。
2. 自动化创建 Jira，例如 `SEC-1024`。
3. Jira Automation 调用 GitHub 创建 `waf/SEC-1024-short-description` 分支。
4. 安全工程师或受控自动化程序修改该分支中的 WAF 策略和测试用例。
5. 创建 PR；PR标题或提交信息必须包含 `SEC-1024`。
6. Jenkins在PR阶段执行校验、测试和部署计划，禁止执行生产写操作。
7. 代码审核人和安全审核人批准PR，分支合并到受保护的 `main`。
8. Jenkins将策略部署到Staging；AWS使用Count，Akamai使用Staging/Alert。
9. 自动验证恶意请求能够命中、正常请求不被误拦截，并观察平台指标。
10. 生产审批人确认后，将同一个已测试版本提升到Production/Block。
11. Jenkins执行部署后健康检查；失败则恢复上一版本。
12. Jenkins把构建号、提交SHA、策略版本、部署结果和回滚结果写回Jira。

## 3. 紧急变更流程

正在发生的严重攻击可能无法等待完整观察周期，但仍不能跳过审计：

1. Jira标记为紧急安全事件。
2. 创建紧急分支和PR，并由预先指定的安全审批人批准。
3. Jenkins只运行缩短后的强制检查集，不允许完全跳过测试。
4. 优先发布低风险缓解措施，例如限速、IP集合或特定路径规则。
5. 发布后持续观察，并补齐完整测试和事件复盘。

## 4. Jenkins运行模式

| 模式 | 外部写操作 | 使用场景 |
| --- | --- | --- |
| `validate` | 无 | 本地学习和PR校验 |
| `plan` | 只读查询，可生成平台变更计划 | PR审核和部署预览 |
| `staging` | 写入非生产或观察模式 | 合并后的测试发布 |
| `production` | 写入生产WAF | 人工审批后的正式发布 |
| `rollback` | 恢复已知良好版本 | 健康检查失败或误报严重 |

默认模式必须是 `validate`。只有受保护分支、明确的平台选择、有效凭据和人工审批同时满足时，才允许进入 `production`。

## 5. 本机当前能力边界

当前已检测到：

- Git、Docker、Java、jq、Node.js、npm和Python 3。
- Docker socket存在，可用于后续本地WAF容器测试。

当前未检测到：

- Terraform、AWS CLI和Akamai CLI。
- AWS、Akamai、Jira和GitHub API凭据。

因此当前可以实现并验证：

- 仓库目录和分支规范；
- Jenkins Pipeline语法与本地脚本；
- WAF策略静态校验；
- Docker中的规则测试；
- AWS/Akamai部署命令的dry-run和mock测试。

当前不能执行：

- 在真实Jira中创建工单；
- 在真实GitHub组织中自动创建分支或PR；
- 修改真实AWS WAF Web ACL；
- 激活真实Akamai AppSec配置。

## 6. 真实接入所需配置

后续在Jenkins中使用Credentials注入，禁止提交到Git：

| 平台 | 建议的Jenkins Credential ID | 用途 |
| --- | --- | --- |
| GitHub | `github-app-waf-bot` | 建分支、更新PR状态 |
| Jira | `jira-waf-automation` | 创建和更新工单 |
| AWS | `aws-waf-deployer` | Terraform/CLI部署AWS WAF |
| Akamai | `akamai-appsec-edgerc` | AppSec配置和网络激活 |

真实权限应限制到指定仓库、Jira项目、AWS Web ACL或Akamai安全配置，不能使用个人管理员账号。
