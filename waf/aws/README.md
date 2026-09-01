# AWS WAF适配器

后续步骤会把`waf/policies`中的通用策略映射为AWS WAFv2规则：

- `monitor` → `Count`
- `block` → `Block`
- `allow` → `Allow`

PR阶段只生成变更计划；合并后先发布到测试Web ACL或生产Web ACL的Count模式，经审批后才切换为Block。
