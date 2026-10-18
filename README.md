# Leo's Skills · 团队入口

这里集中说明团队与 Agent 共同遵循什么、遇到什么任务再安装哪些 Skill，以及怎样保留本机规则并安全更新。先读共同原则，工作方法按场景使用，Skill 按需安装。

`portable-skill-registry.json` 是唯一分发目录；下面的目录由它生成。GitHub 中已发布的 commit 是同步来源，各电脑上的安装副本是使用副本。安装某个 Skill 不代表取得其所有外部操作的授权，仍须遵循任务和项目规则。

使用 Codex 的插件管理界面时，可添加本仓库的[团队插件市场](#在-codex-中使用插件市场)。原有单个 Skill 安装方式继续保留。

<a id="通用工作方法"></a>

## 先选需要的内容

<!-- BEGIN REGISTRY CATALOG -->

| 类型 | 内容与版本 | 什么时候用 |
| --- | --- | --- |
| 共同原则 | [表达原则](docs/work-methods/expression-principles.md) · v1.2 | 团队和 Agent 写给人看的说明、报告与建议时共同遵循。 |
| 工作方法 | [决策闭环](docs/work-methods/decision-loop.md) · v1.5 | 需要作决定、比较办法或复盘结果时使用；目标与授权仍以原处为准。 |
| 同步说明 | [跨电脑同步提示词](docs/work-methods/sync-prompt.md) · 随仓库 commit | 需要将两份文档接入另一台电脑的 Codex 全局指引时使用。 |

<a id="已收录-skills"></a>

以下 Skill 都按需安装。它们尚未单独编号，以固定 commit 和目录 SHA-256 识别版本；`list` 可查看校验值。

| Skill | 用途与适用情况 | 必要前提 |
| --- | --- | --- |
| [`five-level-ternary-thinking`](skills/five-level-ternary-thinking/SKILL.md) | 把复杂问题拆成五层三叉思考树，生成可交互的编号图。 需要系统分析“是什么、为什么、怎么办”；简单查询或只要短文本时不必安装。 | Python 3.10+、实际可写的输出目录，以及能打开 HTML 的环境。 |
| [`second-brain-digest`](skills/second-brain-digest/SKILL.md) | 把获授权的本地资料归档为可追溯来源，并更新最少的知识记录。 需要整理自己的知识库、消化资料或合并重复笔记。 | 明确设置 SECOND_BRAIN_ROOT，并先读该知识库根目录的 .AGENTS.md。<br>归档移动须有对应范围和计划的授权；特殊格式转换工具按需另配。<br>建议环境已有 jsonschema 以作完整模式校验；缺失时脚本退回内置合同检查。本仓库安装器不会安装它。 |
| [`analyze-showroom-sales-recording`](skills/analyze-showroom-sales-recording/SKILL.md) | 从家具接待录音生成独立五环节复盘，另把客户事实查重后写入客户表。 处理家具展厅销售录音、逐字稿或飞书妙记；需要确认客户、销售和说话人。 | 先配置项目规则和私密目录；SHOWROOM_* 配置详见 SKILL.md 的“运行配置”。<br>飞书操作需要另备 lark-cli、lark-minutes/lark-doc/lark-wiki/lark-base Skills，以及获授权的身份和目标；本仓库不提供这些依赖。<br>本地音频转写脚本使用 Apple Silicon 的 MLX 路线；其他机器可提供已有逐字稿。从该 Skill 目录先运行 scripts/ensure_local_transcription.sh --check 检查；旧的无参数命令会联网安装依赖，只有获准安装时才运行。 |
| [`write-showroom-acquisition-video-script`](skills/write-showroom-acquisition-video-script/SKILL.md) | 把人工审核通过的具体展厅选题写成低搬动成本的视频脚本候选。 选题和审核人已经明确，需要逐镜脚本与制作难度检查。 | 先取得具体选题的人工通过结论；产品、素材和咨询承接信息按实际提供。<br>Python 3.10+ 运行自带验证器；拍摄、发布、投放分别按原授权执行。 |

<!-- END REGISTRY CATALOG -->

## 让自己的 Agent 达成共识

把这段话交给 Agent 即可开始，文档无需安装成 Skill：

> 请读取这个仓库的 README 和注册表，记录实际 commit。先完整读表达原则 v1.2；遇到决策或复盘时再读决策闭环 v1.5，并按其适用范围执行。根据当前任务选择需要的 Skill，先说明前提和安装计划。不自动安装全部 Skill，不覆盖本机自定义规则；遇到不明冲突先列出冲突。

这段说明只约定本次读取。需要跨会话或跨电脑保留指引时，使用[原同步提示词](docs/work-methods/sync-prompt.md)：它先识别实际 `CODEX_HOME`、`AGENTS.override.md` 和项目覆盖规则，备份后只合并有标记的管理段，保留其他规则并读回。仓库安装器只管理 Skill，**不会复制原则文档，也不会改全局 `AGENTS.md`**。其他电脑和已打开的会话需要各自读取更新。

## 在 Codex 中使用插件市场

市场名称是 **Leo 团队插件市场**（`leo-team`），首版提供一个 **Leo Skills** 合集插件（`leo-skills`），包含上表登记的 Skills。合集直接引用原 `skills/` 目录，不维护第二份正文；共同原则和工作方法仍是文档，不会因为安装插件而自动写入全局规则。

这个仓库目前公开。该市场可以供团队内部使用，但不提供“仅内部成员可见”的访问控制。不要向这里上传凭证、客户资料或内部业务文件；需要限制阅读范围时，应另用经批准的私有仓库。本次没有新增许可证或改变仓库权限。

在 Codex 的插件页面添加市场时，使用仓库地址：

```text
https://github.com/leevi2010-cursor/skills
```

同步后选择 **Leo 团队插件市场**，再按需安装 **Leo Skills**。添加市场只登记来源，不会自动安装或启用合集。合集安装会一起提供本仓库的 Skills；只需要其中一个时，仍可使用下方的单 Skill 安装器。

也可用已支持插件市场命令的 Codex CLI：

```bash
codex plugin marketplace add leevi2010-cursor/skills --ref main
codex plugin list --marketplace leo-team --available --json
```

确认需要整个合集后才执行：

```bash
codex plugin add leo-skills@leo-team
```

安装后新建对话，确认 Agent 能发现并读取所需 Skill。已有手工安装副本不会由本仓库删除或迁移；若出现同名工作流，应先确认选择了哪个来源，避免混用不同版本。插件不包含 Python、转写环境、飞书工具或账号授权，这些前提仍按上表分别准备。安装不代表已经取得写入客户表、移动资料、发布内容或其他外部操作的批准。

刷新已登记的市场：

```bash
codex plugin marketplace upgrade leo-team
codex plugin list --marketplace leo-team --available --json
```

刷新市场目录不等于已打开的 Agent 会话已加载新版本；还须在插件界面确认安装状态，并在新对话中核对。停止使用时，可先用 `codex plugin remove leo-skills@leo-team` 移除合集，再用 `codex plugin marketplace remove leo-team` 移除来源；原手工安装的 Skills 不受这两个命令管理。

市场入口是 [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json)，插件入口是 [`plugin.json`](plugin.json)。创建方式依据 [OpenAI 官方插件打包文档](https://developers.openai.com/plugins/build/plugins)。

## 在另一台电脑安装单个 Skill

需要 Git、Python 3.10+。下例选择一个 Skill，名称可换成上表中的任意一项；Windows 可将 `python3` 换成 `py`。

```bash
git clone https://github.com/leevi2010-cursor/skills.git
cd skills
python3 portable_skill_manager.py validate
python3 portable_skill_manager.py list
python3 portable_skill_manager.py check five-level-ternary-thinking
python3 portable_skill_manager.py install five-level-ternary-thinking --dry-run
python3 portable_skill_manager.py install five-level-ternary-thinking
python3 portable_skill_manager.py check five-level-ternary-thinking
```

`check` 返回 2 表示还没安装、存在差异或需要处理；先看 JSON 中的具体状态。`--dry-run` 遇到待安装或有差异时也返回 2，只报告计划，尚未执行。默认安装到当前 `CODEX_HOME/skills/<名称>/`，未设置 `CODEX_HOME` 时使用 `~/.codex/skills/<名称>/`。`list` 和 `--dry-run` 会列出实际目标，先核对再安装；其他运行环境可用 `--skills-dir` 指定其**绝对 Skill 根目录**。符号链接路径会被拒绝，须先核实实际目录，不能靠强制替换绕过。安装器不会安装 Python 包、转写工具或飞书工具。

旧的 `list`、`check`、`install <名称>` 命令继续可用。不写名称仍会选择全部注册 Skill；它是兼容行为，不是团队的安装要求。如果当前 Codex 尚未显示新 Skill，请重开任务或重启 Codex 后确认已发现。

## 更新已安装 Skill

先检查源仓库是否有自己的改动；有改动时先比较并保留，不要直接拉取覆盖。确认工作区干净后：

```bash
git status --short
git pull --ff-only
git rev-parse HEAD
python3 portable_skill_manager.py validate
python3 portable_skill_manager.py install five-level-ternary-thinking --dry-run
python3 portable_skill_manager.py install five-level-ternary-thinking
python3 portable_skill_manager.py check five-level-ternary-thinking
```

相同内容不重写；本工具上次安装的副本没有被改过时，可以备份后更新。已有副本来源不明，或本机做过修改时，默认保留并报冲突。先比较原文；明确选用仓库版本后，才加 `--replace-local`。此选项仍会备份，不能绕过符号链接、越界路径或源与目标重叠检查。每次只更新自己需要的名称。

同一目标一次只运行一个安装器。脚本会在写入前重核内容，但没有跨进程锁；进程被强制结束或机器断电后，先检查目标和返回过的备份位置，再决定恢复或重试。

新备份放在 Skill 根目录之外的同级专用目录，避免被 Agent 当成重复 Skill；实际路径写在安装结果中。已有旧备份不自动迁移或删除。安装后读回失败会回滚本次写入。安装记录保存在 Skill 根目录的隐藏状态目录中，丢失时按未知副本保护。恢复旧版时，先保留当前副本，再把选定备份恢复到原位置并 `check`；不要删除唯一备份。原则文档的更新仍使用[文档同步提示词](docs/work-methods/sync-prompt.md)。

<a id="添加新的-skill"></a>

## 维护与发布

新增 Skill、改注册信息和发布前检查见[维护说明](docs/maintenance.md)。维护者只改仓库源文件，不把某台电脑的安装副本直接反向覆盖仓库。这里不自动接管其他知识库或注册表管理的 Skills。

<a id="权威边界"></a>

当前仓库未声明开源许可证；公开可见与可克隆不自动授予再分发、修改或商用许可。
