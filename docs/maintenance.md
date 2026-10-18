# 维护和发布

改仓库源文件，更新唯一注册表，验证后再发布。原则、方法和 Skill 的内容各保留一份；README 的目录从注册表生成，不手改第二套清单。

## 修改放在哪里

| 要改什么 | 修改位置 | 怎样识别版本 |
| --- | --- | --- |
| 共同原则或工作方法 | `docs/work-methods/` 原文件；同步更新注册表的 `documents` 元数据 | 正文已有版本号；发布时记录实际 commit 和文件校验值 |
| Skill 内容与支持文件 | 原 `skills/<名称>/` 目录，保留 `agents/`、`scripts/`、`references/`、`assets/` 的有效引用 | 未单独编号时，用发布 commit 和完整目录 SHA-256；不要补造版本号 |
| 用途、何时需要、前提 | `portable-skill-registry.json` 的原条目 | 与同次发布的内容一致 |
| 安装和更新行为 | `portable_skill_manager.py` 与对应离线测试 | 同次发布 commit；兼容性变化必须写明 |
| Codex 插件包与市场入口 | 根目录 `plugin.json`、`.agents/plugins/marketplace.json`；Skill 清单仍取原注册表 | 插件包版本在 `plugin.json`；包内容变化时递增，Skill 本体仍按 commit 和目录 SHA-256 核验 |

新增 Skill 时创建 `skills/<名称>/SKILL.md`，登记 `name`、相对 `source`、原格式 `install_target`、`summary`、`when_to_use`、`prerequisites` 与 `version_policy`。Skill 全部按需选择，不因进入注册表就成为全员必装。`documents` 只提供文档路由，不交给 Skill 安装命令。

不要删除旧目录、旧入口或改变有效命令的含义来完成一般整理。确需不兼容迁移、删除入口或重要权限变更时，先准备具体差异和回退方法，交由用户确认。

## 发布前检查

先确认所用分支和基线，保留用户未提交内容。工作区有无关改动时，用独立目录准备；不要自动暂存、提交、丢弃那些改动。

```bash
python3 portable_skill_manager.py validate
python3 scripts/render_catalog.py --write
python3 scripts/render_catalog.py --check
python3 -m unittest discover -s tests -v
git diff --check
git diff --stat
git diff
```

再运行当前环境已有的 Skill Creator `quick_validate.py`，逐个验证所有 Skill。它不随本仓库分发；若环境没有，说明这项尚未完成，不临时安装依赖或假称通过。`validate` 验证分发目录，不等于每个 Skill 的业务效果都已验证。

插件包必须保持与注册表一致，只从原 `skills/` 目录发现 Skill；不要把文档包装成会自动改全局规则的 Skill，也不要复制第二份正文。市场条目保持 `AVAILABLE`，不改成默认安装。发布插件元数据前，用支持插件命令的 Codex CLI 从仓库上下文只读列出市场和可用插件，核对名称、版本及包含内容；仅为检查，不安装合集、不连接账号或运行其中工作流。确需增加 MCP、自动执行钩子或默认安装策略时，先明确新增行为和授权，不沿用本次纯 Skills 包的批准。

在临时目录用 `--skills-dir` 演练有改动的安装器，核对计划、读回、冲突保护、备份和回滚；不要为了测试改动真实安装目录。安装目标不能与整个发布仓库重叠，新备份不能位于 Skill 发现根目录中；原有旧备份保留，核实后再按用户选择处理。转写脚本的 `--check` 可用于只检查工具；无参数旧命令会尝试安装，发布检查不运行它。不要运行真实飞书写入、客户操作或私人资料归档来测试仓库整理。

检查准确的待发布文件，扫描凭据、私人链接、个人数据、客户信息、日志、本机绝对路径和生成缓存。只暂存本次范围，再检查 `git diff --cached`。不新增许可证或修改仓库可见性。向 GitHub 发布须有当次有效授权；用户取消后停止远端写入。发布前重新核对 `main` 头，使用快进更新或带预期旧 SHA 的更新；远端有新提交时先重新核对，不能强推覆盖。

发布后读回 GitHub 的实际 commit 与关键文件，给团队该 commit 的链接、版本和验证结果。只有已挂到目标分支的提交才称为该分支已发布；单独创建的 commit 或本地准备完成都不等于发布成功。
