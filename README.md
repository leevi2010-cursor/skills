# Leo's Skills

Leo 创建并公开分发的 AI Skills 集合。仓库中的 Skill 包是公开分发源；各电脑上的 `~/.codex/skills/` 只是安装副本。

## 已收录 Skills

| Skill | 用途 | 目录 |
| --- | --- | --- |
| `five-level-ternary-thinking` | 用“五层三叉”分析“是什么、为什么、怎么办”，生成 364 个带稳定编号、详解和例子的节点，并渲染为交互 HTML | [`skills/five-level-ternary-thinking/`](skills/five-level-ternary-thinking/) |
| `second-brain-digest` | 将获授权的本机资料归档为可校验 Source，并收敛为最少、可追溯的知识更新 | [`skills/second-brain-digest/`](skills/second-brain-digest/) |
| `analyze-showroom-sales-recording` | 从销售录音生成独立的完整五环节复盘，并把客户事实按字段查重后更新或新建到客户资料表 | [`skills/analyze-showroom-sales-recording/`](skills/analyze-showroom-sales-recording/) |
| `write-showroom-acquisition-video-script` | 把已由人审核通过的家具展厅选题写成低搬动成本的咨询视频候选脚本 | [`skills/write-showroom-acquisition-video-script/`](skills/write-showroom-acquisition-video-script/) |

## 在另一台电脑安装

需要 Git 与 Python 3。

```bash
git clone https://github.com/leevi2010-cursor/skills.git
cd skills
python3 portable_skill_manager.py check five-level-ternary-thinking
python3 portable_skill_manager.py install five-level-ternary-thinking
python3 portable_skill_manager.py check five-level-ternary-thinking
```

Windows 可将 `python3` 换成 `py`。默认安装到 `~/.codex/skills/five-level-ternary-thinking/`。如果当前 Codex 尚未显示该 Skill，请重开任务或重启 Codex，让它重新发现 Skill。

安装销售录音分析 Skill：

```bash
python3 portable_skill_manager.py install analyze-showroom-sales-recording
python3 portable_skill_manager.py check analyze-showroom-sales-recording
```

该 Skill 不包含租户、客户或本机路径。使用前请在本机设置 `SHOWROOM_PROJECT_ROOT`、`SHOWROOM_LARK_PARENT_TOKEN`、`SHOWROOM_LARK_PROFILE`、`SHOWROOM_LARK_ACTOR`、`SHOWROOM_LARK_BASE_URL`、`SHOWROOM_CUSTOMER_BASE_URL`、`SHOWROOM_CUSTOMER_TABLE` 和 `SHOWROOM_PRIVATE_EVIDENCE_ROOT`；客群维度与销售复盘文件路径为可选配置。客户资料写入会先查重：唯一匹配时更新原记录，确认没有对应记录且身份资料足够时自动新建，存在多个候选或旧值冲突时停止并请人工确认。

安装 Second Brain Digest Skill：

```bash
python3 portable_skill_manager.py install second-brain-digest
python3 portable_skill_manager.py check second-brain-digest
```

使用时把 `SECOND_BRAIN_ROOT` 设置为自己的知识库根目录，并在根目录提供 `.AGENTS.md`。公开版只规定 `evidence/sources/`、`evidence/.intake/` 与 `evidence/.processing/` 的通用合同；项目、人物、方法和概念的实际目录由各自知识库规则决定。

安装家具展厅咨询视频脚本 Skill：

```bash
python3 portable_skill_manager.py install write-showroom-acquisition-video-script
python3 portable_skill_manager.py check write-showroom-acquisition-video-script
```

该 Skill 只在选题已经由人明确审核通过后编写脚本候选。它会给每个镜头标记制作等级，默认不搬动重家具，并为多人搬运或整件替换镜头提供低成本替代方案。它不执行拍摄、发布或广告投放，也不代表脚本已经验证能获客。

## 更新已安装 Skill

```bash
git pull --ff-only
python3 portable_skill_manager.py install five-level-ternary-thinking
python3 portable_skill_manager.py check five-level-ternary-thinking
```

安装器会比较整个 Skill 目录的 SHA-256 摘要。目标缺失时会安装；目标发生漂移时，会先在同一目录创建带 UTC 时间戳的备份，再写入仓库版本并读回验证。

## 添加新的 Skill

1. 将完整 Skill 包放入 `skills/<skill-name>/`，其中必须包含 `SKILL.md`。
2. 在 `portable-skill-registry.json` 中登记相对目录和安装位置。
3. 使用 Skill Creator 的 `quick_validate.py` 校验格式。
4. 执行 `python3 portable_skill_manager.py check <skill-name>` 验证注册表与安装状态。
5. 提交前检查仓库中没有凭证、私有业务资料、个人数据或本机绝对路径。

## 权威边界

- 本仓库只作为其中已登记公开 Skills 的分发源。
- Leo 的 Second Brain 中既有便携 Skills 仍由其原注册表管理；本仓库不会自动接管或复制那些 Skills。
- 不要反向把某台电脑的安装副本当成权威源。
- 当前仓库未声明开源许可证；公开可见与可克隆不自动授予再分发、修改或商用许可。
