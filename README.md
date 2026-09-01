# Leo's Skills

Leo 创建并公开分发的 AI Skills 集合。仓库中的 Skill 包是公开分发源；各电脑上的 `~/.codex/skills/` 只是安装副本。

## 已收录 Skills

| Skill | 用途 | 目录 |
| --- | --- | --- |
| `five-level-ternary-thinking` | 用“五层三叉”分析“是什么、为什么、怎么办”，生成 364 个带稳定编号、详解和例子的节点，并渲染为交互 HTML | [`skills/five-level-ternary-thinking/`](skills/five-level-ternary-thinking/) |
| `analyze-showroom-sales-recording` | 从销售逐字稿、录音或飞书妙记生成五环节复盘；必须明确客户称呼和销售姓名 | [`skills/analyze-showroom-sales-recording/`](skills/analyze-showroom-sales-recording/) |

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

该 Skill 不包含租户、客户或本机路径。使用前请在本机设置 `SHOWROOM_PROJECT_ROOT`、`SHOWROOM_LARK_PARENT_TOKEN`、`SHOWROOM_LARK_PROFILE`、`SHOWROOM_LARK_BASE_URL` 和 `SHOWROOM_PRIVATE_EVIDENCE_ROOT`；客群维度与销售复盘文件路径为可选配置。

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
