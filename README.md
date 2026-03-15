# ai-group-1

这是 `hoyo ho` 的 AI 团队业务开发仓库。

仓库目标：

- 让 Halibut 代码团队在本地协作开发多个项目
- 以一个仓库统一管理项目目录、共享资源和文档
- 由本地 git 工作流负责版本控制，再按需要推送到 GitHub

## 建议结构

```text
projects/   各个独立项目
shared/     可复用脚本、模板、公共资源
docs/       仓库级文档、规划、决策记录
```

## AI 团队分工

- Halibut：拆解任务、分派员工、验收结果、汇总交付
- Calamitas：代码侦察、首轮实现、问题复现
- Solin：架构设计、质量门槛、测试规划
- Gloria：集成收尾、交付说明、最终整理

## 建议工作方式

1. 每个新项目放在 `projects/<project-slug>/`
2. 共享逻辑优先放到 `shared/`
3. 文档和决策记录放到 `docs/`
4. 并行开发时优先用分支或 `git worktree`
5. 不要把无关项目混进同一个目录
6. OpenClaw 团队工作区负责规则与案例，实际业务源码默认写在本仓库 `projects/` 下
