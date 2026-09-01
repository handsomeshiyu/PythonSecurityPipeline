# 本地Jenkins学习环境

## 为什么使用Docker

本项目使用独立的Docker容器运行Jenkins，不在macOS中直接安装Jenkins。这样可以隔离依赖、保留数据，并在需要时安全地重新创建环境。

本地学习环境与生产环境的区别：

- 本地Jenkins只用于理解和验证流水线。
- 目前只开放`validate`和`plan`，不能修改真实WAF。
- GitHub Webhook无法直接访问家用电脑时，可以先在Jenkins中手工触发构建。
- 生产Jenkins应部署在受控网络中，并配置HTTPS、备份、访问控制和最小权限凭据。

## 文件说明

- `compose.jenkins.yml`：Jenkins容器、端口和持久化数据卷。
- `jenkins-modern/Dockerfile`：固定Jenkins和Java版本，安装Git、Python与jq。
- `jenkins-modern/plugins.txt`：Pipeline、GitHub和凭据相关插件。
- `Jenkinsfile.waf`：本项目新的WAF策略验证与计划管道。

旧的`docker-compose.yml`和`jenkins/`目录属于原教学项目，本地学习新流程时不使用它们。

## 安全设计

当前容器没有挂载Docker socket，也没有使用privileged模式。后续加入WAF容器测试时，再使用隔离的Docker执行节点，避免让Jenkins控制宿主机Docker守护进程。

Jenkins数据保存在Docker命名卷`jenkins_data`中。停止容器不会删除数据；删除数据卷才会清除Jenkins配置。

任何Jira、GitHub、AWS或Akamai凭据都必须存入Jenkins Credentials，不能写入Compose文件、Jenkinsfile或Git仓库。

## 后续启动命令

在项目根目录执行：

```bash
docker compose -f compose.jenkins.yml up --detach --build
```

启动后访问：

```text
http://localhost:8080
```

首次解锁密码通过下面的命令读取：

```bash
docker exec waf-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

这些命令将在下一步骤中逐条执行。本步骤只创建配置文件，不启动容器。
