# AGENTS.md

这是 AI 团队的业务仓库，不是 OpenClaw 自身工作区。

## 仓库规则

- 所有新项目默认建在 `projects/<project-slug>/`
- 多个项目可以共存，但目录边界必须清楚
- 共享脚本、模板、通用组件放在 `shared/`
- 仓库级文档、计划、决策记录放在 `docs/`
- OpenClaw 团队默认通过 `/home/hoyo/.openclaw/workspace-team/repo.env` 指向本仓库

## 开发原则

- 先明确目标，再建项目目录
- 优先小步提交，不把多个无关改动混在一起
- 能验证就验证，不能验证就明确说明
- 不擅自删除已有项目目录
- 不直接修改 `.git/` 内部内容

## AI 团队协作

- Halibut 负责拆解、调度、验收
- Calamitas 负责仓库摸排、问题复现和首轮实现
- Solin 负责架构与测试门槛
- Gloria 负责收尾集成、文档和交付整理

## 新项目落地格式

建立新项目时，优先包含：

1. `projects/<project-slug>/README.md`
2. 必要的源码目录
3. 最小可运行或可验证骨架
4. 该项目自己的简短说明
5. 如由 OpenClaw 团队创建，对应案例目录会写在 `workspace-team/cases/<case-id>/`
