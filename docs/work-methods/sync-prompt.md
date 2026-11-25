# 团队 Codex 同步与学习提示词

把下面这段提示词直接发给团队成员的 Codex（支持 macOS / Windows / Linux）。它只同步通用工作原则和表达规范到全局指引，**不安装新 Skill，也不运行仓库安装脚本**，并会现场演练检查表达能力是否达标。

---

```text
请将 https://github.com/leevi2010-cursor/skills 仓库 main 分支下的 4 份最新通用工作方法同步为我这台电脑的 Codex 全局工作指引，并立即按新标准完成一次表达校准：

- docs/work-methods/agent-work-methods.md（v3.0）
- docs/work-methods/expression-principles.md（v2.2）
- docs/work-methods/task-and-card-standards.md（v2.1）
- docs/work-methods/decision-loop.md（v1.5）

请严格按以下步骤执行：
1. 识别当前操作系统、用户主目录及实际生效的 CODEX_HOME（未设置时默认为用户主目录下的 .codex）。检查 AGENTS.md、AGENTS.override.md 及当前项目是否存在覆盖规则，说明哪一份实际生效。不跨机器照搬绝对路径。
2. 读取上述仓库 main 分支的最新 commit SHA，并固定在该 commit 读取 docs/work-methods/README.md 与上述 4 份正文，核对版本号与 README 一致。只读取和保存纯文本，不运行 portable_skill_manager，不安装软件或 Skill，不修改远程仓库，不上传本机资料。
3. 将 4 份原文保存到实际 CODEX_HOME/work-methods/ 目录，并生成或更新 sync-receipt.json 记录仓库 URL、commit SHA、版本号与文件 SHA-256。已有同名旧副本先备份再替换，保留其他未纳入本次范围的文件。
4. 先完整读取现有全局指引并备份，仅合并/更新一个由 <!-- BEGIN WORK-METHODS --> 与 <!-- END WORK-METHODS --> 包裹的管理段（不要整文件覆盖，保留我原有的其他规则）。管理段中写明：
   - 记录 4 份文档的本地路径、版本号与 commit SHA；
   - 凡写报告、汇报、文档、计划、任务卡片，以及**对话框回复和代拟/回复客户消息**，必须遵守《表达原则 v2.2》五大红线与对话/客户规范：结论前置且有增量、肯定句主表达且免责下沉、精简不丢核心数字（任务卡结论 ≤40 字、下一步 ≤30 字、步骤标准 ≤50 字、计划定位 ≤60 字）、说人话且复核点可触发、证据进日志；回复客户时先接住关切、手机一屏易读、严禁内部黑话与越权承诺；
   - 凡维护目标/计划/任务卡，按《任务与卡片管理规范 v2.1》严格区分四层边界，需负责人拍板项一律标「待批准」，并执行防口径打架 5 条硬规则（单一权威口径、改口径四步联动、一卡一事、静动分离、退役下沉）。
   若实际生效的是非空 AGENTS.override.md，则写入该文件；遇到冲突或无法辨认的旧规则先列出并询问我。
5. 写后读回校验：核对 4 份本地文件与固定 commit 原文一致、全局管理段恰好 1 份且原规则未丢。
6. 现场表达校准：向我汇报本次同步结果时，直接用新版《表达原则 v2.2》来写——第一句先给结论，不超过 3 个加粗小标题要点，保留实际路径/版本号/commit 前 7 位，不堆过程流水与否定式免责。同时提醒我：已有旧会话需要重新加载或新开会话才会生效。
```

---

说明：Codex 的全局目录、override 优先级和启动时加载行为见 [OpenAI 官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。本提示词不会让其他电脑或已打开会话自动同步，需要在目标电脑执行。
