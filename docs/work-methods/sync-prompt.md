# 在另一台电脑同步到 Codex

把下面这段提示词交给那台电脑上的 Codex。它只同步文档和全局指引，不安装新 Skill，也不运行仓库脚本。

---

请将 https://github.com/leevi2010-cursor/skills 的 main 分支中 docs/work-methods/expression-principles.md和 docs/work-methods/decision-loop.md同步为这台电脑的 Codex 全局工作指引。

1. 先识别操作系统、实际用户主目录和当前 Codex 使用的 CODEX_HOME；未设置时使用用户主目录下的 .codex。分别检查 AGENTS.md 和 AGENTS.override.md，说明哪一个实际生效；也检查当前项目的覆盖规则。不要把一台机器的绝对路径搬到另一台。
2. 从上述仓库读取 main 的实际 commit SHA，然后固定在该 SHA 读取 docs/work-methods/README.md 和这两个文件，核对两份正文版本与同一 commit 的 README 一致。只读取和保存文本，不执行下载脚本，不运行 portable_skill_manager，不安装软件，不改仓库或上传本机资料。若仓库不可读、版本不符或无法确定实际生效目录，停下说明，不编造成功。
3. 将两份原文保存到实际 CODEX_HOME 下的 work-methods/，记录仓库 URL、实际 commit SHA、版本和文件校验值。已有副本先备份并比较；保留未归入本次管理范围的文件。GitHub 是经授权的通用发布副本，不另建业务目标，不复制私人目标、经营数据、日志或任务表。
4. 先读完整的现有全局指引并备份，只合并一个由 <!-- BEGIN WORK-METHODS --> 与 <!-- END WORK-METHODS --> 标记的管理段；再次同步只替换该段，保留所有其他规则，不整文件覆盖。管理段明确要求执行任务前阅读上述两份本地文档并按其适用范围执行，记录两份版本和 commit。若实际生效的是非空 AGENTS.override.md，就将唯一管理段合并到该文件；不要删除或改名 override 来强行生效。若两文件中发现旧管理段，先比较并说明迁移方案，只清理确认属于本次同步的重复段；遇到冲突或无法辨认的旧规则先问我。默认不改项目级规则、权限和审批设置。
5. 写完重新读取：确认两份文档与固定 commit 的原文一致、管理段恰好一份、其他规则未变；报告实际路径、版本、commit、校验结果及会影响生效的覆盖规则。不要仅凭文件写入成功就声称已生效。请在本会话显式阅读并应用这两份文档；其他已打开的旧会话需要逐个明确告知读取更新，或重新启动会话后确认已加载。

---

说明：Codex 的全局目录、override 优先级和启动时加载行为见 [OpenAI 官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。本提示词不会让其他电脑或已打开会话自动同步；需要在目标电脑执行。
