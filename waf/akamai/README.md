# Akamai AppSec适配器

后续步骤会把`waf/policies`中的通用策略映射为Akamai AppSec自定义规则：

- `monitor` → `Alert`
- `block` → `Deny`
- `allow` → 平台支持的放行或例外配置

PR阶段只生成变更计划；合并后先激活到Akamai Staging网络，经审批后再激活同一已测试版本到Production。
