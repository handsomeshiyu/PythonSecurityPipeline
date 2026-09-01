# WAF策略目录

这个目录保存经过Git版本管理的WAF期望状态。当前阶段使用厂商无关的策略格式；后续由部署适配器转换为AWS WAF或Akamai AppSec配置。

```text
waf/
├── policies/   # 每条WAF策略及其测试用例
├── aws/        # 后续加入AWS WAF渲染和部署配置
└── akamai/     # 后续加入Akamai AppSec渲染和部署配置
```

每条策略必须：

- 关联一个Jira工单；
- 使用全局唯一的规则ID和优先级；
- 明确目标平台；
- Staging阶段使用`monitor`；
- Production阶段明确使用`block`或`allow`；
- 至少包含一个应命中的攻击用例和一个不应命中的正常用例。

本地校验：

```bash
python3 scripts/validate_waf_policies.py
```

`monitor`是仓库中的统一语义：AWS适配器会把它映射为`Count`，Akamai适配器会把它映射为`Alert`。
