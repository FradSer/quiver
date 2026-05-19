# Quiver ![Python 3.13](https://img.shields.io/badge/python-3.13-blue) ![Status: Complete](https://img.shields.io/badge/status-complete-brightgreen)

[![Built with Claude Agent SDK](https://img.shields.io/badge/built_with-Claude_Agent_SDK-orange)](https://code.claude.com/docs/en/agent-sdk) [![Tests](https://img.shields.io/badge/tests-64_passing-brightgreen)](#开发)

[English](README.md) | **简体中文**

基于 Claude Agent SDK 构建的求职代理工具。Quiver 能搜索职位、解析并验证职位描述、生成诚实的匹配分析、定制简历，以及起草求职邮件。

## 为什么叫"工具链"

模型只是一部分；围绕它的验证、审查关卡、单一事实来源、工具对接——这些构成了**工具链**。Quiver 的核心特性是**诚实工具链**：一套防止代理捏造事实、夸大陈述或信任未验证职位描述的约束机制。

工作原理：

- Intake 代理为每条职位标注 `verification_status`（verified、past、reconstructed），只有 verified 和 past 的描述会被信任。
- Reviewer 代理是事实审查关卡——在简历和邮件发出前捕获夸大陈述。
- 个人档案文件为只读，任何代理都不能修改事实来源。
- GitHub star 数通过 `gh` CLI 实时获取，不依赖模型记忆。

## 安装

```bash
uv sync
```

Quiver 通过已登录的 Claude Code CLI 认证，不需要 API key。Agent SDK 以无头模式运行 CLI 并复用其会话。先运行 `claude` 确认已登录。

如需直接使用 Anthropic API key，复制 `.env.example` 为 `.env` 并设置 `ANTHROPIC_API_KEY`。

## 配置

所有路径和个人信息均可通过 `.env` 配置：

```bash
cp .env.example .env
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | _(无)_ | 直接使用 API key；留空则复用 Claude Code CLI 会话 |
| `QUIVER_KNOWLEDGE_DIR` | `~/Documents/Work Research` | 知识库目录（个人档案 + 产出物） |
| `QUIVER_PROFILE_FILENAME` | `profile.md` | 知识库中的个人档案文件名 |

## 命令

```bash
quiver --version          # 打印版本
quiver smoke              # 验证 SDK 连通性（需联网）
quiver intake <file|url>  # 将职位描述解析为结构化数据
quiver analyze            # 根据个人档案生成匹配报告
quiver tailor             # 为特定职位生成定制简历
quiver email              # 起草求职邮件
quiver review <artifact>  # 对产出物进行事实审查
quiver scout              # 通过网络搜索职位线索
quiver run <file|url>     # 完整流水线：intake -> analyze -> tailor -> email
quiver eval               # 运行黄金用例评估（需联网）
```

## 架构

Clean Architecture，四层依赖向内指向：

```
domain/          纯值对象和接口——无外部导入
application/     基于领域接口的编排——不导入基础设施
infrastructure/  Claude Agent SDK、文件系统、GitHub CLI 适配器
cli.py           组合根——仅负责组装，不含业务逻辑
```

六个子代理各司其职：

| 代理 | 职责 |
|------|------|
| **Scout** | 通过网络搜索职位线索 |
| **Intake** | 将职位描述解析为结构化数据 |
| **Analyst** | 根据个人档案生成匹配报告 |
| **Reviewer** | 对产出物进行诚实度和事实审查 |
| **Tailor** | 生成定制简历 |
| **Writer** | 起草求职邮件 |

评估工具（`evaluation/`）用黄金用例检验真实代理，防止诚实检查退化。

## 开发

```bash
uv run pytest            # 全部测试，离线运行（64 个测试）
uv run ruff check .      # 代码检查
uv run mypy              # 类型检查（严格模式）
uv run quiver smoke      # SDK 连通性检查（需联网）
uv run quiver eval       # 黄金用例评估，生成 eval-report.md
```

BDD 驱动：先写 `.feature` 场景，再写失败测试，最后实现。Feature 文件在 `tests/features/`。

## 项目状态

全部阶段（P0–P8）已完成。完整路线图见 [`docs/plan.md`](docs/plan.md)。
